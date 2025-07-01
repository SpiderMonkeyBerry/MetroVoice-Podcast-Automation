# MetroVoice Podcast Automation System

A comprehensive, automated podcast generation system that creates multiple themed podcast series under the MetroVoice brand. The system runs on complete autopilot, covering different niches with AI-generated content, text-to-speech conversion, and automated publishing.

## 🎙️ Podcast Series

The system currently supports four themed podcast series:

1. **Metro Business Brief** - Daily business news and startup insights
2. **Tech Voice** - Weekly technology trends and product reviews  
3. **Urban Lifestyle** - Content about city living, culture, and lifestyle trends
4. **Metro Money** - Personal finance and investment advice

## 🏗️ System Architecture

The system is built with a modular, maintainable architecture:

```
├── config.py              # Centralized configuration management
├── content_generator.py   # AI content generation service
├── tts_service.py         # Text-to-speech conversion service
├── podcast_publisher.py   # Podcast publishing service
├── podcast_orchestrator.py # Main orchestration service
├── lambda_handler.py      # AWS Lambda entry point
└── requirements.txt       # Python dependencies
```

### Key Features

- **Modular Design**: Each service is independent and easily maintainable
- **Error Handling**: Comprehensive error handling with retry logic
- **Security**: API keys stored as environment variables
- **Scalability**: Built for AWS Lambda with cloud-native architecture
- **Monitoring**: Detailed logging and status tracking
- **Flexibility**: Support for custom prompts and manual triggers

## 🚀 Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- Python 3.8+
- API keys for:
  - Perplexity AI (for content generation)
  - ElevenLabs (for text-to-speech)
  - Podbean (for podcast publishing)

### Environment Setup

1. **Set Environment Variables**:
   ```bash
   export PERPLEXITY_API_KEY="your_perplexity_api_key"
   export ELEVENLABS_API_KEY="your_elevenlabs_api_key"
   export PODBEAN_CLIENT_ID="your_podbean_client_id"
   export PODBEAN_CLIENT_SECRET="your_podbean_client_secret"
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **AWS Configuration**:
   - Create S3 bucket: `tmv-podcast-content`
   - Create SNS topic: `Upload_Podcast_Trigger`
   - Configure Lambda function with appropriate IAM roles

### Local Testing

```python
from podcast_orchestrator import PodcastOrchestrator

# Initialize orchestrator
orchestrator = PodcastOrchestrator()

# Generate a single episode
episode = orchestrator.generate_episode("metro_business_brief")

# Generate multiple episodes
episodes = orchestrator.generate_multiple_episodes([
    "metro_business_brief",
    "tech_voice"
])

# Get system status
status = orchestrator.get_series_status()
```

## 📋 Usage Examples

### Manual Episode Generation

```python
# Generate specific series
episode = orchestrator.generate_episode(
    series_id="metro_business_brief",
    custom_prompt="Create a special episode about startup funding trends",
    auto_publish=True
)

# Generate multiple series with custom prompts
custom_prompts = {
    "metro_business_brief": "Focus on international business news",
    "tech_voice": "Cover AI and machine learning trends"
}

episodes = orchestrator.generate_multiple_episodes(
    series_ids=["metro_business_brief", "tech_voice"],
    custom_prompts=custom_prompts
)
```

### Scheduled Generation

The system automatically handles scheduled generation based on publishing frequency:

- **Daily**: Metro Business Brief
- **Weekly**: Tech Voice, Urban Lifestyle, Metro Money (Mondays)

### Lambda Function Triggers

#### CloudWatch Scheduled Events
```json
{
  "source": "aws.events",
  "detail-type": "Scheduled Event"
}
```

#### Manual Triggers
```json
{
  "series_id": "metro_business_brief",
  "custom_prompt": "Optional custom prompt",
  "auto_publish": true
}
```

#### Multiple Series
```json
{
  "series_ids": ["metro_business_brief", "tech_voice"],
  "custom_prompts": {
    "metro_business_brief": "Custom prompt for business series"
  }
}
```

#### Status Check
```json
{
  "action": "status"
}
```

## 🔧 Configuration

### Adding New Podcast Series

Edit `config.py` to add new series:

```python
"new_series": PodcastSeries(
    name="New Series Name",
    description="Series description",
    prompt_template="Custom prompt template for content generation",
    voice_id="ELEVENLABS_VOICE_ID",
    publish_frequency="weekly",  # daily, weekly, monthly
    content_type="news"  # news, review, lifestyle, finance, etc.
)
```

### Customizing Voice Settings

Modify TTS configuration in `config.py`:

```python
TTS_CONFIG = {
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
        "stability": 0.5,        # 0.0 to 1.0
        "similarity_boost": 0.8, # 0.0 to 1.0
        "style": 0.0,           # 0.0 to 1.0
        "use_speaker_boost": True
    }
}
```

## 📊 Monitoring and Logging

The system provides comprehensive logging:

- **Content Generation**: Word count, quality validation
- **Audio Generation**: File size, upload status
- **Publishing**: Episode IDs, Podbean URLs
- **Errors**: Detailed error messages with retry information

### Status Monitoring

```python
# Get detailed status of all series
status = orchestrator.get_series_status()

# Validate system configuration
is_valid = orchestrator.validate_configuration()
```

## 🔒 Security Considerations

- **API Keys**: Stored as environment variables, never in code
- **AWS Permissions**: Minimal required permissions for S3, SNS, Lambda
- **Error Handling**: No sensitive information in error messages
- **Input Validation**: All inputs validated before processing

## 🚨 Error Handling

The system includes robust error handling:

- **Retry Logic**: Automatic retries for transient failures
- **Graceful Degradation**: Continues processing other series if one fails
- **Detailed Logging**: Comprehensive error tracking
- **Fallback Mechanisms**: Legacy support for existing triggers

## 📈 Scaling Considerations

- **Lambda Limits**: Configure appropriate timeout and memory
- **API Rate Limits**: Built-in rate limiting and backoff
- **S3 Storage**: Automatic cleanup of old files
- **Concurrent Processing**: Support for multiple series generation

## 🤝 Contributing

This system is designed to be maintainable and extensible:

1. **Modular Architecture**: Easy to add new services
2. **Type Hints**: Full type annotation for better code quality
3. **Documentation**: Comprehensive docstrings and comments
4. **Testing**: Structure supports unit and integration tests

## 📄 License

This project is designed for public GitHub hosting with no sensitive information included.

## 🆘 Troubleshooting

### Common Issues

1. **API Key Errors**: Verify environment variables are set correctly
2. **AWS Permissions**: Check IAM roles for S3, SNS, Lambda permissions
3. **Content Quality**: Adjust prompt templates for better content
4. **Audio Issues**: Verify ElevenLabs API key and voice IDs

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📞 Support

For issues and questions:
1. Check the logs for detailed error information
2. Verify configuration and API keys
3. Test individual components using the provided examples

---

**MetroVoice Podcast Automation** - Automated podcast generation for the modern content creator. 