# notification_strategy.py
"""
Module defining notification strategy classes.

This module contains the abstract base class and concrete implementations
for different types of notifications that can be sent by the system.
Each strategy handles the creation of notification content specific to
its notification type.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from loguru import logger
import html


@dataclass(frozen=True)
class ValidatedModelReviewData:
    """Immutable data class for validated model review data."""
    model_name_escaped: str
    app_group_display_escaped: str
    review_date_escaped: str
    days_overdue: int
    model_path_escaped: str
    review_interval: int
    notification_date_escaped: str
    
    def __post_init__(self):
        """Validate data after initialization."""
        if self.days_overdue < 0:
            raise ValueError(f"days_overdue cannot be negative, got {self.days_overdue}")
        if self.review_interval <= 0:
            raise ValueError(f"review_interval must be positive, got {self.review_interval}")


@dataclass(frozen=True)
class ValidatedPerformanceData:
    """Immutable data class for validated performance degradation data."""
    model_name_escaped: str
    app_group_display_escaped: str
    performance_metrics_escaped: str
    threshold_escaped: str
    current_value_escaped: str
    detection_date_escaped: str
    metric_name_escaped: str


@dataclass(frozen=True)
class ValidatedEthicsData:
    """Immutable data class for validated ethics assessment data."""
    model_name_escaped: str
    app_group_display_escaped: str
    last_assessment_escaped: str
    due_date_escaped: str
    risk_level_escaped: str
    compliance_requirements: List[str]
    model_category_escaped: str
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not isinstance(self.compliance_requirements, list):
            raise TypeError(f"compliance_requirements must be a list, got {type(self.compliance_requirements).__name__}")


class NotificationConfig:
    """Configuration constants for notifications."""
    
    # Review settings
    REVIEW_INTERVAL_DAYS = 180
    DEFAULT_REVIEW_INTERVAL = 180
    MIN_DAYS_OVERDUE = 0
    
    # Display constants
    REVIEW_BADGE_TEXT_FORMAT = "Every {} days"
    APP_GROUP_NOT_SPECIFIED = "Not specified"
    
    # Urgency thresholds (days overdue)
    URGENCY_THRESHOLDS = {
        'critical': 60,
        'high': 30,
        'medium': 7
    }
    
    # Urgency styling
    URGENCY_STYLES = {
        'critical': {
            'style': "background-color: #dc3545; color: white;",
            'text': "CRITICALLY OVERDUE"
        },
        'high': {
            'style': "background-color: #fd7e14; color: white;",
            'text': "OVERDUE"
        },
        'medium': {
            'style': "background-color: #ffc107; color: black;",
            'text': "RECENTLY OVERDUE"
        },
        'default': {
            'style': "background-color: #dc3545; color: white;",
            'text': "OVERDUE"
        }
    }


class NotificationStrategy(ABC):
    """
    Base strategy interface for different notification types.
    
    This abstract base class defines the interface that all notification
    strategies must implement. Each concrete strategy handles the creation
    of notification content for a specific type of notification.
    """
    
    @abstractmethod
    def create_notification_content(self, model_name: str, app_group_id: Optional[str], metadata: Dict[str, Any]) -> str:
        """
        Creates the content for a notification.
        
        Args:
            model_name: Name of the model requiring notification.
            app_group_id: ID of the application group (can be None).
            metadata: Additional metadata about the model from model_review module.
            
        Returns:
            Formatted notification content as string.
            
        Raises:
            ValueError: If model_name is empty or metadata is invalid.
            TypeError: If metadata is not a dictionary.
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
    
    @abstractmethod
    def get_notification_icon(self) -> str:
        """
        Returns the icon for this notification type.
        
        Returns:
            Emoji or icon string for this notification type.
        """
        pass
    
    @abstractmethod
    def get_notification_color_scheme(self) -> Dict[str, str]:
        """
        Returns the color scheme for this notification type.
        
        Returns:
            Dictionary with color values for the notification theme.
        """
        pass
    
    def _validate_inputs(self, model_name: str, metadata: Dict[str, Any]) -> None:
        """
        Validates input parameters for notification creation.
        
        Args:
            model_name: Name of the model requiring notification.
            metadata: Additional metadata about the model.
            
        Raises:
            ValueError: If model_name is empty.
            TypeError: If metadata is not a dictionary.
        """
        if not model_name or not model_name.strip():
            raise ValueError("model_name cannot be empty or whitespace")
        
        if not isinstance(metadata, dict):
            raise TypeError(f"metadata must be a dictionary, got {type(metadata).__name__}")
    
    def _safe_create_content(self, model_name: str, app_group_id: Optional[str], metadata: Dict[str, Any]) -> str:
        """
        Safely creates notification content with error handling.
        
        Args:
            model_name: Name of the model requiring notification.
            app_group_id: ID of the application group (can be None).
            metadata: Additional metadata about the model.
            
        Returns:
            Formatted notification content as string.
        """
        try:
            # Validate inputs first
            self._validate_inputs(model_name, metadata)
            return self.create_notification_content(model_name, app_group_id, metadata)
        except Exception as e:
            logger.error(
                f"Error creating {self.get_notification_type()} notification",
                extra={
                    "model_name": model_name,
                    "app_group_id": app_group_id,
                    "notification_type": self.get_notification_type(),
                    "error": str(e)
                }
            )
            return self._get_fallback_content(model_name)
    
    def _get_fallback_content(self, model_name: str) -> str:
        """
        Generates basic fallback content when content creation fails.
        
        Args:
            model_name: Name of the model requiring notification.
            
        Returns:
            Basic HTML notification content.
        """
        escaped_model_name = html.escape(model_name)
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.get_notification_type().replace('_', ' ').title()} Required</title>
</head>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f8f9fa;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px;">
        <h2 style="color: #dc3545;">{self.get_notification_type().replace('_', ' ').title()} Required - {escaped_model_name}</h2>
        <p>Model "<strong>{escaped_model_name}</strong>" requires attention. Please contact the ModelOps team for details.</p>
        <hr>
        <p style="font-size: 12px; color: #6c757d;"><em>MACATO System</em></p>
    </div>
</body>
</html>"""
    
    def _create_base_html_template(self, title: str, content_sections: List[str], metadata: Dict[str, Any], 
                                 custom_header_content: Optional[str] = None) -> str:
        """
        Creates a base HTML template that can be used by all notification types.
        
        Args:
            title: The main title for the notification.
            content_sections: List of HTML content sections to include.
            metadata: Metadata for footer information.
            custom_header_content: Optional custom content to add to the header (e.g., urgency badge).
            
        Returns:
            Complete HTML notification template.
        """
        icon = self.get_notification_icon()
        colors = self.get_notification_color_scheme()
        notification_date = html.escape(str(metadata.get('notification_date', 'Unknown')))
        
        # Join content sections
        content_html = '\n'.join(content_sections)
        
        # Add custom header content if provided
        header_extra = f"\n{custom_header_content}" if custom_header_content else ""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>{self._generate_base_html_styles()}</style>
</head>
<body>
    <div class="container">
        <div class="header" style="background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']});">
            <h1>{icon} {html.escape(title)}</h1>{header_extra}
        </div>
        
        <div class="content">
            {content_html}
            
            <div class="emphasis">
                <p><strong>⚠️ Important:</strong> This notification requires your attention. Please take appropriate action as outlined above.</p>
            </div>
            
            <p>If you have any questions or need assistance, please contact the ModelOps team.</p>
        </div>
        
        <div class="footer">
            <p><strong>📧 MACATO System - Automated Notification</strong></p>
            <p>🕒 Generated on: {notification_date}</p>
            <p>This is an automated notification. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>"""
    
    def _generate_base_html_styles(self) -> str:
        """
        Generates base CSS styles that are common to all notification types.
        
        Returns:
            CSS styles as a string.
        """
        return """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            color: white;
            padding: 30px 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }
        .content {
            padding: 30px;
        }
        .alert {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 25px;
            border-left: 4px solid #ffb700;
        }
        .alert-text {
            color: #856404;
            font-weight: 600;
            margin: 0;
        }
        .section-title {
            color: #495057;
            font-size: 18px;
            font-weight: 600;
            margin: 25px 0 15px 0;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 8px;
        }
        .details-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: #fff;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .details-table th,
        .details-table td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        .details-table th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
            width: 40%;
        }
        .details-table tr:last-child td {
            border-bottom: none;
        }
        .details-table tr:hover {
            background-color: #f8f9fa;
        }
        .code-text, .model-path {
            font-family: 'Courier New', monospace;
            background-color: #f1f3f4;
            padding: 4px 8px;
            border-radius: 4px;
            word-break: break-all;
            font-size: 12px;
        }
        .action-section {
            background: linear-gradient(135deg, #e7f3ff, #cce7ff);
            border: 1px solid #b3d7ff;
            border-radius: 8px;
            padding: 25px;
            margin: 25px 0;
        }
        .action-title {
            color: #0056b3;
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 15px;
        }
        .action-list {
            margin: 0;
            padding-left: 20px;
        }
        .action-list li {
            margin-bottom: 8px;
            color: #495057;
        }
        .action-list strong {
            color: #0056b3;
        }
        .footer {
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #e9ecef;
        }
        .footer p {
            margin: 5px 0;
            font-size: 12px;
            color: #6c757d;
        }
        .emphasis {
            background-color: #fff9c4;
            border-left: 4px solid #ffb700;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 6px 6px 0;
        }
        .highlight-value, .days-overdue {
            color: #dc3545;
            font-weight: bold;
            font-size: 16px;
        }
        .urgency-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 12px;
            margin-top: 10px;
            display: inline-block;
        }
        """


class ModelReviewNotification(NotificationStrategy):
    """
    Concrete strategy for model review notifications.
    
    Handles creation of notification content when models are due for
    their 6-month review cycle.
    """
    
    def create_notification_content(self, model_name: str, app_group_id: Optional[str], metadata: Dict[str, Any]) -> str:
        """
        Creates HTML content specific to model review notifications.
        
        Args:
            model_name: Name of the model requiring review.
            app_group_id: ID of the application group (can be None).
            metadata: Model metadata from model_review module containing:
                     - review_date: Last review date
                     - days_overdue: Days since last review
                     - model_path: S3 path to model file
                     - review_interval_days: Review interval (180 days)
            
        Returns:
            Formatted HTML notification content for model review.
            
        Raises:
            ValueError: If required metadata fields are missing or invalid.
        """
        # Validate inputs
        self._validate_inputs(model_name, metadata)
        self._validate_review_metadata(metadata)
        
        # Extract and validate metadata
        validated_data = self._extract_and_validate_metadata(model_name, app_group_id, metadata)
        
        # Create urgency badge HTML
        urgency_info = self._create_urgency_badge(validated_data.days_overdue)
        urgency_badge_html = f'<span class="urgency-badge" style="{urgency_info["style"]}">{urgency_info["text"]}</span>'
        
        # Create content sections
        content_sections = [
            self._create_alert_section(validated_data),
            self._create_details_section(validated_data),
            self._create_action_section(validated_data.review_interval)
        ]
        
        title = f"Model Review Required - {validated_data.model_name_escaped}"
        
        logger.debug(
            f"Created model review notification",
            extra={
                "model_name": model_name,
                "app_group_id": app_group_id,
                "days_overdue": validated_data.days_overdue,
                "notification_type": self.get_notification_type()
            }
        )
        
        return self._create_base_html_template(title, content_sections, metadata, urgency_badge_html)
    
    def _validate_review_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Validates review-specific metadata fields.
        
        Args:
            metadata: Model metadata dictionary.
            
        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if 'days_overdue' in metadata:
            days_overdue = metadata['days_overdue']
            if not isinstance(days_overdue, (int, float)):
                raise ValueError(f"days_overdue must be a number, got {type(days_overdue).__name__}")
    
    def _extract_and_validate_metadata(self, model_name: str, app_group_id: Optional[str], 
                                      metadata: Dict[str, Any]) -> ValidatedModelReviewData:
        """
        Extracts and validates metadata with safe defaults and HTML escaping.
        
        Args:
            model_name: Name of the model requiring review.
            app_group_id: ID of the application group (can be None).
            metadata: Model metadata dictionary.
            
        Returns:
            Dataclass with validated and escaped data.
        """
        # Extract metadata with safe defaults
        review_date = metadata.get('review_date', 'Unknown')
        days_overdue = self._get_days_overdue(metadata)
        model_path = metadata.get('model_path', 'Not available')
        review_interval = metadata.get('review_interval_days', NotificationConfig.DEFAULT_REVIEW_INTERVAL)
        notification_date = metadata.get('notification_date', 'Unknown')
        
        # Handle missing app_group_id gracefully
        app_group_display = app_group_id if app_group_id else NotificationConfig.APP_GROUP_NOT_SPECIFIED
        
        # Create and return immutable dataclass instance
        return ValidatedModelReviewData(
            model_name_escaped=html.escape(str(model_name)),
            app_group_display_escaped=html.escape(str(app_group_display)),
            review_date_escaped=html.escape(str(review_date)),
            days_overdue=days_overdue,
            model_path_escaped=html.escape(str(model_path)),
            review_interval=review_interval,
            notification_date_escaped=html.escape(str(notification_date))
        )
    
    def _get_days_overdue(self, metadata: Dict[str, Any]) -> int:
        """
        Safely extracts and validates days_overdue from metadata.
        
        Args:
            metadata: Model metadata dictionary.
            
        Returns:
            Validated days_overdue as integer.
        """
        days_overdue = metadata.get('days_overdue', 0)
        if not isinstance(days_overdue, (int, float)):
            logger.warning(f"Invalid days_overdue value: {days_overdue}, defaulting to 0")
            return NotificationConfig.MIN_DAYS_OVERDUE
        return max(NotificationConfig.MIN_DAYS_OVERDUE, int(days_overdue))  # Ensure non-negative integer
    
    def _create_urgency_badge(self, days_overdue: int) -> Dict[str, str]:
        """
        Creates urgency styling and text based on days overdue.
        
        Args:
            days_overdue: Number of days the review is overdue.
            
        Returns:
            Dictionary with 'style' and 'text' keys for urgency display.
        """
        thresholds = NotificationConfig.URGENCY_THRESHOLDS
        styles = NotificationConfig.URGENCY_STYLES
        
        if days_overdue > thresholds['critical']:
            return styles['critical']
        elif days_overdue > thresholds['high']:
            return styles['high']
        elif days_overdue > thresholds['medium']:
            return styles['medium']
        else:
            return styles['default']
    
    def _create_alert_section(self, validated_data: ValidatedModelReviewData) -> str:
        """
        Creates the alert section for model review.
        
        Args:
            validated_data: Dataclass with validated and escaped data.
            
        Returns:
            HTML string for the alert section.
        """
        return f"""
            <div class="alert">
                <p class="alert-text">
                    The model "<strong>{validated_data.model_name_escaped}</strong>" is due for its 
                    {validated_data.review_interval}-day review cycle.
                </p>
            </div>
        """
    
    def _create_details_section(self, validated_data: ValidatedModelReviewData) -> str:
        """
        Creates the details section for model review.
        
        Args:
            validated_data: Dataclass with validated and escaped data.
            
        Returns:
            HTML string for the details section.
        """
        return f"""
            <h2 class="section-title">📊 Model Details</h2>
            <table class="details-table">
                <tr>
                    <th>🏷️ Model Name</th>
                    <td><strong>{validated_data.model_name_escaped}</strong></td>
                </tr>
                <tr>
                    <th>👥 Application Group</th>
                    <td>{validated_data.app_group_display_escaped}</td>
                </tr>
                <tr>
                    <th>📅 Last Review Date</th>
                    <td>{validated_data.review_date_escaped}</td>
                </tr>
                <tr>
                    <th>⏰ Days Since Review</th>
                    <td><span class="days-overdue">{validated_data.days_overdue}</span></td>
                </tr>
                <tr>
                    <th>📂 Model File Location</th>
                    <td><code class="model-path">{validated_data.model_path_escaped}</code></td>
                </tr>
                <tr>
                    <th>🔄 Review Interval</th>
                    <td>{NotificationConfig.REVIEW_BADGE_TEXT_FORMAT.format(validated_data.review_interval)}</td>
                </tr>
            </table>
        """
    
    def _create_action_section(self, review_interval: int) -> str:
        """
        Creates the action section for model review.
        
        Args:
            review_interval: Review interval in days.
            
        Returns:
            HTML string for the action section.
        """
        return f"""
            <div class="action-section">
                <div class="action-title">📋 Next Steps Required:</div>
                <ol class="action-list">
                    <li><strong>Access the model</strong> through MACATO system</li>
                    <li><strong>Perform comprehensive review</strong> including:
                        <ul>
                            <li>Model performance validation</li>
                            <li>Data quality assessment</li>
                            <li>Business requirements alignment</li>
                            <li>Compliance and governance checks</li>
                        </ul>
                    </li>
                    <li><strong>Update the model_review_date field</strong> once review is completed</li>
                    <li><strong>Document any findings</strong> or required actions</li>
                </ol>
            </div>
        """
    
    def get_notification_type(self) -> str:
        """Returns the notification type identifier."""
        return "model_review"
    
    def get_notification_icon(self) -> str:
        """Returns the icon for model review notifications."""
        return "🔔"
    
    def get_notification_color_scheme(self) -> Dict[str, str]:
        """Returns the color scheme for model review notifications."""
        return {
            'primary': '#007bff',
            'secondary': '#0056b3'
        }


class PerformanceDegradationNotification(NotificationStrategy):
    """
    Concrete strategy for performance degradation notifications.
    
    This strategy handles notifications when model performance
    drops below acceptable thresholds.
    """
    
    def create_notification_content(self, model_name: str, app_group_id: Optional[str], metadata: Dict[str, Any]) -> str:
        """
        Creates HTML content for performance degradation notifications.
        
        Args:
            model_name: Name of the model with performance issues.
            app_group_id: ID of the application group (can be None).
            metadata: Performance-related metadata including:
                     - performance_metrics: Dict of current metrics
                     - threshold: Performance threshold that was breached
                     - current_value: Current performance value
                     - detection_date: When the issue was detected
            
        Returns:
            Formatted HTML notification content for performance degradation.
            
        Raises:
            ValueError: If required metadata fields are missing or invalid.
        """
        # Validate inputs
        self._validate_inputs(model_name, metadata)
        
        # Extract and validate metadata
        validated_data = self._extract_and_validate_metadata(model_name, app_group_id, metadata)
        
        # Create content sections
        content_sections = [
            self._create_alert_section(validated_data),
            self._create_details_section(validated_data),
            self._create_action_section()
        ]
        
        title = f"Performance Alert - {validated_data['model_name_escaped']}"
        
        logger.debug(
            f"Created performance degradation notification",
            extra={
                "model_name": model_name,
                "app_group_id": app_group_id,
                "metric_name": metadata.get('metric_name'),
                "notification_type": self.get_notification_type()
            }
        )
        
        return self._create_base_html_template(title, content_sections, metadata)
    
    def _extract_and_validate_metadata(self, model_name: str, app_group_id: Optional[str], 
                                      metadata: Dict[str, Any]) -> ValidatedPerformanceData:
        """
        Extracts and validates metadata with safe defaults and HTML escaping.
        
        Args:
            model_name: Name of the model with performance issues.
            app_group_id: ID of the application group (can be None).
            metadata: Performance metadata dictionary.
            
        Returns:
            Dataclass with validated and escaped data.
        """
        # Extract metadata with safe defaults
        performance_metrics = metadata.get('performance_metrics', {})
        threshold = metadata.get('threshold', 'Not specified')
        current_value = metadata.get('current_value', 'Not available')
        detection_date = metadata.get('detection_date', 'Unknown')
        metric_name = metadata.get('metric_name', 'Performance metric')
        
        # Handle missing app_group_id gracefully
        app_group_display = app_group_id if app_group_id else NotificationConfig.APP_GROUP_NOT_SPECIFIED
        
        # Create and return immutable dataclass instance
        return ValidatedPerformanceData(
            model_name_escaped=html.escape(str(model_name)),
            app_group_display_escaped=html.escape(str(app_group_display)),
            performance_metrics_escaped=html.escape(str(performance_metrics)),
            threshold_escaped=html.escape(str(threshold)),
            current_value_escaped=html.escape(str(current_value)),
            detection_date_escaped=html.escape(str(detection_date)),
            metric_name_escaped=html.escape(str(metric_name))
        )
    
    def _create_alert_section(self, validated_data: ValidatedPerformanceData) -> str:
        """
        Creates the alert section for performance degradation.
        
        Args:
            validated_data: Dataclass with validated and escaped data.
            
        Returns:
            HTML string for the alert section.
        """
        return f"""
            <div class="alert">
                <p class="alert-text">
                    Performance degradation detected for model "<strong>{validated_data.model_name_escaped}</strong>". 
                    Immediate investigation and corrective action required.
                </p>
            </div>
        """
    
    def _create_details_section(self, validated_data: ValidatedPerformanceData) -> str:
        """
        Creates the details section for performance degradation.
        
        Args:
            validated_data: Dataclass with validated and escaped data.
            
        Returns:
            HTML string for the details section.
        """
        return f"""
            <h2 class="section-title">⚠️ Performance Alert Details</h2>
            
            <table class="details-table">
                <tr>
                    <th>🏷️ Model Name</th>
                    <td><strong>{validated_data.model_name_escaped}</strong></td>
                </tr>
                <tr>
                    <th>👥 Application Group</th>
                    <td>{validated_data.app_group_display_escaped}</td>
                </tr>
                <tr>
                    <th>📊 Metric</th>
                    <td>{validated_data.metric_name_escaped}</td>
                </tr>
                <tr>
                    <th>🎯 Expected Threshold</th>
                    <td><code class="code-text">{validated_data.threshold_escaped}</code></td>
                </tr>
                <tr>
                    <th>📉 Current Value</th>
                    <td><span class="highlight-value">{validated_data.current_value_escaped}</span></td>
                </tr>
                <tr>
                    <th>📅 Detection Date</th>
                    <td>{validated_data.detection_date_escaped}</td>
                </tr>
                <tr>
                    <th>📈 Performance Metrics</th>
                    <td><code class="code-text">{validated_data.performance_metrics_escaped}</code></td>
                </tr>
            </table>
        """
    
    def _create_action_section(self) -> str:
        """
        Creates the action section for performance degradation.
        
        Returns:
            HTML string for the action section.
        """
        return """
            <div class="action-section">
                <div class="action-title">🔧 Immediate Actions Required:</div>
                <ol class="action-list">
                    <li><strong>Investigate the root cause</strong> of performance degradation:
                        <ul>
                            <li>Review recent data changes or data quality issues</li>
                            <li>Check for infrastructure or deployment changes</li>
                            <li>Analyze model input distributions</li>
                        </ul>
                    </li>
                    <li><strong>Assess impact</strong> on business operations and users</li>
                    <li><strong>Consider corrective actions</strong>:
                        <ul>
                            <li>Model retraining with recent data</li>
                            <li>Rollback to previous model version</li>
                            <li>Adjustment of model parameters</li>
                        </ul>
                    </li>
                    <li><strong>Document findings</strong> and actions taken</li>
                    <li><strong>Update monitoring thresholds</strong> if necessary</li>
                </ol>
            </div>
        """
    
    def get_notification_type(self) -> str:
        """Returns the notification type identifier."""
        return "performance_degradation"
    
    def get_notification_icon(self) -> str:
        """Returns the icon for performance degradation notifications."""
        return "📉"
    
    def get_notification_color_scheme(self) -> Dict[str, str]:
        """Returns the color scheme for performance degradation notifications."""
        return {
            'primary': '#dc3545',
            'secondary': '#c82333'
        }


# class EthicsAssessmentNotification(NotificationStrategy):
#     """
#     Concrete strategy for ethics assessment notifications.
    
#     This strategy handles notifications when models require ethics reviews
#     to ensure compliance with ethical AI guidelines.
#     """
    
#     def create_notification_content(self, model_name: str, app_group_id: Optional[str], metadata: Dict[str, Any]) -> str:
#         """
#         Creates HTML content for ethics assessment notifications.
        
#         Args:
#             model_name: Name of the model requiring ethics assessment.
#             app_group_id: ID of the application group (can be None).
#             metadata: Ethics-related metadata including:
#                      - ethics_assessment_date: Last ethics assessment date
#                      - assessment_due_date: When assessment is due
#                      - risk_level: Risk level of the model
#                      - compliance_requirements: Specific compliance needs
            
#         Returns:
#             Formatted HTML notification content for ethics assessment.
            
#         Raises:
#             ValueError: If required metadata fields are missing or invalid.
#         """
#         # Validate inputs
#         self._validate_inputs(model_name, metadata)
#         self._validate_ethics_metadata(metadata)
        
#         # Extract and validate metadata
#         validated_data = self._extract_and_validate_metadata(model_name, app_group_id, metadata)
        
#         # Create content sections
#         content_sections = [
#             self._create_alert_section(validated_data),
#             self._create_details_section(validated_data),
#             self._create_action_section(validated_data)
#         ]
        
#         title = f"Ethics Assessment Required - {validated_data['model_name_escaped']}"
        
#         logger.debug(
#             f"Created ethics assessment notification",
#             extra={
#                 "model_name": model_name,
#                 "app_group_id": app_group_id,
#                 "risk_level": metadata.get('risk_level'),
#                 "notification_type": self.get_notification_type()
#             }
#         )
        
#         return self._create_base_html_template(title, content_sections, metadata)
    
#     def _validate_ethics_metadata(self, metadata: Dict[str, Any]) -> None:
#         """
#         Validates ethics-specific metadata fields.
        
#         Args:
#             metadata: Ethics metadata dictionary.
            
#         Raises:
#             ValueError: If compliance_requirements is present but not a list.
#         """
#         if 'compliance_requirements' in metadata:
#             requirements = metadata['compliance_requirements']
#             if not isinstance(requirements, list):
#                 raise ValueError(f"compliance_requirements must be a list, got {type(requirements).__name__}")
    
#     def _extract_and_validate_metadata(self, model_name: str, app_group_id: Optional[str], 
#                                       metadata: Dict[str, Any]) -> ValidatedEthicsData:
#         """
#         Extracts and validates metadata with safe defaults and HTML escaping.
        
#         Args:
#             model_name: Name of the model requiring ethics assessment.
#             app_group_id: ID of the application group (can be None).
#             metadata: Ethics metadata dictionary.
            
#         Returns:
#             Dataclass with validated and escaped data.
#         """
#         # Extract metadata with safe defaults
#         last_assessment = metadata.get('ethics_assessment_date', 'No previous assessment')
#         due_date = metadata.get('assessment_due_date', 'As soon as possible')
#         risk_level = metadata.get('risk_level', 'Not specified')
#         compliance_requirements = metadata.get('compliance_requirements', ['General ethical AI guidelines'])
#         model_category = metadata.get('model_category', 'Not specified')
        
#         # Ensure compliance_requirements is a list
#         if not isinstance(compliance_requirements, list):
#             compliance_requirements = ['General ethical AI guidelines']
        
#         # Handle missing app_group_id gracefully
#         app_group_display = app_group_id if app_group_id else NotificationConfig.APP_GROUP_NOT_SPECIFIED
        
#         # Create and return immutable dataclass instance
#         return ValidatedEthicsData(
#             model_name_escaped=html.escape(str(model_name)),
#             app_group_display_escaped=html.escape(str(app_group_display)),
#             last_assessment_escaped=html.escape(str(last_assessment)),
#             due_date_escaped=html.escape(str(due_date)),
#             risk_level_escaped=html.escape(str(risk_level)),
#             compliance_requirements=compliance_requirements,  # Will be escaped when rendered
#             model_category_escaped=html.escape(str(model_category))
#         )
    
#     def _create_alert_section(self, validated_data: ValidatedEthicsData) -> str:
#         """
#         Creates the alert section for ethics assessment.
        
#         Args:
#             validated_data: Dataclass with validated and escaped data.
            
#         Returns:
#             HTML string for the alert section.
#         """
#         return f"""
#             <div class="alert">
#                 <p class="alert-text">
#                     Ethics assessment is required for model "<strong>{validated_data.model_name_escaped}</strong>" 
#                     to ensure compliance with ethical AI guidelines and organizational policies.
#                 </p>
#             </div>
#         """
    
#     def _create_details_section(self, validated_data: ValidatedEthicsData) -> str:
#         """
#         Creates the details section for ethics assessment.
        
#         Args:
#             validated_data: Dataclass with validated and escaped data.
            
#         Returns:
#             HTML string for the details section.
#         """
#         # Format compliance requirements with escaping
#         requirements_html = ""
#         if validated_data.compliance_requirements:
#             requirements_html = "<ul>" + "".join(
#                 f"<li>{html.escape(str(req))}</li>" 
#                 for req in validated_data.compliance_requirements
#             ) + "</ul>"
#         else:
#             requirements_html = "General ethical AI guidelines"
        
#         return f"""
#             <h2 class="section-title">🛡️ Ethics Assessment Details</h2>
            
#             <table class="details-table">
#                 <tr>
#                     <th>🏷️ Model Name</th>
#                     <td><strong>{validated_data.model_name_escaped}</strong></td>
#                 </tr>
#                 <tr>
#                     <th>👥 Application Group</th>
#                     <td>{validated_data.app_group_display_escaped}</td>
#                 </tr>
#                 <tr>
#                     <th>📂 Model Category</th>
#                     <td>{validated_data.model_category_escaped}</td>
#                 </tr>
#                 <tr>
#                     <th>⚠️ Risk Level</th>
#                     <td><span class="highlight-value">{validated_data.risk_level_escaped}</span></td>
#                 </tr>
#                 <tr>
#                     <th>📅 Last Assessment</th>
#                     <td>{validated_data.last_assessment_escaped}</td>
#                 </tr>
#                 <tr>
#                     <th>⏰ Assessment Due</th>
#                     <td><strong>{validated_data.due_date_escaped}</strong></td>
#                 </tr>
#                 <tr>
#                     <th>📋 Compliance Requirements</th>
#                     <td>{requirements_html}</td>
#                 </tr>
#             </table>
#         """">
#                 <tr>
#                     <th>🏷️ Model Name</th>
#                     <td><strong>{validated_data['model_name_escaped']}</strong></td>
#                 </tr>
#                 <tr>
#                     <th>👥 Application Group</th>
#                     <td>{validated_data['app_group_display_escaped']}</td>
#                 </tr>
#                 <tr>
#                     <th>📂 Model Category</th>
#                     <td>{validated_data['model_category_escaped']}</td>
#                 </tr>
#                 <tr>
#                     <th>⚠️ Risk Level</th>
#                     <td><span class="highlight-value">{validated_data['risk_level_escaped']}</span></td>
#                 </tr>
#                 <tr>
#                     <th>📅 Last Assessment</th>
#                     <td>{validated_data['last_assessment_escaped']}</td>
#                 </tr>
#                 <tr>
#                     <th>⏰ Assessment Due</th>
#                     <td><strong>{validated_data['due_date_escaped']}</strong></td>
#                 </tr>
#                 <tr>
#                     <th>📋 Compliance Requirements</th>
#                     <td>{requirements_html}</td>
#                 </tr>
#             </table>
#         """
    
#     def _create_action_section(self, validated_data: ValidatedEthicsData) -> str:
#         """
#         Creates the action section for ethics assessment.
        
#         Args:
#             validated_data: Dataclass with validated and escaped data.
            
#         Returns:
#             HTML string for the action section.
#         """
#         return """
#             <div class="action-section">
#                 <div class="action-title">⚖️ Ethics Assessment Steps:</div>
#                 <ol class="action-list">
#                     <li><strong>Schedule assessment</strong> with the Ethics Review Board</li>
#                     <li><strong>Prepare documentation</strong> including:
#                         <ul>
#                             <li>Model purpose and use cases</li>
#                             <li>Training data sources and potential biases</li>
#                             <li>Target populations and impact analysis</li>
#                             <li>Fairness and transparency measures</li>
#                         </ul>
#                     </li>
#                     <li><strong>Conduct ethical review</strong> covering:
#                         <ul>
#                             <li>Bias detection and mitigation strategies</li>
#                             <li>Privacy and data protection compliance</li>
#                             <li>Fairness across different user groups</li>
#                             <li>Explainability and transparency requirements</li>
#                         </ul>
#                     </li>
#                     <li><strong>Document assessment results</strong> and any remediation actions</li>
#                     <li><strong>Update ethics assessment records</strong> in the system</li>
#                     <li><strong>Schedule next review</strong> based on risk level and compliance requirements</li>
#                 </ol>
#             </div>
#         """
    
#     def get_notification_type(self) -> str:
#         """Returns the notification type identifier."""
#         return "ethics_assessment"
    
#     def get_notification_icon(self) -> str:
#         """Returns the icon for ethics assessment notifications."""
#         return "⚖️"
    
#     def get_notification_color_scheme(self) -> Dict[str, str]:
#         """Returns the color scheme for ethics assessment notifications."""
#         return {
#             'primary': '#6f42c1',
#             'secondary': '#563d7c'
#         }