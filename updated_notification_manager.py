# notification_manager.py
"""
Module for the NotificationManager class that coordinates the notification process.

This module contains the main orchestrator for the notification system.
It coordinates between the model review checker, notification strategies,
and delivery mechanisms to send appropriate notifications.
"""
from typing import Dict, Any, Optional
import logging

# Import updated modules
from model_review import ModelReviewChecker
from notification_factory import NotificationFactory
from notification_strategy import NotificationStrategy

logger = logging.getLogger(__name__)

class NotificationDelivery:
    """
    Abstract base class for notification delivery methods.
    
    This is a placeholder interface that should be implemented by
    specific delivery mechanisms (email, SMS, etc.).
    """
    
    def send(self, recipient: str, subject: str, content: str) -> bool:
        """
        Send notification to recipient.
        
        Args:
            recipient: Target recipient (email address, phone number, etc.).
            subject: Subject line or title for the notification.
            content: Main content of the notification.
            
        Returns:
            True if notification was sent successfully, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement send method")

class EmailDelivery(NotificationDelivery):
    """
    Email delivery implementation.
    
    This is a placeholder implementation. In a real system, this would
    integrate with your email service (SMTP, SES, SendGrid, etc.).
    """
    
    def __init__(self, email_service=None):
        """
        Initialize email delivery service.
        
        Args:
            email_service: Email service implementation (SMTP client, API client, etc.).
        """
        self._email_service = email_service
        logger.info("Initialized EmailDelivery service")
    
    def send(self, recipient: str, subject: str, content: str) -> bool:
        """
        Send email notification.
        
        Args:
            recipient: Email address of the recipient.
            subject: Email subject line.
            content: Email body content.
            
        Returns:
            True if email was sent successfully, False otherwise.
        """
        try:
            # Placeholder implementation
            # In a real system, this would use your email service
            if self._email_service:
                # Example: self._email_service.send(recipient, subject, content)
                logger.info(f"Email sent successfully to {recipient} with subject: {subject}")
                return True
            else:
                # For testing/development - just log the email
                logger.info(f"[EMAIL SIMULATION] To: {recipient}")
                logger.info(f"[EMAIL SIMULATION] Subject: {subject}")
                logger.info(f"[EMAIL SIMULATION] Content: {content[:100]}...")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False

class NotificationManager:
    """
    Manages the notification process.
    
    This class orchestrates the entire notification workflow:
    1. Uses ModelReviewChecker to identify models needing attention
    2. Uses NotificationFactory to create appropriate notifications
    3. Uses delivery services to send notifications to recipients
    """
    
    def __init__(self, 
                 review_checker: ModelReviewChecker, 
                 delivery_method: NotificationDelivery,
                 notification_factory: NotificationFactory = None):
        """
        Initialize the notification manager.
        
        Args:
            review_checker: Checker for determining which models need review.
            delivery_method: Method for delivering notifications.
            notification_factory: Factory for creating notifications (uses default if None).
        """
        self.review_checker = review_checker
        self.delivery = delivery_method
        self.factory = notification_factory or NotificationFactory()
        
        logger.info("Initialized NotificationManager")
    
    def get_recipient_for_app_group(self, app_group_id: str) -> str:
        """
        Determine the email recipient(s) for a given app group.
        
        Args:
            app_group_id: ID of the application group (can be None).
            
        Returns:
            Email address(es) for the recipient(s).
        """
        # Handle case where app_group_id is None or empty
        if not app_group_id:
            logger.warning("No app_group_id provided, using default recipient")
            return "modelops-team@example.com"
        
        # In a real implementation, this would look up recipients from a configuration
        # database, or service based on the app_group_id
        
        # For now, create recipient email based on app_group_id
        clean_id = app_group_id.lower().replace(' ', '_').replace('-', '_')
        recipient = f"{clean_id}_team@example.com"
        
        logger.debug(f"Mapped app_group_id '{app_group_id}' to recipient '{recipient}'")
        return recipient
    
    def send_model_review_notifications(self, file_prefix: str = None) -> Dict[str, Any]:
        """
        Check for models requiring review and send notifications.
        
        Args:
            file_prefix: Optional prefix for filtering S3 objects.
            
        Returns:
            Dictionary containing notification results and statistics.
        """
        logger.info("Starting model review notification process")
        
        results = {
            'total_models_checked': 0,
            'notifications_sent': 0,
            'notifications_failed': 0,
            'errors': [],
            'successful_notifications': [],
            'failed_notifications': []
        }
        
        try:
            # Step 1: Get models due for review
            models_to_review = self.review_checker.check_models_due_for_review(file_prefix)
            
            if not models_to_review:
                logger.info("No models require review at this time")
                return results
            
            results['total_models_checked'] = len(models_to_review)
            logger.info(f"Found {len(models_to_review)} models requiring review")
            
            # Step 2: Get notification strategy
            strategy = self.factory.create_notification("model_review")
            if not strategy:
                error_msg = "No strategy available for 'model_review' notifications"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                return results
            
            # Step 3: Process each model
            for model_name, metadata in models_to_review.items():
                try:
                    app_group_id = metadata.get('app_group_id')
                    
                    # Get recipient (handles None app_group_id gracefully)
                    recipient = self.get_recipient_for_app_group(app_group_id)
                    
                    # Create notification content
                    content = strategy.create_notification_content(model_name, app_group_id, metadata)
                    
                    # Extract subject from content (first line after "Subject: ")
                    lines = content.split('\n')
                    subject = "Model Review Required"  # Default subject
                    body = content
                    
                    for line in lines:
                        if line.startswith('Subject: '):
                            subject = line.replace('Subject: ', '').strip()
                            # Remove subject line from body
                            body = '\n'.join(lines[1:]).strip()
                            break
                    
                    # Send notification
                    success = self.delivery.send(recipient, subject, body)
                    
                    if success:
                        results['notifications_sent'] += 1
                        results['successful_notifications'].append({
                            'model_name': model_name,
                            'recipient': recipient,
                            'app_group_id': app_group_id
                        })
                        logger.info(f"Successfully sent review notification for model {model_name} to {recipient}")
                    else:
                        results['notifications_failed'] += 1
                        results['failed_notifications'].append({
                            'model_name': model_name,
                            'recipient': recipient,
                            'error': 'Delivery failed'
                        })
                        logger.error(f"Failed to send review notification for model {model_name}")
                
                except Exception as e:
                    error_msg = f"Error processing model {model_name}: {str(e)}"
                    logger.error(error_msg)
                    results['notifications_failed'] += 1
                    results['errors'].append(error_msg)
                    results['failed_notifications'].append({
                        'model_name': model_name,
                        'error': str(e)
                    })
            
            logger.info(f"Notification process completed. Sent: {results['notifications_sent']}, "
                       f"Failed: {results['notifications_failed']}")
            
            return results
            
        except Exception as e:
            error_msg = f"Critical error in notification process: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    def send_custom_notification(self, 
                               notification_type: str, 
                               model_name: str, 
                               app_group_id: str, 
                               metadata: Dict[str, Any]) -> bool:
        """
        Send a custom notification for a specific model.
        
        Args:
            notification_type: Type of notification to send (e.g., "performance_degradation").
            model_name: Name of the model.
            app_group_id: ID of the application group.
            metadata: Additional metadata about the model.
            
        Returns:
            True if notification was sent successfully, False otherwise.
        """
        try:
            logger.info(f"Sending custom notification of type '{notification_type}' for model {model_name}")
            
            # Get notification strategy
            strategy = self.factory.create_notification(notification_type)
            if not strategy:
                logger.error(f"No strategy available for '{notification_type}' notifications")
                return False
            
            # Get recipient
            recipient = self.get_recipient_for_app_group(app_group_id)
            
            # Create content
            content = strategy.create_notification_content(model_name, app_group_id, metadata)
            
            # Create subject
            subject_prefix = notification_type.replace('_', ' ').title()
            subject = f"{subject_prefix} - {model_name}"
            
            # Send notification
            success = self.delivery.send(recipient, subject, content)
            
            if success:
                logger.info(f"Successfully sent {notification_type} notification for {model_name}")
            else:
                logger.error(f"Failed to send {notification_type} notification for {model_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending custom notification for {model_name}: {e}")
            return False
    
    def schedule_regular_checks(self, interval_hours: int = 24) -> None:
        """
        Set up a scheduler to regularly check for and send notifications.
        
        Args:
            interval_hours: Hours between checks.
            
        Note:
            This is a placeholder implementation. In a real system, you would
            integrate with a scheduling system like APScheduler, Celery, or
            cloud-based schedulers (AWS EventBridge, etc.).
        """
        logger.info(f"Scheduling regular notification checks every {interval_hours} hours")
        
        # Placeholder implementation
        # Example implementation with APScheduler would be:
        # from apscheduler.schedulers.background import BackgroundScheduler
        # scheduler = BackgroundScheduler()
        # scheduler.add_job(
        #     func=self.send_model_review_notifications,
        #     trigger='interval',
        #     hours=interval_hours,
        #     id='model_review_notifications'
        # )
        # scheduler.start()
        
        logger.info("Scheduler setup complete (placeholder implementation)")

# Factory function for easy setup
def create_notification_manager(bucket_name: str,
                              bucket_prefix: str = "",
                              database_name: str = "Mydag",
                              table_name: str = "modelops_docato_output",
                              email_service=None) -> NotificationManager:
    """
    Create a fully configured NotificationManager.
    
    Args:
        bucket_name: S3 bucket name containing model files.
        bucket_prefix: Optional prefix for S3 objects.
        database_name: Database name for model metadata.
        table_name: Table name containing model review data.
        email_service: Email service implementation (optional).
        
    Returns:
        Configured NotificationManager instance.
    """
    from model_review import create_model_review_checker
    
    # Create review checker
    review_checker = create_model_review_checker(
        bucket_name=bucket_name,
        bucket_prefix=bucket_prefix,
        database_name=database_name,
        table_name=table_name
    )
    
    # Create delivery service
    delivery = EmailDelivery(email_service)
    
    # Create and return notification manager
    return NotificationManager(review_checker, delivery)