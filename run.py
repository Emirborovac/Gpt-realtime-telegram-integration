import os
import json
import logging
import asyncio
from typing import Dict
import websockets
import base64
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from pydub import AudioSegment
import io
from openai import OpenAI

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = ""
OPENAI_API_KEY = ""

# Store WebSocket connections
ws_connections: Dict[int, websockets.WebSocketClientProtocol] = {}

class MultiModalBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.setup_handlers()
        
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

    async def connect_websocket(self, chat_id: int, is_voice=False) -> websockets.WebSocketClientProtocol:
        """Create or get WebSocket connection for a chat"""
        if chat_id not in ws_connections:
            url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
            try:
                logger.info("Connecting to WebSocket...")
                ws = await websockets.connect(url, extra_headers=headers)
                logger.info("WebSocket connected")
                
                response = json.loads(await ws.recv())
                logger.info(f"Session created: {response}")
                
                session_config = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["audio", "text"] if is_voice else ["text"],
                        "instructions": "You are a helpful assistant in a Telegram chat."
                    }
                }
                
                if is_voice:
                    session_config["session"].update({
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "voice": "ballad",
                        "turn_detection": None
                    })
                
                await ws.send(json.dumps(session_config))
                response = json.loads(await ws.recv())
                logger.info(f"Session updated: {response}")
                
                ws_connections[chat_id] = ws
                
            except Exception as e:
                logger.error(f"WebSocket connection failed: {str(e)}")
                raise
                
        return ws_connections[chat_id]

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        await update.message.reply_text(
            "👋 Hello! I'm your MultiModal Assistant. You can:\n"
            "• Send text messages for chat\n"
            "• Send voice messages for voice conversations\n"
            "• Send photos for analysis\n"
            "I'll respond accordingly!"
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        chat_id = update.effective_chat.id
        text = update.message.text
        
        try:
            ws = await self.connect_websocket(chat_id)
            await ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": text
                    }]
                }
            }))
            
            await ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "modalities": ["text"]
                }
            }))
            
            accumulated_text = ""
            typing_message = await update.message.reply_text("...")
            
            while True:
                response = json.loads(await ws.recv())
                
                if response["type"] == "response.text.delta":
                    accumulated_text += response["delta"]
                    if len(accumulated_text) % 20 == 0:
                        await typing_message.edit_text(accumulated_text + "...")
                        
                elif response["type"] == "response.done":
                    await typing_message.edit_text(accumulated_text)
                    break
                    
        except Exception as e:
            logger.error(f"Error in handle_text: {str(e)}")
            await update.message.reply_text("Sorry, I encountered an error while processing your message.")

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages with improved audio processing"""
        chat_id = update.effective_chat.id
        voice = update.message.voice
        processing_msg = None
        
        try:
            processing_msg = await update.message.reply_text("Processing your message...")
            voice_file = await context.bot.get_file(voice.file_id)
            voice_bytes = await voice_file.download_as_bytearray()
            logger.info("Downloaded voice message")
            
            # Improved audio conversion
            with io.BytesIO(voice_bytes) as ogg_bytes:
                logger.info("Converting OGG to PCM16...")
                audio = AudioSegment.from_ogg(ogg_bytes)
                
                # Ensure consistent audio format
                audio = audio.set_frame_rate(24000)  # Match GPT's expected sample rate
                audio = audio.set_channels(1)        # Mono
                audio = audio.set_sample_width(2)    # 16-bit
                
                logger.info(f"Normalized audio format: {audio.frame_rate}Hz, {audio.channels} channel(s), {audio.sample_width} bytes per sample")
                
                # Export as WAV with specific parameters
                wav_io = io.BytesIO()
                audio.export(wav_io, 
                            format="wav",
                            parameters=[
                                "-acodec", "pcm_s16le",
                                "-ar", "24000",
                                "-ac", "1",
                                "-f", "wav"
                            ])
                wav_io.seek(0)
                logger.info("Converted to WAV format")
                
                # Skip WAV header more reliably
                wav_header_size = 44
                wav_io.seek(wav_header_size)
                pcm_data = wav_io.read()
                base64_audio = base64.b64encode(pcm_data).decode('utf-8')
                logger.info(f"PCM data size: {len(pcm_data)} bytes")
            
            # Get WebSocket connection specifically configured for voice
            ws = await self.connect_websocket(chat_id, is_voice=True)
            
            # Send audio in smaller chunks if needed
            chunk_size = 1024 * 1024  # 1MB chunks
            for i in range(0, len(base64_audio), chunk_size):
                chunk = base64_audio[i:i + chunk_size]
                await ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": chunk
                }))
                logger.info(f"Sent audio chunk {i//chunk_size + 1}")
            
            # Commit the audio buffer
            await ws.send(json.dumps({
                "type": "input_audio_buffer.commit"
            }))
            logger.info("Audio buffer committed")
            
            # Request response with both audio and text
            await ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "modalities": ["audio", "text"],
                    "voice": "ballad"
                }
            }))
            
            # Improved response handling
            audio_chunks = []
            text_response = ""
            buffer_size = 0
            max_buffer_size = 10 * 1024 * 1024  # 10MB limit
            
            while True:
                response = json.loads(await ws.recv())
                
                if response["type"] == "error":
                    raise Exception(f"Server error: {response.get('error', {}).get('message', 'Unknown error')}")
                    
                elif response["type"] == "response.audio.delta":
                    chunk = base64.b64decode(response["delta"])
                    buffer_size += len(chunk)
                    
                    if buffer_size > max_buffer_size:
                        raise Exception("Audio response too large")
                        
                    audio_chunks.append(chunk)
                    
                elif response["type"] == "response.text.delta":
                    text_response += response["delta"]
                    await processing_msg.edit_text(f"Processing... Received {len(text_response)} chars")
                    
                elif response["type"] == "response.done":
                    if not audio_chunks:
                        await processing_msg.edit_text("No audio response received.")
                        return
                    
                    complete_audio = b''.join(audio_chunks)
                    
                    # Create WAV with proper headers
                    with io.BytesIO() as wav_io:
                        # Write WAV header
                        wav_io.write(b'RIFF')
                        wav_io.write((36 + len(complete_audio)).to_bytes(4, 'little'))
                        wav_io.write(b'WAVE')
                        wav_io.write(b'fmt ')
                        wav_io.write((16).to_bytes(4, 'little'))
                        wav_io.write((1).to_bytes(2, 'little'))      # PCM format
                        wav_io.write((1).to_bytes(2, 'little'))      # Mono
                        wav_io.write((24000).to_bytes(4, 'little'))  # Sample rate
                        wav_io.write((48000).to_bytes(4, 'little'))  # Byte rate (24000 * 2)
                        wav_io.write((2).to_bytes(2, 'little'))      # Block align
                        wav_io.write((16).to_bytes(2, 'little'))     # Bits per sample
                        wav_io.write(b'data')
                        wav_io.write(len(complete_audio).to_bytes(4, 'little'))
                        wav_io.write(complete_audio)
                        
                        # Convert to OGG with optimal quality
                        wav_io.seek(0)
                        audio = AudioSegment.from_wav(wav_io)
                        ogg_io = io.BytesIO()
                        
                        # Export with specific codec parameters
                        audio.export(ogg_io,
                                format='ogg',
                                codec='libopus',
                                parameters=[
                                    "-ar", "24000",
                                    "-ac", "1",
                                    "-b:a", "64k"  # Bitrate for good quality
                                ])
                        ogg_io.seek(0)
                        
                        # Send voice message
                        await context.bot.send_voice(
                            chat_id=chat_id,
                            voice=ogg_io,
                            filename="response.ogg",
                            caption=text_response if text_response else None
                        )
                    
                    await processing_msg.delete()
                    break
                    
        except Exception as e:
            logger.error(f"Error in handle_voice: {str(e)}")
            error_message = f"Sorry, I encountered an error while processing your voice message: {str(e)}"
            if processing_msg:
                await processing_msg.edit_text(error_message)
            else:
                await update.message.reply_text(error_message)

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages using Vision API"""
        photo = update.message.photo[-1]  # Get the largest photo
        caption = update.message.caption or "Describe this image"
        processing_msg = None
        
        try:
            processing_msg = await update.message.reply_text("Processing image...")
            
            # Download photo
            photo_file = await context.bot.get_file(photo.file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Convert to base64
            base64_image = base64.b64encode(photo_bytes).decode('utf-8')
            
            # Process with Vision API
            response = self.openai_client.chat.completions.create(
                model="chatgpt-4o-latest",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": caption
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            # Send the response
            analysis = response.choices[0].message.content
            await processing_msg.edit_text(analysis)
            
        except Exception as e:
            logger.error(f"Error in handle_photo: {str(e)}")
            if processing_msg:
                await processing_msg.edit_text("Sorry, I encountered an error while processing your image.")
            else:
                await update.message.reply_text("Sorry, I encountered an error while processing your image.")

    async def cleanup_websockets(self):
        """Clean up WebSocket connections"""
        for ws in ws_connections.values():
            try:
                await ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket connection: {str(e)}")

    def run(self):
        """Run the bot"""
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function to run the bot"""
    bot = MultiModalBot()
    try:
        logger.info("Starting bot...")
        bot.run()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
        asyncio.get_event_loop().run_until_complete(bot.cleanup_websockets())
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        asyncio.get_event_loop().run_until_complete(bot.cleanup_websockets())
        raise

if __name__ == '__main__':
    main()