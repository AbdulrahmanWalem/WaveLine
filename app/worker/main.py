"""
Worker - Consumes notifications from Redis Stream and delivers them
"""

import asyncio
import logging
import sys
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.notification import Notification, DeliveryLog, StatusEnum
from app.models.app import App
from app.services.queue import read_from_queue, push_to_queue
from app.services.delivery import deliver_notification

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


async def process_notification(notification_id: str) -> bool:
    """
    Process a single notification: fetch from DB, deliver, log result.
    
    Args:
        notification_id: UUID string of the notification
        
    Returns:
        True if processed successfully, False otherwise
    """
    async with AsyncSessionLocal() as session:
        try:
            # Fetch notification from DB
            result = await session.execute(
                select(Notification).where(Notification.id == notification_id)
            )
            notification = result.scalar_one_or_none()
            
            if not notification:
                logger.error(f"Notification {notification_id} not found in DB")
                return False
            
            # Skip if already processed
            if notification.status in (StatusEnum.sent, StatusEnum.failed):
                logger.info(f"Notification {notification_id} already processed with status {notification.status}")
                return True
            
            # Fetch the app
            result = await session.execute(
                select(App).where(App.id == notification.app_id)
            )
            app = result.scalar_one_or_none()
            
            if not app:
                logger.error(f"App {notification.app_id} not found for notification {notification_id}")
                return False
            
            # Attempt delivery with retry logic
            success = False
            error_message = None
            
            for attempt in range(1, MAX_RETRIES + 1):
                logger.info(f"Attempting delivery for notification {notification_id}, attempt {attempt}/{MAX_RETRIES}")
                
                # Create delivery log entry
                delivery_log = DeliveryLog(
                    notification_id=notification.id,
                    attempt=attempt,
                    status=StatusEnum.pending
                )
                session.add(delivery_log)
                await session.commit()
                
                # Try to deliver
                success, error_message = await deliver_notification(notification, app)
                
                if success:
                    delivery_log.status = StatusEnum.sent
                    await session.commit()
                    break
                else:
                    delivery_log.status = StatusEnum.failed
                    delivery_log.error_message = error_message
                    await session.commit()
                    
                    if attempt < MAX_RETRIES:
                        logger.warning(f"Delivery failed, retrying in {RETRY_DELAY}s: {error_message}")
                        await asyncio.sleep(RETRY_DELAY)
            
            # Update notification status
            notification.status = StatusEnum.sent if success else StatusEnum.failed
            await session.commit()
            
            if success:
                logger.info(f"Notification {notification_id} delivered successfully")
            else:
                logger.error(f"Notification {notification_id} failed after {MAX_RETRIES} attempts: {error_message}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing notification {notification_id}: {e}")
            return False


async def worker_loop():
    """
    Main worker loop: continuously read from queue and process notifications.
    """
    logger.info("Worker started, waiting for notifications...")
    
    while True:
        try:
            # Read messages from queue (blocks for 1 second)
            messages = read_from_queue(block_ms=1000, count=10)
            
            if not messages:
                continue
            
            # Process each stream's messages
            for stream_name, stream_messages in messages:
                for message in stream_messages:
                    message_id = message["id"]
                    message_data = message["message"]
                    notification_id = message_data.get("notification_id")
                    
                    if notification_id:
                        logger.info(f"Processing notification: {notification_id}")
                        await process_notification(notification_id)
                        
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(1)


async def main():
    """Entry point for the worker"""
    logger.info("Starting Waveline Worker...")
    await worker_loop()


if __name__ == "__main__":
    asyncio.run(main())

