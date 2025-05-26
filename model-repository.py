# s3_file_repository_simple.py
"""
Simplified module for accessing model files from S3 storage.
Direct approach without protocol abstraction.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any
import re
import pickle
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from io import BytesIO

logger = logging.getLogger(__name__)

@dataclass(frozen=True) 
class S3Config:
    """Configuration for S3 connection."""
    bucket_name: str
    prefix: str = ""

class ModelFileRepository:
    """Repository for accessing model files from S3 storage."""
    
    # Constants
    DUMMY_MODEL_NAME = "Model-0"
    MODEL_FILE_PATTERN = r'(docato_.+)_(\d{8}_\d{6})\.pkl'
    AAP_ATTRIBUTE = 'aap'
    AAP_GROUP_ID_ATTRIBUTE = 'aap_group_id'
    
    def __init__(self, bucket_name: str, prefix: str = ""):
        """Initialize repository with S3 configuration.
        
        Args:
            bucket_name: S3 bucket name containing model files.
            prefix: Optional prefix for filtering objects in bucket.
            
        Raises:
            NoCredentialsError: If AWS credentials are not found.
        """
        self._config = S3Config(bucket_name, prefix)
        
        try:
            # Let boto3 auto-detect region from AWS config/environment
            self._s3_client = boto3.client('s3')
            logger.info(f"Initialized S3 repository for bucket: {bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
    
    def _list_s3_objects(self, prefix: str = "", max_objects: int = None) -> list[str]:
        """List all objects in S3 bucket with given prefix.
        
        Args:
            prefix: Prefix to filter objects.
            max_objects: Optional limit on number of objects to return.
                        If None, returns all objects (may require pagination).
            
        Returns:
            List of S3 object keys.
        """
        try:
            # Combine config prefix with method prefix
            full_prefix = f"{self._config.prefix}/{prefix}".strip("/")
            if full_prefix:
                full_prefix += "/"
            
            logger.debug(f"Listing S3 objects with prefix: {full_prefix}")
            
            object_keys = []
            
            # If we have a reasonable limit, use single call for efficiency
            if max_objects and max_objects <= 1000:
                response = self._s3_client.list_objects_v2(
                    Bucket=self._config.bucket_name,
                    Prefix=full_prefix,
                    MaxKeys=max_objects
                )
                
                if 'Contents' in response:
                    object_keys = [obj['Key'] for obj in response['Contents']]
                    
            else:
                # Use paginator for potentially large datasets or unlimited requests
                paginator = self._s3_client.get_paginator('list_objects_v2')
                page_iterator = paginator.paginate(
                    Bucket=self._config.bucket_name,
                    Prefix=full_prefix
                )
                
                objects_collected = 0
                for page in page_iterator:
                    if 'Contents' in page:
                        page_objects = [obj['Key'] for obj in page['Contents']]
                        object_keys.extend(page_objects)
                        objects_collected += len(page_objects)
                        
                        # Respect max_objects limit if specified
                        if max_objects and objects_collected >= max_objects:
                            object_keys = object_keys[:max_objects]
                            break
            
            logger.info(f"Found {len(object_keys)} objects in S3")
            return object_keys
            
        except ClientError as e:
            logger.error(f"Failed to list S3 objects: {e}")
            return []
    
    def _get_s3_object(self, key: str) -> bytes:
        """Get object content from S3.
        
        Args:
            key: S3 object key to retrieve.
            
        Returns:
            Object content as bytes.
            
        Raises:
            ClientError: If object cannot be retrieved from S3.
        """
        try:
            logger.debug(f"Retrieving S3 object: {key}")
            response = self._s3_client.get_object(
                Bucket=self._config.bucket_name,
                Key=key
            )
            content = response['Body'].read()
            logger.debug(f"Retrieved {len(content)} bytes from S3")
            return content
            
        except ClientError as e:
            logger.error(f"Failed to get S3 object {key}: {e}")
            raise
    
    def get_latest_model_paths(self, prefix: str = "", max_models: int = None) -> Optional[Dict[str, str]]:
        """Find the most recent version of each model.
        
        Args:
            prefix: Optional prefix to filter objects.
            max_models: Optional limit on number of objects to fetch from S3.
                       If you know you have < 1000 model files, set this for efficiency.
            
        Returns:
            Dictionary mapping model names to their most recent S3 keys,
            or None if error or no models found.
        """
        try:
            # Step 1: Get objects from S3 (with optional limit for efficiency)
            all_objects = self._list_s3_objects(prefix, max_models)
            
            # Step 2: Filter for pickle files
            pkl_files = [obj for obj in all_objects if obj.endswith('.pkl')]
            
            if not pkl_files:
                logger.warning(f"No pickle files found with prefix: {prefix}")
                return None
            
            logger.info(f"Processing {len(pkl_files)} pickle files")
            
            # Step 3: Group files by model name using regex
            model_groups = {}
            
            for file_key in pkl_files:
                filename = Path(file_key).name
                match = re.match(self.MODEL_FILE_PATTERN, filename)
                
                if match:
                    model_name, date_str = match.groups()
                    
                    # Skip dummy models
                    if model_name == self.DUMMY_MODEL_NAME:
                        continue
                    
                    if model_name not in model_groups:
                        model_groups[model_name] = []
                    model_groups[model_name].append((file_key, date_str))
            
            if not model_groups:
                logger.warning("No files matched the expected model pattern")
                return None
            
            # Step 4: Find latest version of each model
            latest_models = {}
            for model_name, versions in model_groups.items():
                # Sort by date (most recent last)
                sorted_versions = sorted(versions, key=lambda x: x[1])
                latest_models[model_name] = sorted_versions[-1][0]
            
            logger.info(f"Found latest versions for {len(latest_models)} models")
            return latest_models
            
        except Exception as e:
            logger.error(f"Failed to get latest model paths: {e}")
            return None
    
    def get_models_by_aap_group_id(self, model_paths: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Extract aap_group_id from each model file.
        
        Args:
            model_paths: Dictionary mapping model names to S3 keys.
            
        Returns:
            Dictionary mapping model names to aap_group_ids,
            or None if error or no valid group IDs found.
        """
        if not model_paths:
            logger.warning("No model paths provided")
            return None
        
        try:
            result = {}
            
            for model_name, s3_key in model_paths.items():
                try:
                    # Step 1: Get object from S3
                    object_content = self._get_s3_object(s3_key)
                    
                    # Step 2: Load pickle data
                    model_data = pickle.load(BytesIO(object_content))
                    
                    # Step 3: Extract AAP group ID
                    aap_group_id = self._extract_aap_group_id(model_data, s3_key)
                    
                    if aap_group_id:
                        result[model_name] = aap_group_id
                        logger.debug(f"Extracted aap_group_id '{aap_group_id}' from {s3_key}")
                    
                except Exception as e:
                    logger.error(f"Error processing {s3_key}: {e}")
                    # Continue with other files
            
            if result:
                logger.info(f"Successfully extracted aap_group_id for {len(result)} models")
                return result
            else:
                logger.warning("No valid aap_group_ids found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract aap_group_ids: {e}")
            return None
    
    def _extract_aap_group_id(self, model_data: Any, s3_key: str) -> Optional[str]:
        """Extract aap_group_id from model data.
        
        Args:
            model_data: Loaded pickle object.
            s3_key: S3 key for logging.
            
        Returns:
            aap_group_id if found, None otherwise.
        """
        try:
            if not hasattr(model_data, self.AAP_ATTRIBUTE):
                logger.debug(f"No '{self.AAP_ATTRIBUTE}' attribute in {s3_key}")
                return None
            
            aap_obj = getattr(model_data, self.AAP_ATTRIBUTE)
            aap_group_id = getattr(aap_obj, self.AAP_GROUP_ID_ATTRIBUTE, None)
            
            if not aap_group_id or aap_group_id == '':
                logger.warning(f"Empty/None aap_group_id in {s3_key}")
                return None
            
            return str(aap_group_id)
            
        except Exception as e:
            logger.error(f"Error extracting aap_group_id from {s3_key}: {e}")
            return None

# Simple factory function
def create_s3_repository(bucket_name: str, prefix: str = "") -> ModelFileRepository:
    """Create S3 repository.
    
    Args:
        bucket_name: S3 bucket name.
        prefix: Optional prefix for objects.
        
    Returns:
        ModelFileRepository instance.
    """
    return ModelFileRepository(bucket_name, prefix)