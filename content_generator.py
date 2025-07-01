"""
Content Generation Service for MetroVoice Podcast Automation
Handles AI-powered content creation using Perplexity API
"""

import json
import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class ContentGenerationError(Exception):
    """Custom exception for content generation errors"""
    pass

class ContentGenerator:
    """Handles content generation using Perplexity AI API"""
    
    def __init__(self):
        self.api_endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.API_CONFIG.perplexity_api_key}"
        }
    
    def generate_content(self, series_id: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate content for a specific podcast series
        
        Args:
            series_id: The ID of the podcast series
            custom_prompt: Optional custom prompt to override the series template
            
        Returns:
            Dict containing the generated content and metadata
        """
        try:
            # Get series configuration
            series_config = Config.get_series_config(series_id)
            if not series_config:
                raise ContentGenerationError(f"Invalid series ID: {series_id}")
            
            # Use custom prompt or series template
            prompt = custom_prompt or series_config.prompt_template
            
            # Prepare the request payload
            payload = {
                "model": Config.CONTENT_CONFIG["model"],
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Send request with retry logic
            response = self._make_request_with_retry(payload)
            
            # Process the response
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Extract title and content
                lines = content.strip().split('\n')
                title = lines[0].strip()
                story_content = '\n'.join(lines[1:]).strip()
                
                return {
                    "success": True,
                    "series_id": series_id,
                    "series_name": series_config.name,
                    "title": title,
                    "content": story_content,
                    "full_content": content,
                    "word_count": len(content.split()),
                    "generated_at": datetime.utcnow().isoformat(),
                    "content_type": series_config.content_type
                }
            else:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise ContentGenerationError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during content generation: {str(e)}"
            logger.error(error_msg)
            raise ContentGenerationError(error_msg)
        except (KeyError, IndexError) as e:
            error_msg = f"Error parsing API response: {str(e)}"
            logger.error(error_msg)
            raise ContentGenerationError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during content generation: {str(e)}"
            logger.error(error_msg)
            raise ContentGenerationError(error_msg)
    
    def _make_request_with_retry(self, payload: Dict[str, Any]) -> requests.Response:
        """
        Make API request with retry logic
        
        Args:
            payload: The request payload
            
        Returns:
            API response
        """
        max_retries = Config.CONTENT_CONFIG["max_retries"]
        timeout = Config.CONTENT_CONFIG["timeout"]
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=timeout
                )
                
                # If successful, return immediately
                if response.status_code == 200:
                    return response
                
                # If rate limited, wait and retry
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {wait_time} seconds before retry {attempt + 1}")
                    import time
                    time.sleep(wait_time)
                    continue
                
                # For other errors, don't retry
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise ContentGenerationError("Request timed out after all retries")
                continue
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise ContentGenerationError("Connection failed after all retries")
                continue
        
        raise ContentGenerationError(f"Request failed after {max_retries} attempts")
    
    def validate_content(self, content: str, min_words: int = 500) -> bool:
        """
        Validate generated content meets quality standards
        
        Args:
            content: The generated content
            min_words: Minimum word count required
            
        Returns:
            True if content is valid, False otherwise
        """
        if not content or not content.strip():
            return False
        
        word_count = len(content.split())
        if word_count < min_words:
            return False
        
        # Check for basic content quality indicators
        lines = content.split('\n')
        if len(lines) < 3:  # Should have at least title and some content
            return False
        
        # Check for common error patterns
        error_indicators = [
            "I apologize",
            "I'm sorry",
            "I cannot",
            "I'm unable",
            "Error",
            "Failed"
        ]
        
        content_lower = content.lower()
        for indicator in error_indicators:
            if indicator.lower() in content_lower:
                return False
        
        return True 