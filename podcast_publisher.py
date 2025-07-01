"""
Podcast Publishing Service for MetroVoice Podcast Automation
Handles uploading episodes to Podbean platform
"""

import requests
import boto3
import os
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class PodcastPublisherError(Exception):
    """Custom exception for podcast publishing errors"""
    pass

class PodcastPublisher:
    """Handles podcast episode publishing to Podbean"""
    
    def __init__(self):
        self.client_id = Config.API_CONFIG.podbean_client_id
        self.client_secret = Config.API_CONFIG.podbean_client_secret
        self.access_token = None
        self.token_expiry = None
        self.s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
    
    def publish_episode(self, series_id: str, title: str, s3_key: str, 
                       description: Optional[str] = None) -> Dict[str, Any]:
        """
        Publish an episode to Podbean
        
        Args:
            series_id: The podcast series ID
            title: The episode title
            s3_key: The S3 key of the audio file
            description: Optional episode description
            
        Returns:
            Dict containing publishing information
        """
        try:
            # Get access token
            access_token = self._get_access_token()
            
            # Download file from S3 to local temp
            local_file_path = self._download_from_s3(s3_key)
            
            # Get presigned URL for upload
            file_size = os.path.getsize(local_file_path)
            presigned_url, file_key = self._get_presigned_url(
                access_token, os.path.basename(s3_key), file_size
            )
            
            # Upload file to Podbean
            self._upload_to_podbean(local_file_path, presigned_url)
            
            # Create episode
            episode_data = self._create_episode_data(
                access_token, title, description, file_key, series_id
            )
            
            # Publish episode
            episode_response = self._publish_episode_to_podbean(episode_data)
            
            # Cleanup
            os.remove(local_file_path)
            
            return {
                "success": True,
                "series_id": series_id,
                "title": title,
                "episode_id": episode_response.get("id"),
                "published_at": datetime.utcnow().isoformat(),
                "podbean_url": episode_response.get("url"),
                "file_key": file_key
            }
            
        except Exception as e:
            error_msg = f"Error publishing episode: {str(e)}"
            logger.error(error_msg)
            raise PodcastPublisherError(error_msg)
    
    def _get_access_token(self) -> str:
        """Get or refresh Podbean access token"""
        if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return self.access_token
        
        token_url = 'https://api.podbean.com/v1/oauth/token'
        headers = {'Content-Type': 'application/json'}
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(token_url, headers=headers, json=data)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                # Set expiry to 1 hour from now (with some buffer)
                self.token_expiry = datetime.utcnow().replace(
                    second=0, microsecond=0
                ).replace(minute=datetime.utcnow().minute + 55)
                return self.access_token
            else:
                error_msg = f"Failed to obtain access token. Status: {response.status_code}"
                logger.error(error_msg)
                raise PodcastPublisherError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error getting access token: {str(e)}"
            logger.error(error_msg)
            raise PodcastPublisherError(error_msg)
    
    def _download_from_s3(self, s3_key: str) -> str:
        """Download file from S3 to local temp directory"""
        local_file_path = f"/tmp/{os.path.basename(s3_key)}"
        
        try:
            self.s3_client.download_file(
                Config.S3_BUCKET_NAME, 
                s3_key, 
                local_file_path
            )
            logger.info(f"Downloaded {s3_key} to {local_file_path}")
            return local_file_path
            
        except Exception as e:
            error_msg = f"Error downloading from S3: {str(e)}"
            logger.error(error_msg)
            raise PodcastPublisherError(error_msg)
    
    def _get_presigned_url(self, access_token: str, filename: str, 
                          filesize: int) -> Tuple[str, str]:
        """Get presigned URL for file upload"""
        upload_authorize_url = 'https://api.podbean.com/v1/files/uploadAuthorize'
        params = {
            'access_token': access_token,
            'filename': filename,
            'filesize': filesize,
            'content_type': 'audio/mpeg'
        }
        
        try:
            response = requests.get(upload_authorize_url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('presigned_url'), data.get('file_key')
            else:
                error_msg = f"Failed to get presigned URL. Status: {response.status_code}"
                logger.error(error_msg)
                raise PodcastPublisherError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error getting presigned URL: {str(e)}"
            logger.error(error_msg)
            raise PodcastPublisherError(error_msg)
    
    def _upload_to_podbean(self, local_file_path: str, presigned_url: str) -> None:
        """Upload file to Podbean using presigned URL"""
        headers = {'Content-Type': 'audio/mpeg'}
        
        try:
            with open(local_file_path, 'rb') as file:
                response = requests.put(presigned_url, data=file, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"Failed to upload to Podbean. Status: {response.status_code}"
                logger.error(error_msg)
                raise PodcastPublisherError(error_msg)
                
            logger.info("File uploaded to Podbean successfully")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error uploading to Podbean: {str(e)}"
            logger.error(error_msg)
            raise PodcastPublisherError(error_msg)
    
    def _create_episode_data(self, access_token: str, title: str, 
                           description: Optional[str], file_key: str, 
                           series_id: str) -> Dict[str, Any]:
        """Create episode data for publishing"""
        series_config = Config.get_series_config(series_id)
        series_name = series_config.name if series_config else "MetroVoice"
        
        # Create default description if none provided
        if not description:
            description = f"Latest episode from {series_name} - {series_config.description if series_config else 'MetroVoice Podcast'}"
        
        return {
            "access_token": access_token,
            "title": title,
            "content": description,
            "status": "publish",
            "type": "public",
            "media_key": file_key,
            "logo_key": "",  # Optional: Add series logo if available
            "tags": f"metrovoice,{series_id},{series_name.lower().replace(' ', '_')}"
        }
    
    def _publish_episode_to_podbean(self, episode_data: Dict[str, Any]) -> Dict[str, Any]:
        """Publish episode to Podbean"""
        upload_url = 'https://api.podbean.com/v1/episodes'
        
        try:
            response = requests.post(upload_url, data=episode_data)
            
            if response.status_code == 200:
                episode_info = response.json()
                logger.info(f"Episode published successfully: {episode_info.get('id')}")
                return episode_info
            else:
                error_msg = f"Failed to publish episode. Status: {response.status_code}, Response: {response.text}"
                logger.error(error_msg)
                raise PodcastPublisherError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error publishing episode: {str(e)}"
            logger.error(error_msg)
            raise PodcastPublisherError(error_msg)
    
    def get_episode_status(self, episode_id: str) -> Dict[str, Any]:
        """Get status of a published episode"""
        access_token = self._get_access_token()
        url = f'https://api.podbean.com/v1/episodes/{episode_id}'
        params = {'access_token': access_token}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Could not get episode status: {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error getting episode status: {str(e)}")
            return {} 