# model_review.py
"""
Module for business logic related to determining which models need review.

This module contains the core business logic for checking which models
require review based on their last review dates and associated metadata.
It coordinates between database and file repositories to gather complete
model information.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
import pandas as pd

# Import the finalized repository modules
from database_repository import ModelDatabaseRepository
from s3_file_repository import ModelFileRepository, create_s3_repository

logger = logging.getLogger(__name__)

class ModelReviewChecker:
    """Business logic for checking which models need review.
    
    This class coordinates between database and file repositories to
    determine which models need review and enriches the data with
    relevant metadata for notification purposes.
    
    Attributes:
        REVIEW_INTERVAL_DAYS: Number of days after which a model needs review.
    """
    
    # Business rule constants
    REVIEW_INTERVAL_DAYS = 180  # 6 months
    
    def __init__(self, 
                 database_repository: ModelDatabaseRepository,
                 file_repository: ModelFileRepository):
        """Initialize the checker with repository instances.
        
        Args:
            database_repository: Repository for database operations.
            file_repository: Repository for S3/file operations.
        """
        self._db_repository = database_repository
        self._file_repository = file_repository
        logger.info("Initialized ModelReviewChecker with separated repositories")
        
    def _is_review_required(self, review_date_str: str) -> bool:
        """Check if a model needs review based on its last review date.
        
        Args:
            review_date_str: String representation of the last review date.
            
        Returns:
            True if review is required, False otherwise.
            
        Note:
            If the date cannot be parsed, assumes review is needed for safety.
        """
        if not review_date_str or review_date_str.strip() == '':
            logger.warning("Empty review date provided, assuming review needed")
            return True
            
        try:
            review_date = pd.to_datetime(review_date_str)
            cutoff_date = datetime.now() - timedelta(days=self.REVIEW_INTERVAL_DAYS)
            
            is_overdue = review_date < cutoff_date
            logger.debug(f"Review date {review_date_str}: {'overdue' if is_overdue else 'current'}")
            return is_overdue
            
        except Exception as e:
            logger.warning(f"Could not parse review date '{review_date_str}': {e}")
            # If we can't parse the date, assume review is needed for safety
            return True
    
    def _calculate_days_overdue(self, review_date_str: str) -> Any:
        """Calculate how many days overdue a review is.
        
        Args:
            review_date_str: String representation of the review date.
            
        Returns:
            Number of days overdue as integer, or "Unknown" if cannot calculate.
        """
        try:
            review_date = pd.to_datetime(review_date_str)
            current_date = datetime.now()
            days_overdue = (current_date - review_date).days
            return max(0, days_overdue)  # Don't return negative days
        except Exception as e:
            logger.debug(f"Could not calculate days overdue for '{review_date_str}': {e}")
            return "Unknown"
            
    def check_models_due_for_review(self, file_prefix: str = None) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get all models that need review with their enriched metadata.
        
        This method coordinates between database and file repositories to:
        1. Get review dates from database
        2. Get latest model file paths from S3
        3. Extract AAP group IDs from model files
        4. Apply business rules to determine which models need review
        5. Return enriched metadata for notification purposes
        
        Args:
            file_prefix: Optional prefix for filtering S3 objects. If None, 
                        searches all objects in the bucket.
            
        Returns:
            Dictionary with model names as keys and enriched metadata as values,
            or None if an error occurs during the process.
            
        Example:
            >>> checker = ModelReviewChecker(db_repo, file_repo)
            >>> models = checker.check_models_due_for_review("models/production/")
            >>> if models:
            ...     print(f"Found {len(models)} models needing review")
        """
        try:
            logger.info("Starting model review check process")
            
            # Step 1: Get review dates from database
            logger.debug("Fetching model review dates from database")
            all_review_dates = self._db_repository.get_model_review_dates()
            
            if not all_review_dates:
                logger.warning("No review dates found in database")
                return None
            
            logger.info(f"Found review dates for {len(all_review_dates)} models in database")
            
            # Step 2: Get latest model file paths from S3
            logger.debug("Fetching latest model paths from file repository")
            # Handle None prefix by converting to empty string for the repository
            prefix_to_use = file_prefix if file_prefix is not None else ""
            model_paths = self._file_repository.get_latest_model_paths(prefix_to_use)
            
            if not model_paths:
                logger.warning("No model files found in storage")
                return None
            
            logger.info(f"Found {len(model_paths)} latest model files")
            
            # Step 3: Extract AAP group IDs from model files
            logger.debug("Extracting AAP group IDs from model files")
            app_group_ids = self._file_repository.get_models_by_aap_group_id(model_paths)
            
            if not app_group_ids:
                logger.warning("No valid AAP group IDs found in model files")
                # Continue processing - we can still send notifications without AAP group IDs
                app_group_ids = {}
            else:
                logger.info(f"Extracted AAP group IDs for {len(app_group_ids)} models")
            
            # Step 4: Apply business logic to determine which models need review
            logger.debug("Applying business rules to determine models needing review")
            result = {}
            
            for model_name, review_date_str in all_review_dates.items():
                # Apply business rule: is review required?
                if self._is_review_required(review_date_str):
                    
                    # Calculate days overdue
                    days_overdue = self._calculate_days_overdue(review_date_str)
                    
                    # Build enriched metadata for notification system
                    metadata = {
                        'review_date': review_date_str,
                        'app_group_id': app_group_ids.get(model_name),
                        'model_path': model_paths.get(model_name),
                        'days_overdue': days_overdue,
                        'review_interval_days': self.REVIEW_INTERVAL_DAYS
                    }
                    
                    # Only include models that have corresponding files or AAP group IDs
                    # This ensures we can send meaningful notifications
                    if metadata['model_path'] or metadata['app_group_id']:
                        result[model_name] = metadata
                        logger.debug(f"Model {model_name} needs review (overdue by {days_overdue} days)")
                    else:
                        logger.warning(f"Model {model_name} needs review but no file/AAP group found - skipping")
            
            if result:
                logger.info(f"Found {len(result)} models requiring review")
                return result
            else:
                logger.info("No models require review at this time")
                return None
            
        except Exception as e:
            logger.error(f"Error during model review check: {e}")
            return None

# Factory function for easy instantiation
def create_model_review_checker(bucket_name: str, 
                               bucket_prefix: str = "",
                               database_name: str = "Mydag",
                               table_name: str = "modelops_docato_output") -> ModelReviewChecker:
    """Create ModelReviewChecker with default repository configurations.
    
    Args:
        bucket_name: S3 bucket name containing model files.
        bucket_prefix: Optional prefix for S3 objects.
        database_name: Database name for model metadata.
        table_name: Table name containing model review data.
        
    Returns:
        Configured ModelReviewChecker instance.
    """
    # Create repositories
    db_repo = ModelDatabaseRepository(database_name, table_name)
    file_repo = create_s3_repository(bucket_name, bucket_prefix)
    
    # Create and return checker
    return ModelReviewChecker(db_repo, file_repo)