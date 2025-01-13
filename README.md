# MultiModal Telegram Bot with GPT-4o Realtime API

A sophisticated yet elegantly implemented Telegram bot that leverages OpenAI's GPT-4o Realtime API to provide seamless text, voice, and image interactions. This implementation showcases real-time WebSocket communication and advanced audio processing while maintaining clean, maintainable code.

## Features

- **Real-time Text Chat**: Streaming text responses with typing indicators
- **Voice Interaction**: High-quality audio processing with format optimization
- **Image Analysis**: Vision capabilities using GPT-4o Vision
- **WebSocket Management**: Efficient connection handling per chat
- **Multi-Modal Support**: Seamless switching between text, voice, and image processing

## Technical Overview

### Core Components

- **WebSocket Handling**: Implements the GPT-4o Realtime API WebSocket protocol
- **Audio Processing**: 
  - Input: OGG → PCM16 (16kHz, mono)
  - Output: PCM16 → WAV → OGG (with optimized parameters)
- **Connection Management**: Per-chat WebSocket connections with automatic cleanup
- **Error Handling**: Comprehensive error catching and logging

## Installation

```bash
# Clone the repository
git clone [repository-url]

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Set environment variables:
```bash
export TELEGRAM_TOKEN="your_telegram_token"
export OPENAI_API_KEY="your_openai_api_key"
```

2. Configure logging (optional):
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Architecture

### Session Management
- WebSocket connections maintained per chat
- Automatic session configuration for voice/text modes
- Efficient cleanup on shutdown

### Audio Processing Pipeline
1. **Input Processing**:
   - Download Telegram voice message
   - Convert OGG to PCM16 with specific parameters
   - Handle WAV headers properly

2. **Output Processing**:
   - Collect audio chunks
   - Build WAV with correct headers
   - Convert to OGG with optimized quality

### Response Handling
- Streaming text updates
- Chunked audio processing
- Buffer size monitoring
- Proper error handling

## Implementation Examples

### Initialize Bot
```python
bot = MultiModalBot()
bot.run()
```

### Handle Voice Messages
```python
# Voice messages are automatically processed through:
# 1. Audio format conversion
# 2. WebSocket streaming
# 3. Response collection
# 4. Audio reconstruction
```

## API Integration

Utilizes OpenAI's GPT-4o Realtime API endpoints:
- WebSocket: `wss://api.openai.com/v1/realtime`
- Model: `gpt-4o-realtime-preview-2024-12-17`

## Best Practices

1. **Audio Processing**:
   - Maintain consistent sample rates
   - Use proper buffering
   - Handle format conversions carefully

2. **Error Handling**:
   - Comprehensive logging
   - Graceful fallbacks
   - Clear user feedback

3. **Resource Management**:
   - Proper WebSocket cleanup
   - Buffer size limits
   - Connection pooling

## Limitations and Considerations

- WebSocket connections require proper cleanup
- Audio processing is memory-intensive
- Rate limits apply to API usage

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
MIT
