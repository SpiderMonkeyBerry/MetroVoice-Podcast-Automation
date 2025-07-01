"""
Configuration file for MetroVoice Podcast Automation System
Contains all settings, API keys, and series configurations
"""

import os
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class PodcastSeries:
    """Configuration for a podcast series"""
    name: str
    description: str
    prompt_template: str
    voice_id: str
    publish_frequency: str  # daily, weekly, monthly
    content_type: str  # news, story, analysis, etc.

@dataclass
class APIConfig:
    """API configuration settings"""
    perplexity_api_key: str
    elevenlabs_api_key: str
    podbean_client_id: str
    podbean_client_secret: str

class Config:
    """Main configuration class"""
    
    # AWS Configuration
    AWS_REGION = "us-west-2"
    S3_BUCKET_NAME = "tmv-podcast-content"
    SNS_TOPIC_ARN = "arn:aws:sns:us-west-2:992382733262:Upload_Podcast_Trigger"
    
    # API Configuration - Use environment variables for security
    API_CONFIG = APIConfig(
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY", ""),
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        podbean_client_id=os.getenv("PODBEAN_CLIENT_ID", ""),
        podbean_client_secret=os.getenv("PODBEAN_CLIENT_SECRET", "")
    )
    
    # Podcast Series Configurations
    PODCAST_SERIES = {
        "metro_business_brief": PodcastSeries(
            name="Metro Business Brief",
            description="Daily business news and startup insights",
            prompt_template=(
                "Create a comprehensive daily business news summary covering: "
                "1. Top 3-4 major business headlines from today "
                "2. Startup funding news and insights "
                "3. Market trends and analysis "
                "4. One actionable business tip for entrepreneurs "
                "Format as a professional business podcast episode. "
                "Word count: 800-1200 words. "
                "Tone: Professional, informative, engaging. "
                "Include a clear title and structured content suitable for audio narration."
            ),
            voice_id="MF3mGyEYCl7XYWbV9V6O",  # Professional business voice
            publish_frequency="daily",
            content_type="news"
        ),
        
        "tech_voice": PodcastSeries(
            name="Tech Voice",
            description="Weekly technology trends and product reviews",
            prompt_template=(
                "Create a weekly technology podcast episode covering: "
                "1. Major tech industry news and developments "
                "2. Product reviews and recommendations "
                "3. Emerging technology trends "
                "4. Tech tips and insights for listeners "
                "Format as an engaging tech podcast episode. "
                "Word count: 1000-1500 words. "
                "Tone: Tech-savvy, enthusiastic, accessible. "
                "Include a clear title and structured content suitable for audio narration."
            ),
            voice_id="pNInz6obpgDQGcFmaJgB",  # Tech enthusiast voice
            publish_frequency="weekly",
            content_type="review"
        ),
        
        "urban_lifestyle": PodcastSeries(
            name="Urban Lifestyle",
            description="Content about city living, culture, and lifestyle trends",
            prompt_template=(
                "Create an urban lifestyle podcast episode covering: "
                "1. City living tips and insights "
                "2. Cultural trends and events "
                "3. Lifestyle recommendations for urban dwellers "
                "4. Stories about city life and community "
                "Format as an engaging lifestyle podcast episode. "
                "Word count: 800-1200 words. "
                "Tone: Relatable, warm, community-focused. "
                "Include a clear title and structured content suitable for audio narration."
            ),
            voice_id="VR6AewLTigWG4xSOukaG",  # Warm, relatable voice
            publish_frequency="weekly",
            content_type="lifestyle"
        ),
        
        "metro_money": PodcastSeries(
            name="Metro Money",
            description="Personal finance and investment advice",
            prompt_template=(
                "Create a personal finance podcast episode covering: "
                "1. Current financial market insights "
                "2. Personal finance tips and strategies "
                "3. Investment advice and opportunities "
                "4. Financial planning guidance "
                "Format as a professional finance podcast episode. "
                "Word count: 1000-1500 words. "
                "Tone: Professional, trustworthy, educational. "
                "Include a clear title and structured content suitable for audio narration."
            ),
            voice_id="pNInz6obpgDQGcFmaJgB",  # Professional finance voice
            publish_frequency="weekly",
            content_type="finance"
        )
    }
    
    # TTS Configuration
    TTS_CONFIG = {
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    
    # Content Generation Configuration
    CONTENT_CONFIG = {
        "model": "sonar",
        "max_retries": 3,
        "timeout": 30
    }
    
    @classmethod
    def get_series_config(cls, series_id: str) -> PodcastSeries:
        """Get configuration for a specific podcast series"""
        return cls.PODCAST_SERIES.get(series_id)
    
    @classmethod
    def get_all_series_ids(cls) -> List[str]:
        """Get all available series IDs"""
        return list(cls.PODCAST_SERIES.keys())
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that all required configuration is present"""
        required_keys = [
            cls.API_CONFIG.perplexity_api_key,
            cls.API_CONFIG.elevenlabs_api_key,
            cls.API_CONFIG.podbean_client_id,
            cls.API_CONFIG.podbean_client_secret
        ]
        return all(key for key in required_keys) 