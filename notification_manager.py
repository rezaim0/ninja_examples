# notification_manager.py
"""
Module for the NotificationManager class that coordinates the notification process.

This module contains the main orchestrator for the notification system.
It coordinates between the model review checker, notification strategies,
and CSV file generation to create notification files for Data Engineering teams.
"""
from typing import Dict, Any, Optional
from loguru import logger
# Import updated modules
from model_review import ModelReviewChecker
from notification_factory import NotificationFactory
from notification_strategy import NotificationStrategy
from notification_delivery import NotificationDelivery, create_json_delivery


class NotificationManager:
    """
    Manages the notification process.
    
    This class orchestrates the entire notification workflow:
    1. Uses ModelReviewChecker to identify models needing attention
    2. Uses NotificationFactory to create appropriate notifications
    3. Uses NotificationDelivery to generate CSV files for Data Engineering teams
    """
    
    def __init__(self, 
                 review_checker: ModelReviewChecker, 
                 delivery_service: NotificationDelivery,
                 notification_factory: NotificationFactory = None):
        """
        Initialize the notification manager.
        
        Args:
            review_checker: Checker for determining which models need review.
            delivery_service: Service for generating CSV notification files.
            notification_factory: Factory for creating notifications (uses default if None).
        """
        self.review_checker = review_checker
        self.delivery = delivery_service
        self.factory = notification_factory or NotificationFactory()
        
        logger.info("Initialized NotificationManager")
    
    def send_model_review_notifications(self, file_prefix: str = None) -> Dict[str, Any]:
        """
        Check for models requiring review and generate notification JSON files.
        
        This method orchestrates the complete notification workflow:
        1. Gets models needing review from ModelReviewChecker
        2. Creates notification content using strategy pattern
        3. Generates individual JSON files for each notification
        
        Args:
            file_prefix: Optional prefix for filtering S3 objects.
            
        Returns:
            Dictionary containing notification results and statistics.
            
        Example Result:
            {
                'total_models_checked': 15,
                'notifications_generated': 8,
                'notifications_failed': 0,
                'json_files_created': 8,
                'output_directory': './emails_dir/sent_emails',
                'successful_notifications': [
                    {'model_name': 'model_a', 'aap_group_id': 'group_123', 'filename': 'email_group_123_20241220.json'},
                    ...
                ],
                'errors': []
            }
        """
        logger.info("Starting model review notification process")
        
        results = {
            'total_models_checked': 0,
            'notifications_generated': 0,
            'notifications_failed': 0,
            'json_files_created': 0,
            'output_directory': str(self.delivery.get_output_directory()),
            'successful_notifications': [],
            'failed_notifications': [],
            'errors': []
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
            
            # Step 3: Process each model and generate JSON files
            files_before = self.delivery.get_file_count()
            
            for model_name, metadata in models_to_review.items():
                try:
                    app_group_id = metadata.get('app_group_id')
                    
                    # Skip models without app_group_id since Data Engineering needs it for email lookup
                    if not app_group_id:
                        warning_msg = f"Skipping model {model_name}: no app_group_id found"
                        logger.warning(warning_msg)
                        results['failed_notifications'].append({
                            'model_name': model_name,
                            'error': 'Missing app_group_id'
                        })
                        results['notifications_failed'] += 1
                        continue
                    
                    # Create notification content using strategy
                    content = strategy.create_notification_content(model_name, app_group_id, metadata)
                    
                    # Create subject line
                    subject = f"IMPORTANT: Model Review Required - {model_name}"
                    
                    # Prepare metadata for JSON file
                    json_metadata = {
                        'model_name': model_name,
                        'app_group_id': app_group_id,
                        'review_date': metadata.get('review_date'),
                        'days_overdue': metadata.get('days_overdue'),
                        'model_path': metadata.get('model_path'),
                        'review_interval_days': metadata.get('review_interval_days'),
                        'notification_date': metadata.get('notification_date')
                    }
                    
                    # Generate JSON notification file
                    success = self.delivery.send(
                        aap_group_id=app_group_id,
                        subject=subject,
                        content=content,
                        model_name=model_name,
                        notification_type="model_review",
                        metadata=json_metadata
                    )
                    
                    if success:
                        results['notifications_generated'] += 1
                        results['successful_notifications'].append({
                            'model_name': model_name,
                            'aap_group_id': app_group_id,
                            'subject': subject
                        })
                        logger.info(f"Generated JSON notification for model {model_name} (app_group_id: {app_group_id})")
                    else:
                        results['notifications_failed'] += 1
                        results['failed_notifications'].append({
                            'model_name': model_name,
                            'aap_group_id': app_group_id,
                            'error': 'Failed to generate JSON file'
                        })
                        logger.error(f"Failed to generate JSON notification for model {model_name}")
                
                except Exception as e:
                    error_msg = f"Error processing model {model_name}: {str(e)}"
                    logger.error(error_msg)
                    results['notifications_failed'] += 1
                    results['errors'].append(error_msg)
                    results['failed_notifications'].append({
                        'model_name': model_name,
                        'error': str(e)
                    })
            
            # Step 4: Calculate files created
            files_after = self.delivery.get_file_count()
            results['json_files_created'] = files_after - files_before
            
            logger.info(f"Notification process completed. Generated: {results['notifications_generated']} JSON files, "
                       f"Failed: {results['notifications_failed']}")
            
            # Show generated files for debugging
            if results['notifications_generated'] > 0:
                recent_files = self.delivery.get_generated_files()[:results['notifications_generated']]
                logger.info(f"Generated JSON files: {[Path(f).name for f in recent_files]}")
            
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
        
        Generates a JSON file for a single custom notification (e.g., performance 
        degradation, ethics assessment).
        
        Args:
            notification_type: Type of notification to send (e.g., "performance_degradation").
            model_name: Name of the model.
            app_group_id: ID of the application group.
            metadata: Additional metadata about the model.
            
        Returns:
            True if JSON notification file was generated successfully, False otherwise.
        """
        try:
            logger.info(f"Generating custom notification of type '{notification_type}' for model {model_name}")
            
            # Get notification strategy
            strategy = self.factory.create_notification(notification_type)
            if not strategy:
                logger.error(f"No strategy available for '{notification_type}' notifications")
                return False
            
            # Create content using strategy
            content = strategy.create_notification_content(model_name, app_group_id, metadata)
            
            # Create subject
            subject_prefix = notification_type.replace('_', ' ').title()
            subject = f"{subject_prefix} - {model_name}"
            
            # Generate JSON file
            success = self.delivery.send(
                aap_group_id=app_group_id,
                subject=subject,
                content=content,
                model_name=model_name,
                notification_type=notification_type,
                metadata=metadata
            )
            
            if success:
                logger.info(f"Generated {notification_type} JSON notification for {model_name}")
            else:
                logger.error(f"Failed to generate {notification_type} JSON notification for {model_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error generating custom notification for {model_name}: {e}")
            return False
    
    def get_delivery_status(self) -> Dict[str, Any]:
        """
        Get status information about the delivery service.
        
        Returns:
            Dictionary with delivery service status and JSON file information.
        """
        try:
            generated_files = self.delivery.get_generated_files()
            
            return {
                'output_directory': str(self.delivery.get_output_directory()),
                'total_json_files': len(generated_files),
                'recent_files': [Path(f).name for f in generated_files[:5]],  # Show 5 most recent
                'oldest_file': Path(generated_files[-1]).name if generated_files else None,
                'newest_file': Path(generated_files[0]).name if generated_files else None
            }
        except Exception as e:
            logger.error(f"Error getting delivery status: {e}")
            return {
                'error': str(e)
            }

# Factory function for easy setup
def create_notification_manager(bucket_name: str,
                              bucket_prefix: str = "",
                              table_name: str = "output",
                              output_directory: str = "./emails_dir/sent_emails") -> NotificationManager:
    """
    Create a fully configured NotificationManager.
    
    Args:
        bucket_name: S3 bucket name containing model files.
        bucket_prefix: Optional prefix for S3 objects.
        table_name: Table identifier for database (config key like "output").
        output_directory: Directory for JSON notification files.
        
    Returns:
        Configured NotificationManager instance.
        
    Example:
        >>> manager = create_notification_manager(
        ...     bucket_name="my-model-bucket",
        ...     bucket_prefix="models/production/",
        ...     output_directory="./emails/outbox"
        ... )
        >>> results = manager.send_model_review_notifications()
        >>> print(f"Generated {results['json_files_created']} JSON files")
    """
    from model_review import create_model_review_checker
    
    # Create review checker
    review_checker = create_model_review_checker(
        bucket_name=bucket_name,
        bucket_prefix=bucket_prefix,
        table_name=table_name
    )
    
    # Create JSON delivery service
    delivery = create_json_delivery(output_directory)
    
    # Create and return notification manager
    return NotificationManager(review_checker, delivery)

# Example usage function
def run_notification_process(bucket_name: str, 
                           output_directory: str = "./emails_dir/sent_emails",
                           file_prefix: str = None) -> Dict[str, Any]:
    """
    Complete example of running the notification process.
    
    Args:
        bucket_name: S3 bucket name containing model files.
        output_directory: Directory where JSON files will be generated.
        file_prefix: Optional S3 prefix for filtering model files.
        
    Returns:
        Results dictionary from the notification process.
        
    Example:
        >>> results = run_notification_process(
        ...     bucket_name="my-model-bucket",
        ...     output_directory="./emails/outbox"
        ... )
        >>> print(f"Generated {results['json_files_created']} JSON notification files")
        >>> print(f"Files saved to: {results['output_directory']}")
    """
    try:
        # Create notification manager
        manager = create_notification_manager(
            bucket_name=bucket_name,
            output_directory=output_directory
        )
        
        # Run the notification process
        results = manager.send_model_review_notifications(file_prefix)
        
        # Log summary
        logger.info(f"Notification process completed:")
        logger.info(f"  Models checked: {results['total_models_checked']}")
        logger.info(f"  JSON files generated: {results['json_files_created']}")
        logger.info(f"  Notifications sent: {results['notifications_generated']}")
        logger.info(f"  Failures: {results['notifications_failed']}")
        logger.info(f"  Output directory: {results['output_directory']}")
        
        if results['errors']:
            logger.warning(f"  Errors encountered: {len(results['errors'])}")
            for error in results['errors']:
                logger.warning(f"    - {error}")
        
        return results
        
    except Exception as e:
        error_msg = f"Failed to run notification process: {e}"
        logger.error(error_msg)
        return {
            'total_models_checked': 0,
            'notifications_generated': 0,
            'notifications_failed': 0,
            'json_files_created': 0,
            'output_directory': output_directory,
            'errors': [error_msg]
        }