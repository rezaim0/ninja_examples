# notification_strategy.py
"""
Module defining notification strategy classes.

This module contains the abstract base class and concrete implementations
for different types of notifications that can be sent by the system.
Each strategy handles the creation of notification content specific to
its notification type.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class NotificationStrategy(ABC):
    """
    Base strategy interface for different notification types.
    
    This abstract base class defines the interface that all notification
    strategies must implement. Each concrete strategy handles the creation
    of notification content for a specific type of notification.
    """
    
    @abstractmethod
    def create_notification_content(self, model_name: str, app_group_id: str, metadata: Dict[str, Any]) -> str:
        """
        Creates the content for a notification.
        
        Args:
            model_name: Name of the model requiring notification.
            app_group_id: ID of the application group (can be None).
            metadata: Additional metadata about the model from model_review module.
            
        Returns:
            Formatted notification content as string.
        """
        pass
    
    @abstractmethod
    def get_notification_type(self) -> str:
        """
        Returns the type identifier for this notification.
        
        Returns:
            String identifier for this notification type.
        """
        pass

class ModelReviewNotification(NotificationStrategy):
    """
    Concrete strategy for model review notifications.
    
    Handles creation of notification content when models are due for
    their 6-month review cycle.
    """
    
    def create_notification_content(self, model_name: str, app_group_id: str, metadata: Dict[str, Any]) -> str:
        """
        Creates content specific to model review notifications.
        
        Args:
            model_name: Name of the model requiring review.
            app_group_id: ID of the application group (can be None).
            metadata: Model metadata from model_review module containing:
                     - review_date: Last review date
                     - days_overdue: Days since last review
                     - model_path: S3 path to model file
                     - review_interval_days: Review interval (180 days)
            
        Returns:
            Formatted notification content for model review.
        """
        try:
            # Extract metadata with safe defaults
            review_date = metadata.get('review_date', 'Unknown')
            days_overdue = metadata.get('days_overdue', 'Unknown')
            model_path = metadata.get('model_path', 'Not available')
            review_interval = metadata.get('review_interval_days', 180)
            
            # Handle missing app_group_id gracefully
            app_group_display = app_group_id if app_group_id else 'Not specified'
            
            content = f"""Subject: IMPORTANT: Model Review Required - {model_name}

Dear Modeling Team,

Our records indicate that the model "{model_name}" is due for its {review_interval}-day review.

Model Details:
- Model Name: {model_name}
- Application Group ID: {app_group_display}
- Last Review Date: {review_date}
- Days Since Last Review: {days_overdue}
- Model File Location: {model_path}

Please schedule a review of this model at your earliest convenience. Regular reviews
ensure model quality and compliance with our organizational standards.

To review the model, please access it through MACATO and update the model_review_date
field once the review is complete.

If you have any questions or need assistance, please contact the ModelOps team.

Thank you,
MACATO System"""
            
            logger.debug(f"Created model review notification content for {model_name}")
            return content
            
        except Exception as e:
            logger.error(f"Error creating model review notification content for {model_name}: {e}")
            # Return a basic notification if content creation fails
            return f"""Subject: Model Review Required - {model_name}

Model "{model_name}" requires review. Please contact the ModelOps team for details.

MACATO System"""
    
    def get_notification_type(self) -> str:
        """Returns the notification type identifier."""
        return "model_review"

class PerformanceDegradationNotification(NotificationStrategy):
    """
    Concrete strategy for performance degradation notifications.
    
    This strategy is designed for future use when performance monitoring
    is implemented. It will handle notifications when model performance
    drops below acceptable thresholds.
    """
    
    def create_notification_content(self, model_name: str, app_group_id: str, metadata: Dict[str, Any]) -> str:
        """
        Creates content for performance degradation notifications.
        
        Args:
            model_name: Name of the model with performance issues.
            app_group_id: ID of the application group (can be None).
            metadata: Performance-related metadata including:
                     - performance_metrics: Dict of current metrics
                     - threshold: Performance threshold that was breached
                     - current_value: Current performance value
            
        Returns:
            Formatted notification content for performance degradation.
        """
        try:
            metrics = metadata.get('performance_metrics', {})
            threshold = metadata.get('threshold', 'N/A')
            current_value = metadata.get('current_value', 'N/A')
            app_group_display = app_group_id if app_group_id else 'Not specified'
            
            content = f"""Subject: ALERT: Performance Degradation Detected - {model_name}

Dear Modeling Team,

Our monitoring system has detected potential performance degradation for model "{model_name}".

Model Details:
- Model Name: {model_name}
- Application Group ID: {app_group_display}
- Performance Metrics: {metrics}
- Threshold: {threshold}
- Current Value: {current_value}

Please investigate this issue and take appropriate action to address the degradation.
Consider retraining the model or reviewing recent data changes.

For assistance, please contact the ModelOps team.

Thank you,
MACATO System"""
            
            logger.debug(f"Created performance degradation notification content for {model_name}")
            return content
            
        except Exception as e:
            logger.error(f"Error creating performance degradation notification for {model_name}: {e}")
            return f"""Subject: Performance Alert - {model_name}

Model "{model_name}" may have performance issues. Please investigate.

MACATO System"""
    
    def get_notification_type(self) -> str:
        """Returns the notification type identifier."""
        return "performance_degradation"

class EthicsAssessmentNotification(NotificationStrategy):
    """
    Concrete strategy for ethics assessment notifications.
    
    This strategy is designed for future use when ethics assessment
    tracking is implemented. It will handle notifications when models
    require ethics reviews.
    """
    
    def create_notification_content(self, model_name: str, app_group_id: str, metadata: Dict[str, Any]) -> str:
        """
        Creates content for ethics assessment notifications.
        
        Args:
            model_name: Name of the model requiring ethics assessment.
            app_group_id: ID of the application group (can be None).
            metadata: Ethics-related metadata including:
                     - ethics_assessment_date: Last ethics assessment date
                     - assessment_due_date: When assessment is due
            
        Returns:
            Formatted notification content for ethics assessment.
        """
        try:
            last_assessment = metadata.get('ethics_assessment_date', 'Unknown')
            due_date = metadata.get('assessment_due_date', 'As soon as possible')
            app_group_display = app_group_id if app_group_id else 'Not specified'
            
            content = f"""Subject: Ethics Assessment Required - {model_name}

Dear Modeling Team,

An ethics assessment is needed for model "{model_name}".

Model Details:
- Model Name: {model_name}
- Application Group ID: {app_group_display}
- Last Ethics Assessment: {last_assessment}
- Assessment Due: {due_date}

Please schedule an ethics assessment for this model to ensure compliance 
with our ethical AI guidelines and organizational policies.

For guidance on conducting ethics assessments, please refer to the 
ModelOps documentation or contact the Ethics Review Board.

Thank you,
MACATO System"""
            
            logger.debug(f"Created ethics assessment notification content for {model_name}")
            return content
            
        except Exception as e:
            logger.error(f"Error creating ethics assessment notification for {model_name}: {e}")
            return f"""Subject: Ethics Assessment Required - {model_name}

Model "{model_name}" requires ethics assessment. Please contact the Ethics Review Board.

MACATO System"""
    
    def get_notification_type(self) -> str:
        """Returns the notification type identifier."""
        return "ethics_assessment"