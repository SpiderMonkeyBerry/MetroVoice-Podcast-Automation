"""
Podcast Orchestrator for MetroVoice Podcast Automation
Main orchestrator that coordinates content generation, TTS, and publishing
"""

import json
import logging
import boto3
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from config import Config
from content_generator import ContentGenerator, ContentGenerationError
from tts_service import TTSService, TTSServiceError
from podcast_publisher import PodcastPublisher, PodcastPublisherError

logger = logging.getLogger(__name__)

@dataclass
class EpisodeMetadata:
    """Metadata for a generated episode"""
    series_id: str
    title: str
    content: str
    s3_key: str
    episode_id: Optional[str] = None
    podbean_url: Optional[str] = None
    generated_at: Optional[str] = None
    published_at: Optional[str] = None

class PodcastOrchestratorError(Exception):
    """Custom exception for orchestrator errors"""
    pass

class PodcastOrchestrator:
    """Main orchestrator for podcast automation"""
    
    def __init__(self):
        self.content_generator = ContentGenerator()
        self.tts_service = TTSService()
        self.publisher = PodcastPublisher()
        self.sns_client = boto3.client('sns', region_name=Config.AWS_REGION)
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def generate_episode(self, series_id: str, custom_prompt: Optional[str] = None,
                        auto_publish: bool = True) -> EpisodeMetadata:
        """
        Generate a complete episode for a series
        
        Args:
            series_id: The podcast series ID
            custom_prompt: Optional custom prompt
            auto_publish: Whether to automatically publish the episode
            
        Returns:
            EpisodeMetadata object with episode information
        """
        try:
            logger.info(f"Starting episode generation for series: {series_id}")
            
            # Step 1: Generate content
            logger.info("Generating content...")
            content_result = self.content_generator.generate_content(series_id, custom_prompt)
            
            if not content_result["success"]:
                raise PodcastOrchestratorError("Content generation failed")
            
            # Validate content quality
            if not self.content_generator.validate_content(content_result["content"]):
                raise PodcastOrchestratorError("Generated content failed quality validation")
            
            logger.info(f"Content generated successfully: {content_result['word_count']} words")
            
            # Step 2: Generate audio
            logger.info("Generating audio...")
            audio_result = self.tts_service.generate_audio(
                content_result["content"],
                series_id,
                content_result["title"]
            )
            
            if not audio_result["success"]:
                raise PodcastOrchestratorError("Audio generation failed")
            
            logger.info(f"Audio generated successfully: {audio_result['filename']}")
            
            # Step 3: Publish episode (if enabled)
            episode_metadata = EpisodeMetadata(
                series_id=series_id,
                title=content_result["title"],
                content=content_result["content"],
                s3_key=audio_result["s3_key"],
                generated_at=datetime.utcnow().isoformat()
            )
            
            if auto_publish:
                logger.info("Publishing episode...")
                publish_result = self.publisher.publish_episode(
                    series_id=series_id,
                    title=content_result["title"],
                    s3_key=audio_result["s3_key"],
                    description=f"Latest episode from {content_result['series_name']}"
                )
                
                if publish_result["success"]:
                    episode_metadata.episode_id = publish_result["episode_id"]
                    episode_metadata.podbean_url = publish_result["podbean_url"]
                    episode_metadata.published_at = publish_result["published_at"]
                    logger.info(f"Episode published successfully: {publish_result['episode_id']}")
                else:
                    logger.warning("Episode publishing failed, but content and audio were generated")
            
            # Step 4: Cleanup old files
            self.tts_service.cleanup_old_files(series_id)
            
            # Step 5: Send notification
            self._send_notification(episode_metadata)
            
            logger.info(f"Episode generation completed successfully for {series_id}")
            return episode_metadata
            
        except (ContentGenerationError, TTSServiceError, PodcastPublisherError) as e:
            error_msg = f"Error in episode generation pipeline: {str(e)}"
            logger.error(error_msg)
            raise PodcastOrchestratorError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error in episode generation: {str(e)}"
            logger.error(error_msg)
            raise PodcastOrchestratorError(error_msg)
    
    def generate_multiple_episodes(self, series_ids: List[str], 
                                 custom_prompts: Optional[Dict[str, str]] = None,
                                 auto_publish: bool = True) -> List[EpisodeMetadata]:
        """
        Generate episodes for multiple series
        
        Args:
            series_ids: List of series IDs to generate episodes for
            custom_prompts: Optional dict of custom prompts for specific series
            auto_publish: Whether to automatically publish episodes
            
        Returns:
            List of EpisodeMetadata objects
        """
        results = []
        
        for series_id in series_ids:
            try:
                custom_prompt = custom_prompts.get(series_id) if custom_prompts else None
                episode_metadata = self.generate_episode(
                    series_id, custom_prompt, auto_publish
                )
                results.append(episode_metadata)
                
            except PodcastOrchestratorError as e:
                logger.error(f"Failed to generate episode for {series_id}: {str(e)}")
                # Continue with other series
                continue
        
        return results
    
    def generate_scheduled_episodes(self) -> List[EpisodeMetadata]:
        """
        Generate episodes based on publishing schedule
        
        Returns:
            List of EpisodeMetadata objects for generated episodes
        """
        today = datetime.utcnow().date()
        episodes_to_generate = []
        
        for series_id, series_config in Config.PODCAST_SERIES.items():
            if self._should_generate_episode(series_id, series_config, today):
                episodes_to_generate.append(series_id)
        
        if episodes_to_generate:
            logger.info(f"Generating scheduled episodes for: {episodes_to_generate}")
            return self.generate_multiple_episodes(episodes_to_generate)
        else:
            logger.info("No episodes scheduled for generation today")
            return []
    
    def _should_generate_episode(self, series_id: str, series_config, today: datetime.date) -> bool:
        """
        Determine if an episode should be generated based on schedule
        
        Args:
            series_id: The series ID
            series_config: The series configuration
            today: Today's date
            
        Returns:
            True if episode should be generated
        """
        # This is a simplified schedule check
        # In production, you might want to use a more sophisticated scheduling system
        
        if series_config.publish_frequency == "daily":
            return True
        elif series_config.publish_frequency == "weekly":
            # Generate on Mondays
            return today.weekday() == 0
        elif series_config.publish_frequency == "monthly":
            # Generate on the first day of the month
            return today.day == 1
        
        return False
    
    def _send_notification(self, episode_metadata: EpisodeMetadata) -> None:
        """
        Send notification about generated episode
        
        Args:
            episode_metadata: The episode metadata
        """
        try:
            message = {
                "series_id": episode_metadata.series_id,
                "title": episode_metadata.title,
                "s3_key": episode_metadata.s3_key,
                "episode_id": episode_metadata.episode_id,
                "podbean_url": episode_metadata.podbean_url,
                "generated_at": episode_metadata.generated_at,
                "published_at": episode_metadata.published_at
            }
            
            self.sns_client.publish(
                TopicArn=Config.SNS_TOPIC_ARN,
                Message=json.dumps(message),
                Subject=f"New Episode Generated: {episode_metadata.title}"
            )
            
            logger.info("Notification sent successfully")
            
        except Exception as e:
            logger.warning(f"Failed to send notification: {str(e)}")
    
    def get_series_status(self) -> Dict[str, Any]:
        """
        Get status of all podcast series
        
        Returns:
            Dict containing status information for all series
        """
        status = {}
        
        for series_id, series_config in Config.PODCAST_SERIES.items():
            try:
                # Get recent episodes from S3
                s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
                prefix = f"episodes/{series_id}/"
                
                response = s3_client.list_objects_v2(
                    Bucket=Config.S3_BUCKET_NAME,
                    Prefix=prefix,
                    MaxKeys=5
                )
                
                recent_episodes = []
                if 'Contents' in response:
                    for obj in response['Contents']:
                        recent_episodes.append({
                            "filename": obj['Key'],
                            "size": obj['Size'],
                            "last_modified": obj['LastModified'].isoformat()
                        })
                
                status[series_id] = {
                    "name": series_config.name,
                    "description": series_config.description,
                    "publish_frequency": series_config.publish_frequency,
                    "content_type": series_config.content_type,
                    "recent_episodes": recent_episodes,
                    "episode_count": len(recent_episodes)
                }
                
            except Exception as e:
                logger.warning(f"Error getting status for {series_id}: {str(e)}")
                status[series_id] = {"error": str(e)}
        
        return status
    
    def validate_configuration(self) -> bool:
        """
        Validate that all configuration is properly set up
        
        Returns:
            True if configuration is valid
        """
        try:
            # Check API keys
            if not Config.validate_config():
                logger.error("Missing required API keys in configuration")
                return False
            
            # Check AWS permissions
            s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
            s3_client.head_bucket(Bucket=Config.S3_BUCKET_NAME)
            
            # Check SNS topic
            self.sns_client.get_topic_attributes(TopicArn=Config.SNS_TOPIC_ARN)
            
            logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False 