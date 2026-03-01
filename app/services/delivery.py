"""
Delivery Service - Handles actual delivery of notifications
via email, webhook, and in-app channels
"""

import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


async def deliver_email(notification, app) -> tuple[bool, Optional[str]]:
    """
    Deliver notification via email using Resend SDK.
    
    Args:
        notification: Notification model instance
        app: App model instance
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        import resend
        from app.config import settings
        
        resend.api_key = settings.RESEND_API_KEY
        
        if not resend.api_key:
            return False, "RESEND_API_KEY not configured"
        
        # Use Resend sandbox for testing, or your verified domain in production
        sender_email = "onboarding@resend.dev" if settings.ENVIRONMENT == "development" else f"waveline@{app.webhook_url or 'resend.dev'}"
        
        response = resend.Emails.send({
            "from": sender_email,
            "to": notification.recipient,
            "subject": notification.title,
            "html": f"<p>{notification.body}</p>"
        })
        
        logger.info(f"Email sent successfully to {notification.recipient}, id: {response.get('id')}")
        return True, None
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False, str(e)


async def deliver_webhook(notification, app) -> tuple[bool, Optional[str]]:
    """
    Deliver notification via webhook POST to the app's webhook URL.
    
    Args:
        notification: Notification model instance
        app: App model instance
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    if not app.webhook_url:
        return False, "No webhook_url configured for this app"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                app.webhook_url,
                json={
                    "id": str(notification.id),
                    "title": notification.title,
                    "body": notification.body,
                    "recipient": notification.recipient
                },
                timeout=10.0
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook delivered successfully to {app.webhook_url}")
                return True, None
            else:
                return False, f"Webhook returned status {response.status_code}"
                
    except httpx.TimeoutException:
        return False, "Webhook request timed out"
    except Exception as e:
        logger.error(f"Failed to send webhook: {e}")
        return False, str(e)


async def deliver_inapp(notification, app) -> tuple[bool, Optional[str]]:
    """
    Deliver in-app notification (already stored in DB, just mark as sent).
    
    Args:
        notification: Notification model instance
        app: App model instance
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    # In-app notifications are already stored in the database
    # This function just confirms successful delivery
    logger.info(f"In-app notification stored for recipient: {notification.recipient}")
    return True, None


async def deliver_notification(notification, app) -> tuple[bool, Optional[str]]:
    """
    Main delivery function that routes to the appropriate channel.
    
    Args:
        notification: Notification model instance
        app: App model instance
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    from app.models.notification import ChannelEnum
    
    if notification.channel == ChannelEnum.email:
        return await deliver_email(notification, app)
    elif notification.channel == ChannelEnum.webhook:
        return await deliver_webhook(notification, app)
    elif notification.channel == ChannelEnum.inapp:
        return await deliver_inapp(notification, app)
    else:
        return False, f"Unknown channel: {notification.channel}"

