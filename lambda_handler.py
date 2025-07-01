"""
Main Lambda Handler for MetroVoice Podcast Automation
Entry point for AWS Lambda function
"""

import json
import logging
import os
from typing import Dict, Any, List
from datetime import datetime

from podcast_orchestrator import PodcastOrchestrator, PodcastOrchestratorError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for podcast automation
    
    Args:
        event: Lambda event containing trigger information
        context: Lambda context
        
    Returns:
        Dict containing response information
    """
    try:
        logger.info("Starting MetroVoice Podcast Automation")
        logger.info(f"Event: {json.dumps(event)}")
        
        # Initialize orchestrator
        orchestrator = PodcastOrchestrator()
        
        # Validate configuration
        if not orchestrator.validate_configuration():
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Configuration validation failed",
                    "message": "Check API keys and AWS permissions"
                })
            }
        
        # Determine what to generate based on event
        episodes_generated = []
        
        if _is_scheduled_event(event):
            # Generate episodes based on schedule
            logger.info("Processing scheduled episode generation")
            episodes_generated = orchestrator.generate_scheduled_episodes()
            
        elif _is_manual_trigger(event):
            # Generate specific episodes based on event parameters
            logger.info("Processing manual episode generation")
            episodes_generated = _process_manual_trigger(event, orchestrator)
            
        elif _is_sns_trigger(event):
            # Process SNS notification (legacy support)
            logger.info("Processing SNS trigger")
            episodes_generated = _process_sns_trigger(event, orchestrator)
            
        else:
            # Default: generate all series
            logger.info("No specific trigger found, generating all series")
            all_series = orchestrator.content_generator.config.get_all_series_ids()
            episodes_generated = orchestrator.generate_multiple_episodes(all_series)
        
        # Prepare response
        response_data = {
            "success": True,
            "episodes_generated": len(episodes_generated),
            "episodes": [
                {
                    "series_id": episode.series_id,
                    "title": episode.title,
                    "episode_id": episode.episode_id,
                    "podbean_url": episode.podbean_url,
                    "generated_at": episode.generated_at,
                    "published_at": episode.published_at
                }
                for episode in episodes_generated
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Successfully generated {len(episodes_generated)} episodes")
        
        return {
            "statusCode": 200,
            "body": json.dumps(response_data, indent=2)
        }
        
    except PodcastOrchestratorError as e:
        error_msg = f"Podcast orchestration error: {str(e)}"
        logger.error(error_msg)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Podcast orchestration failed",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        }

def _is_scheduled_event(event: Dict[str, Any]) -> bool:
    """Check if event is a scheduled CloudWatch event"""
    return (
        "source" in event and 
        event.get("source") == "aws.events" and
        "detail-type" in event and
        event.get("detail-type") == "Scheduled Event"
    )

def _is_manual_trigger(event: Dict[str, Any]) -> bool:
    """Check if event is a manual trigger with specific parameters"""
    return (
        "series_id" in event or
        "series_ids" in event or
        "action" in event
    )

def _is_sns_trigger(event: Dict[str, Any]) -> bool:
    """Check if event is an SNS notification"""
    return (
        "Records" in event and
        len(event["Records"]) > 0 and
        "Sns" in event["Records"][0]
    )

def _process_manual_trigger(event: Dict[str, Any], orchestrator: PodcastOrchestrator) -> List:
    """Process manual trigger event"""
    episodes_generated = []
    
    # Handle single series
    if "series_id" in event:
        series_id = event["series_id"]
        custom_prompt = event.get("custom_prompt")
        auto_publish = event.get("auto_publish", True)
        
        try:
            episode = orchestrator.generate_episode(
                series_id, custom_prompt, auto_publish
            )
            episodes_generated.append(episode)
        except PodcastOrchestratorError as e:
            logger.error(f"Failed to generate episode for {series_id}: {str(e)}")
    
    # Handle multiple series
    elif "series_ids" in event:
        series_ids = event["series_ids"]
        custom_prompts = event.get("custom_prompts")
        auto_publish = event.get("auto_publish", True)
        
        episodes_generated = orchestrator.generate_multiple_episodes(
            series_ids, custom_prompts, auto_publish
        )
    
    # Handle specific actions
    elif "action" in event:
        action = event["action"]
        
        if action == "status":
            # Return status instead of generating episodes
            status = orchestrator.get_series_status()
            logger.info(f"Series status: {json.dumps(status, indent=2)}")
            return []
        
        elif action == "validate":
            # Validate configuration
            is_valid = orchestrator.validate_configuration()
            logger.info(f"Configuration validation: {is_valid}")
            return []
    
    return episodes_generated

def _process_sns_trigger(event: Dict[str, Any], orchestrator: PodcastOrchestrator) -> List:
    """Process SNS trigger event (legacy support)"""
    episodes_generated = []
    
    for record in event["Records"]:
        try:
            sns_message = record["Sns"]["Message"]
            
            # Try to parse as JSON first
            try:
                message_data = json.loads(sns_message)
                series_id = message_data.get("series_id", "metro_business_brief")
            except json.JSONDecodeError:
                # Fallback to treating as plain text (legacy behavior)
                series_id = "metro_business_brief"
            
            episode = orchestrator.generate_episode(series_id)
            episodes_generated.append(episode)
            
        except Exception as e:
            logger.error(f"Error processing SNS record: {str(e)}")
            continue
    
    return episodes_generated

# Additional utility functions for testing and debugging
def get_series_status(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get status of all podcast series"""
    try:
        orchestrator = PodcastOrchestrator()
        status = orchestrator.get_series_status()
        
        return {
            "statusCode": 200,
            "body": json.dumps(status, indent=2)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Failed to get status",
                "message": str(e)
            })
        }

def validate_config(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Validate system configuration"""
    try:
        orchestrator = PodcastOrchestrator()
        is_valid = orchestrator.validate_configuration()
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "valid": is_valid,
                "timestamp": datetime.utcnow().isoformat()
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Configuration validation failed",
                "message": str(e)
            })
        } 