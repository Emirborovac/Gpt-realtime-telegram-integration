# MultiModal Bot - Detailed Technical Explanation

## Models & APIs Used
1. **Real-time Chat & Voice**: `gpt-4o-realtime-preview-2024-12-17`
   - Used for text and voice interactions
   - Accessed via WebSocket connection

2. **Image Analysis**: `chatgpt-4o-latest`
   - Used specifically for image processing
   - Accessed via standard REST API

## Core Components

### 1. Class Structure
```python
class MultiModalBot:
    def __init__(self):
        # Initializes Telegram bot and OpenAI client
        # Sets up message handlers
```

### 2. Connection Management
- Global WebSocket connection dictionary: `ws_connections`
- Per-chat connection management
- Automatic cleanup on shutdown

### 3. Message Handlers

#### Text Messages (`handle_text`)
- Creates WebSocket connection
- Sends text messages
- Streams responses with typing indicators
- Updates message in real-time

#### Voice Messages (`handle_voice`)
1. **Audio Processing Pipeline**:
   - Downloads OGG from Telegram
   - Converts to PCM16 format
   - Sets correct sample rate (24000Hz)
   - Manages mono channel and 16-bit depth

2. **Chunking System**:
   - Splits large audio into 1MB chunks
   - Buffer size monitoring (10MB limit)
   - Proper audio reconstruction

3. **Response Processing**:
   - Collects audio chunks
   - Builds WAV with correct headers
   - Converts to OGG for Telegram
   - Includes text captions

#### Photo Messages (`handle_photo`)
- Uses Vision API directly
- Base64 encodes images
- Processes with high detail setting
- Supports optional captions

### 4. WebSocket Session Management

#### Configuration
```python
session_config = {
    "type": "session.update",
    "session": {
        "modalities": ["audio", "text"] if is_voice else ["text"],
        "instructions": "You are a helpful assistant in a Telegram chat."
    }
}
```

#### Voice-Specific Settings
```python
{
    "input_audio_format": "pcm16",
    "output_audio_format": "pcm16",
    "voice": "ballad",
    "turn_detection": None
}
```

### 5. Error Handling
- Comprehensive try-except blocks
- Detailed logging
- User-friendly error messages
- Connection cleanup on errors

## Technical Specifications

### Audio Processing
1. **Input Format**:
   - Source: Telegram OGG
   - Target: PCM16
   - Sample Rate: 24kHz
   - Channels: Mono
   - Bit Depth: 16-bit

2. **Output Format**:
   - Processing: PCM16 → WAV → OGG
   - Codec: libopus
   - Bitrate: 64k
   - Parameters: 24kHz, mono

### WebSocket Protocol
1. **Connection**:
   - URL: `wss://api.openai.com/v1/realtime`
   - Headers: Authorization & Beta flag

2. **Message Types**:
   - conversation.item.create
   - input_audio_buffer.append
   - input_audio_buffer.commit
   - response.create

### Vision API Integration
```python
{
    "type": "image_url",
    "image_url": {
        "url": f"data:image/jpeg;base64,{base64_image}",
        "detail": "high"
    }
}
```

## Implementation Details

### Resource Management
1. **Memory**:
   - Audio chunk size: 1MB
   - Maximum buffer: 10MB
   - Base64 encoding handling

2. **Connections**:
   - Per-chat WebSocket pools
   - Automatic cleanup
   - Error recovery

### Performance Optimizations
1. **Audio**:
   - Efficient format conversions
   - Proper buffer management
   - Optimized codec parameters

2. **Text**:
   - Real-time streaming
   - Efficient update intervals
   - Message editing optimization

## Usage Examples

### Start Bot
```python
if __name__ == '__main__':
    bot = MultiModalBot()
    bot.run()
```

### Send Voice Message
1. User sends voice message
2. Bot processes audio
3. GPT-4o processes and responds
4. Bot sends voice response with text caption

### Send Image
1. User sends image with optional caption
2. Bot processes with Vision API
3. GPT-4o analyzes image
4. Bot sends detailed description

## Security Considerations
- API key management
- Error message sanitization
- Resource limits enforcement
- Connection security
