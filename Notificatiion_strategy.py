# email_notification_system.py
"""
Simplified email notification system for model reviews.

This module provides a clean, simple architecture for generating
email notifications as JSON files when models need review.
"""

import json
import logging
import re
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from io import BytesIO

import pandas as pd
import boto3
from botocore.exceptions import ClientError
import tdwh
from config import get_db_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class EmailData:
    """Data structure for email JSON output."""
    group_id: str
    subject: str
    env: str
    body: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ModelReviewData:
    """Data for a model that needs review."""
    model_name: str
    group_id: Optional[str]
    review_date: str
    days_overdue: int
    model_path: Optional[str]
    
    @property
    def urgency_level(self) -> str:
        """Determine urgency based on days overdue."""
        if self.days_overdue > 60:
            return "CRITICAL"
        elif self.days_overdue > 30:
            return "HIGH"
        elif self.days_overdue > 7:
            return "MEDIUM"
        return "LOW"


# ==============================================================================
# Database Operations
# ==============================================================================

def get_model_review_dates(table_name: str = "output") -> Dict[str, str]:
    """
    Get model review dates from database.
    
    Args:
        table_name: Table name or config key
        
    Returns:
        Dictionary mapping model names to review dates
    """
    db_config = get_db_config()
    
    # Resolve table name
    actual_table = db_config.table_names.get(table_name, table_name)
    
    # Validate table name for SQL injection prevention
    if not actual_table.replace("_", "").replace(".", "").isalnum():
        raise ValueError(f"Invalid table name: {actual_table}")
    
    full_table = f"{db_config.schema}.{actual_table}" if db_config.schema else actual_table
    
    query = f"""
        SELECT model_name, field_value
        FROM {full_table}
        WHERE field_name = %(field_name)s
        AND end_dttm IS NULL
    """
    
    try:
        with tdwh.teradata_connect() as conn:
            df = tdwh.run_query(
                session=conn,
                query=query,
                params={"field_name": "model_review_date"}
            )
        
        if df is None or df.empty:
            logger.warning("No review dates found in database")
            return {}
        
        result = dict(zip(df['model_name'], df['field_value']))
        logger.info(f"Retrieved {len(result)} review dates from database")
        return result
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        return {}


# ==============================================================================
# S3 Operations
# ==============================================================================

class S3ModelReader:
    """Simple S3 reader for model files."""
    
    def __init__(self, bucket_name: str):
        """Initialize S3 client."""
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        
    def get_latest_models(self, prefix: str = "") -> Dict[str, str]:
        """
        Get the latest version of each model from S3.
        
        Returns:
            Dictionary mapping model names to S3 keys
        """
        try:
            # List all pickle files
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return {}
            
            # Group files by model name and find latest
            model_files = {}
            pattern = r'(docato_.+)_(\d{8}_\d{6})\.pkl'
            
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.pkl'):
                    filename = Path(key).name
                    match = re.match(pattern, filename)
                    if match:
                        model_name, timestamp = match.groups()
                        if model_name not in model_files or timestamp > model_files[model_name][1]:
                            model_files[model_name] = (key, timestamp)
            
            # Return just the S3 keys
            return {name: data[0] for name, data in model_files.items()}
            
        except ClientError as e:
            logger.error(f"S3 error: {e}")
            return {}
    
    def get_group_id(self, s3_key: str) -> Optional[str]:
        """
        Extract group_id from a model pickle file.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Group ID if found, None otherwise
        """
        try:
            # Download and unpickle
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read()
            model_data = pickle.load(BytesIO(content))
            
            # Extract group_id (try different attribute names)
            if hasattr(model_data, 'aap'):
                return getattr(model_data.aap, 'aap_group_id', None)
            elif hasattr(model_data, 'group_id'):
                return model_data.group_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting group_id from {s3_key}: {e}")
            return None


# ==============================================================================
# Email Template Generation
# ==============================================================================

def create_review_email_html(data: ModelReviewData) -> str:
    """
    Create HTML email body for model review notification.
    
    Args:
        data: Model review data
        
    Returns:
        HTML email content
    """
    urgency_color = {
        "CRITICAL": "#dc3545",
        "HIGH": "#fd7e14",
        "MEDIUM": "#ffc107",
        "LOW": "#28a745"
    }.get(data.urgency_level, "#6c757d")
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            text-align: center;
        }}
        .content {{
            background: white;
            padding: 30px;
            border: 1px solid #e0e0e0;
            border-radius: 0 0 8px 8px;
        }}
        .urgency {{
            display: inline-block;
            background: {urgency_color};
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin: 10px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: bold;
        }}
        .actions {{
            background: #e7f3ff;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Model Review Required</h1>
        <span class="urgency">{data.urgency_level} PRIORITY</span>
    </div>
    
    <div class="content">
        <p><strong>Model "{data.model_name}" requires immediate review.</strong></p>
        
        <table>
            <tr>
                <th>Model Name</th>
                <td>{data.model_name}</td>
            </tr>
            <tr>
                <th>Group ID</th>
                <td>{data.group_id or 'Not specified'}</td>
            </tr>
            <tr>
                <th>Last Review</th>
                <td>{data.review_date}</td>
            </tr>
            <tr>
                <th>Days Overdue</th>
                <td style="color: {urgency_color}; font-weight: bold;">{data.days_overdue}</td>
            </tr>
            {f'<tr><th>Model Path</th><td><code>{data.model_path}</code></td></tr>' if data.model_path else ''}
        </table>
        
        <div class="actions">
            <h3>Required Actions:</h3>
            <ol>
                <li>Access the model through MACATO system</li>
                <li>Perform comprehensive review</li>
                <li>Update the model_review_date field</li>
                <li>Document any findings</li>
            </ol>
        </div>
        
        <div class="footer">
            <p>MACATO System - Automated Notification</p>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""


# ==============================================================================
# Main Notification Manager
# ==============================================================================

class EmailNotificationManager:
    """
    Simple manager for generating email notifications.
    
    This class coordinates the entire process of checking models
    and generating JSON files for email notifications.
    """
    
    REVIEW_INTERVAL_DAYS = 180  # 6 months
    
    def __init__(self, 
                 bucket_name: str,
                 output_dir: str = "./emails_dir",
                 environment: str = "production"):
        """
        Initialize the notification manager.
        
        Args:
            bucket_name: S3 bucket containing model files
            output_dir: Directory for JSON output files
            environment: Environment name (production, staging, etc.)
        """
        self.s3_reader = S3ModelReader(bucket_name)
        self.output_dir = Path(output_dir)
        self.environment = environment
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def check_models_needing_review(self) -> List[ModelReviewData]:
        """
        Check which models need review.
        
        Returns:
            List of ModelReviewData for models needing review
        """
        models_needing_review = []
        
        # Get review dates from database
        review_dates = get_model_review_dates()
        if not review_dates:
            logger.warning("No review dates found")
            return models_needing_review
        
        # Get latest models from S3
        model_paths = self.s3_reader.get_latest_models()
        
        # Check each model
        cutoff_date = datetime.now() - timedelta(days=self.REVIEW_INTERVAL_DAYS)
        
        for model_name, review_date_str in review_dates.items():
            try:
                review_date = pd.to_datetime(review_date_str)
                
                if review_date < cutoff_date:
                    # Model needs review
                    days_overdue = (datetime.now() - review_date).days
                    
                    # Get group_id from S3 if available
                    group_id = None
                    model_path = model_paths.get(model_name)
                    if model_path:
                        group_id = self.s3_reader.get_group_id(model_path)
                    
                    models_needing_review.append(
                        ModelReviewData(
                            model_name=model_name,
                            group_id=group_id,
                            review_date=review_date_str,
                            days_overdue=days_overdue,
                            model_path=model_path
                        )
                    )
                    
            except Exception as e:
                logger.error(f"Error processing {model_name}: {e}")
                continue
        
        logger.info(f"Found {len(models_needing_review)} models needing review")
        return models_needing_review
    
    def generate_email_json(self, model_data: ModelReviewData) -> Optional[str]:
        """
        Generate JSON file for a single email notification.
        
        Args:
            model_data: Model review data
            
        Returns:
            Path to generated JSON file, or None if failed
        """
        if not model_data.group_id:
            logger.warning(f"No group_id for {model_data.model_name}, skipping")
            return None
        
        try:
            # Create email data
            email = EmailData(
                group_id=model_data.group_id,
                subject=f"Model Review Required - {model_data.model_name} [{model_data.urgency_level}]",
                env=self.environment,
                body=create_review_email_html(model_data)
            )
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"email_{model_data.model_name}_{timestamp}.json"
            filepath = self.output_dir / filename
            
            # Write JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(email.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Generated email JSON: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate JSON for {model_data.model_name}: {e}")
            return None
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete notification process.
        
        Returns:
            Summary of the process
        """
        logger.info("Starting email notification process")
        
        # Check models
        models_needing_review = self.check_models_needing_review()
        
        # Generate JSON files
        generated_files = []
        failed_models = []
        
        for model_data in models_needing_review:
            filepath = self.generate_email_json(model_data)
            if filepath:
                generated_files.append(filepath)
            else:
                failed_models.append(model_data.model_name)
        
        # Summary
        summary = {
            'models_checked': len(models_needing_review),
            'emails_generated': len(generated_files),
            'failed': len(failed_models),
            'output_directory': str(self.output_dir),
            'generated_files': generated_files,
            'failed_models': failed_models
        }
        
        logger.info(f"Process complete: {summary['emails_generated']} emails generated")
        return summary


# ==============================================================================
# Usage Example
# ==============================================================================

def main():
    """Example usage of the notification system."""
    
    # Configure the system
    manager = EmailNotificationManager(
        bucket_name="my-model-bucket",
        output_dir="./emails_output",
        environment="production"
    )
    
    # Run the process
    results = manager.run()
    
    # Print summary
    print(f"\nNotification Process Summary:")
    print(f"  Models needing review: {results['models_checked']}")
    print(f"  Emails generated: {results['emails_generated']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Output directory: {results['output_directory']}")
    
    if results['generated_files']:
        print(f"\nGenerated files:")
        for filepath in results['generated_files']:
            print(f"  - {Path(filepath).name}")


if __name__ == "__main__":
    main()