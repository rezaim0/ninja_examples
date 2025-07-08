# notification_delivery.py
"""
Module for notification delivery mechanisms.

This module generates JSON files containing notification content and metadata
that will be processed by Data Engineering teams for actual email delivery.
Each JSON file contains all necessary information including AAP group ID,
email subject, HTML content, and metadata for a single notification.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class NotificationDelivery:
    """
    JSON file delivery implementation.
    
    Generates individual JSON files containing notification data that Data Engineering
    teams can process to send actual emails. Each file contains:
    - aap_group_id: For looking up email addresses
    - email_subject: Email subject line  
    - email_content: Full HTML email content
    - model_name: Name of the model requiring attention
    - notification_type: Type of notification (model_review, performance, etc.)
    - generated_timestamp: When notification was created
    - Additional metadata
    """
    
    def __init__(self, output_directory: str = "./emails_dir/sent_emails"):
        """
        Initialize JSON file delivery service.
        
        Args:
            output_directory: Directory where JSON notification files will be created.
                             Defaults to "./emails_dir/sent_emails".
        """
        self.output_directory = Path(output_directory)
        
        # Create output directory if it doesn't exist
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized NotificationDelivery with output directory: {self.output_directory}")
    
    def send(self, aap_group_id: str, subject: str, content: str, 
             model_name: str = None, notification_type: str = "model_review", 
             metadata: Dict[str, Any] = None) -> bool:
        """
        Generate JSON notification file for Data Engineering processing.
        
        Creates an individual JSON file containing all notification data needed
        for email delivery. The file is named using the AAP group ID for easy
        identification and processing.
        
        Args:
            aap_group_id: Application group ID for email address lookup.
            subject: Email subject line.
            content: Email content (HTML or plain text).
            model_name: Name of the model (extracted from metadata if not provided).
            notification_type: Type of notification (default: "model_review").
            metadata: Additional metadata about the model/notification.
            
        Returns:
            True if JSON file was generated successfully, False otherwise.
            
        Generated File Structure:
            {
                "aap_group_id": "group_123",
                "email_subject": "Model Review Required - my_model", 
                "email_content": "<html><body>Dear Team...</body></html>",
                "model_name": "my_model",
                "notification_type": "model_review",
                "generated_timestamp": "2024-12-20T10:30:00.123456",
                "metadata": {
                    "review_date": "2024-06-01",
                    "days_overdue": 185,
                    "model_path": "s3://bucket/model.pkl"
                }
            }
        """
        try:
            # Validate required parameters
            if not aap_group_id or not aap_group_id.strip():
                logger.error("Cannot generate notification: aap_group_id is empty")
                return False
                
            if not subject or not subject.strip():
                logger.warning("Email subject is empty, using default")
                subject = "Notification from MACATO System"
            
            if not content or not content.strip():
                logger.error("Cannot generate notification: content is empty")
                return False
            
            # Extract model name from metadata if not provided
            if not model_name and metadata:
                model_name = metadata.get('model_name', 'Unknown')
            
            # Create comprehensive notification data
            notification_data = {
                "aap_group_id": aap_group_id.strip(),
                "email_subject": subject.strip(),
                "email_content": content.strip(),
                "model_name": model_name or "Unknown",
                "notification_type": notification_type,
                "generated_timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # Generate filename using AAP group ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_group_id = self._sanitize_filename(aap_group_id)
            filename = f"email_{safe_group_id}_{timestamp}.json"
            file_path = self.output_directory / filename
            
            # Write JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(notification_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Generated notification JSON file: {filename}")
            logger.debug(f"File location: {file_path}")
            
            return True
                
        except Exception as e:
            logger.error(f"Failed to generate notification JSON for aap_group_id {aap_group_id}: {e}")
            return False
    
    def _sanitize_filename(self, aap_group_id: str) -> str:
        """
        Sanitize AAP group ID for use in filename.
        
        Replaces unsafe characters with underscores to ensure valid filenames
        across different operating systems.
        
        Args:
            aap_group_id: Original AAP group ID.
            
        Returns:
            Sanitized string safe for use in filenames.
        """
        # Replace unsafe characters with underscores
        import re
        safe_name = re.sub(r'[^\w\-_]', '_', aap_group_id)
        
        # Remove multiple consecutive underscores
        safe_name = re.sub(r'_+', '_', safe_name)
        
        # Remove leading/trailing underscores
        safe_name = safe_name.strip('_')
        
        return safe_name or "unknown_group"
    
    def get_output_directory(self) -> Path:
        """Get the output directory path."""
        return self.output_directory
    
    def get_generated_files(self) -> list[str]:
        """
        Get list of generated JSON notification files.
        
        Returns:
            List of JSON file paths that have been generated, sorted by creation time.
        """
        try:
            files = []
            for file_path in self.output_directory.iterdir():
                if (file_path.is_file() and 
                    file_path.name.startswith('email_') and 
                    file_path.name.endswith('.json')):
                    files.append(str(file_path))
            
            # Sort by modification time (most recent first)
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            return files
            
        except Exception as e:
            logger.error(f"Failed to list generated files: {e}")
            return []
    
    def get_file_count(self) -> int:
        """
        Get the number of JSON notification files generated.
        
        Returns:
            Count of JSON notification files in the output directory.
        """
        return len(self.get_generated_files())
    
    def read_notification_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read and parse a notification JSON file.
        
        Args:
            filename: Name of the JSON file to read.
            
        Returns:
            Parsed notification data as dictionary, or None if error.
        """
        try:
            file_path = self.output_directory / filename
            
            if not file_path.exists():
                logger.error(f"Notification file not found: {filename}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"Successfully read notification file: {filename}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to read notification file {filename}: {e}")
            return None
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """
        Clean up old notification files.
        
        Removes JSON notification files older than the specified number of days
        to prevent the output directory from growing indefinitely.
        
        Args:
            days_old: Remove files older than this many days.
            
        Returns:
            Number of files removed.
        """
        try:
            import time
            
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            files_removed = 0
            
            for file_path in self.output_directory.iterdir():
                if (file_path.is_file() and 
                    file_path.name.startswith('email_') and 
                    file_path.name.endswith('.json')):
                    
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        files_removed += 1
                        logger.debug(f"Removed old notification file: {file_path.name}")
            
            if files_removed > 0:
                logger.info(f"Cleaned up {files_removed} old notification files")
            
            return files_removed
            
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")
            return 0

# Factory function for easy creation
def create_json_delivery(output_directory: str = "./emails_dir/sent_emails") -> NotificationDelivery:
    """
    Create notification delivery service with JSON output.
    
    Args:
        output_directory: Directory where JSON files will be created.
        
    Returns:
        NotificationDelivery instance configured for JSON output.
        
    Example:
        >>> delivery = create_json_delivery("./my_emails/outbox")
        >>> success = delivery.send(
        ...     aap_group_id="group_123",
        ...     subject="Model Review Required",
        ...     content="<html><body>Email content</body></html>",
        ...     model_name="my_model"
        ... )
    """
    return NotificationDelivery(output_directory)