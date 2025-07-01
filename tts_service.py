"""
Text-to-Speech Service for MetroVoice Podcast Automation
Handles audio generation using ElevenLabs API
"""

import requests
import boto3
import logging
from io import BytesIO
from typing import Dict, Any, Optional
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class TTSServiceError(Exception):
    """Custom exception for TTS service errors"""
    pass

class TTSService:
    """Handles text-to-speech conversion using ElevenLabs API"""
    
    def __init__(self):
        self.api_key = Config.API_CONFIG.elevenlabs_api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
    
    def generate_audio(self, text: str, series_id: str, title: str) -> Dict[str, Any]:
        """
        Generate audio from text and upload to S3
        
        Args:
            text: The text to convert to speech
            series_id: The podcast series ID
            title: The episode title
            
        Returns:
            Dict containing audio file information
        """
        try:
            # Get series configuration for voice settings
            series_config = Config.get_series_config(series_id)
            if not series_config:
                raise TTSServiceError(f"Invalid series ID: {series_id}")
            
            # Generate audio using ElevenLabs API
            audio_stream = self._generate_audio_stream(text, series_config.voice_id)
            
            # Create filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{series_id}_{timestamp}.mp3"
            
            # Upload to S3
            s3_key = f"episodes/{series_id}/{filename}"
            self._upload_to_s3(audio_stream, s3_key)
            
            return {
                "success": True,
                "series_id": series_id,
                "title": title,
                "filename": filename,
                "s3_key": s3_key,
                "s3_bucket": Config.S3_BUCKET_NAME,
                "generated_at": datetime.utcnow().isoformat(),
                "file_size": len(audio_stream.getvalue())
            }
            
        except Exception as e:
            error_msg = f"Error generating audio: {str(e)}"
            logger.error(error_msg)
            raise TTSServiceError(error_msg)
    
    def _generate_audio_stream(self, text: str, voice_id: str) -> BytesIO:
        """
        Generate audio stream from text using ElevenLabs API
        
        Args:
            text: The text to convert to speech
            voice_id: The voice ID to use
            
        Returns:
            BytesIO object containing the audio data
        """
        tts_url = f"{self.base_url}/text-to-speech/{voice_id}/stream"
        
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": Config.TTS_CONFIG["model_id"],
            "voice_settings": Config.TTS_CONFIG["voice_settings"]
        }
        
        try:
            response = requests.post(tts_url, headers=headers, json=data, stream=True)
            
            if response.status_code == 200:
                audio_stream = BytesIO()
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        audio_stream.write(chunk)
                audio_stream.seek(0)
                return audio_stream
            else:
                error_msg = f"TTS API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise TTSServiceError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during TTS generation: {str(e)}"
            logger.error(error_msg)
            raise TTSServiceError(error_msg)
    
    def _upload_to_s3(self, audio_stream: BytesIO, s3_key: str) -> None:
        """
        Upload audio stream to S3
        
        Args:
            audio_stream: The audio data as BytesIO
            s3_key: The S3 key for the file
        """
        try:
            self.s3_client.upload_fileobj(
                audio_stream,
                Config.S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': 'audio/mpeg',
                    'Metadata': {
                        'generated_at': datetime.utcnow().isoformat(),
                        'source': 'metrovoice_podcast_automation'
                    }
                }
            )
            logger.info(f"Audio file uploaded to S3: {s3_key}")
            
        except Exception as e:
            error_msg = f"Error uploading to S3: {str(e)}"
            logger.error(error_msg)
            raise TTSServiceError(error_msg)
    
    def get_audio_duration(self, audio_stream: BytesIO) -> Optional[float]:
        """
        Estimate audio duration (approximate)
        
        Args:
            audio_stream: The audio data
            
        Returns:
            Estimated duration in seconds
        """
        try:
            # This is a rough estimation - in production you might want to use a proper audio library
            file_size = len(audio_stream.getvalue())
            # Rough estimation: 1MB ≈ 1 minute of audio at typical podcast quality
            estimated_duration = (file_size / (1024 * 1024)) * 60
            return estimated_duration
        except Exception as e:
            logger.warning(f"Could not estimate audio duration: {str(e)}")
            return None
    
    def cleanup_old_files(self, series_id: str, max_files: int = 10) -> None:
        """
        Clean up old audio files for a series (keep only the most recent ones)
        
        Args:
            series_id: The series ID to clean up
            max_files: Maximum number of files to keep
        """
        try:
            # List objects in the series directory
            prefix = f"episodes/{series_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=Config.S3_BUCKET_NAME,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return
            
            # Sort by last modified time (newest first)
            objects = sorted(
                response['Contents'],
                key=lambda x: x['LastModified'],
                reverse=True
            )
            
            # Delete old files
            files_to_delete = objects[max_files:]
            if files_to_delete:
                delete_keys = [{'Key': obj['Key']} for obj in files_to_delete]
                self.s3_client.delete_objects(
                    Bucket=Config.S3_BUCKET_NAME,
                    Delete={'Objects': delete_keys}
                )
                logger.info(f"Cleaned up {len(files_to_delete)} old files for series {series_id}")
                
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}") 