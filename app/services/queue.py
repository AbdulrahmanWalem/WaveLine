"""
Redis Stream Queue Service
Handles pushing notifications to and reading from Redis Streams
"""

import json
import redis
from app.config import settings

# Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

STREAM_NAME = "notifications_stream"


def push_to_queue(notification_id: str) -> bool:
    """
    Push a notification ID to the Redis stream queue.
    
    Args:
        notification_id: UUID string of the notification to process
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client.xadd(STREAM_NAME, {"notification_id": notification_id})
        return True
    except Exception as e:
        print(f"Error pushing to queue: {e}")
        return False


def read_from_queue(block_ms: int = 1000, count: int = 10):
    """
    Read messages from the Redis stream queue.
    
    Args:
        block_ms: How long to block waiting for messages (in milliseconds)
        count: Maximum number of messages to read at once
            
    Returns:
        List of messages from the stream
    """
    try:
        messages = redis_client.xread({STREAM_NAME: "$"}, block=block_ms, count=count)
        return messages
    except Exception as e:
        print(f"Error reading from queue: {e}")
        return []


def acknowledge_message(message_id: str) -> bool:
    """
    Acknowledge a message has been processed (for consumer groups).
    
    Args:
        message_id: The ID of the message to acknowledge
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client.xack(STREAM_NAME, "waveline_group", message_id)
        return True
    except Exception as e:
        print(f"Error acknowledging message: {e}")
        return False

