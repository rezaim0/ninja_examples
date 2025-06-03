# database_repository.py
"""
Module for accessing model metadata from database sources.

This module provides a repository class for querying model metadata
from Teradata database systems, specifically designed for model review
date tracking and related operations. It integrates with the config.py
system for environment-aware database configuration.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import logging
import pandas as pd
import tdwh  # Your existing database connection module
from config import get_db_config, Environment

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class DatabaseConfig:
    """Immutable configuration for database connection.
    
    Attributes:
        environment: Current environment (LOCAL, DEV, STAGING, PROD).
        database: Database name to connect to.
        schema: Database schema name.
        table_names: Dictionary of table names used in the application.
    """
    environment: Environment
    database: str
    schema: Optional[str]
    table_names: Dict[str, str]

class ModelDatabaseRepository:
    """Responsible for accessing model metadata from database sources only.
    
    This repository handles all database operations related to model metadata,
    including retrieving model review dates and related information from
    the configured Teradata database. It uses the config.py system for
    environment-aware database configuration.
    
    Attributes:
        FIELD_NAME_MODEL_REVIEW: Constant for model review date field name.
        COLUMN_END_DTTM: Database column name for end datetime.
        COLUMN_FIELD_NAME: Database column name for field name.
        COLUMN_MODEL_NAME: Database column name for model name.
        COLUMN_FIELD_VALUE: Database column name for field value.
    """
    
    # Database field constants
    FIELD_NAME_MODEL_REVIEW = "model_review_date"
    COLUMN_END_DTTM = "end_dttm"
    COLUMN_FIELD_NAME = "field_name"
    COLUMN_MODEL_NAME = "model_name"
    COLUMN_FIELD_VALUE = "field_value"
    
    # Default base table identifier
    DEFAULT_TABLE_NAME = "output"  # Config key for the main model output table
    
    def __init__(self, table_name: str = "modelops_docato_output"):
        """Initialize repository with database connection details from config system.
        
        Args:
            table_name: Table name to use. Will look for this in config's table_names values.
            
        Raises:
            ValueError: If configuration is invalid.
        """
        # Load config from config.py system
        self._db_config = self._load_database_config()
        
        # Use the table name from config or fallback to provided name
        self._table_name = self._get_table_name_from_config(table_name)
        
        logger.info(f"Initialized ModelDatabaseRepository for environment: {self._db_config.environment.value}")
        logger.info(f"Using table: {self._table_name}")
        logger.info(f"Database: {self._db_config.database}, Schema: {self._db_config.schema}")
        logger.info(f"Full table name: {self._build_full_table_name()}")
    
    def _get_table_name_from_config(self, requested_table: str) -> str:
        """Get the actual table name from config.
        
        This method resolves table names using the configuration system. It allows
        using either config keys (like "output") or direct table names.
        
        Args:
            requested_table: The table identifier to resolve. Can be either:
                           - A config key like "output", "fields", "version"
                           - A direct table name like "modelops_docato_output"
            
        Returns:
            The actual table name to use in SQL queries. Examples:
            - Input: "output" → Output: "modelops_docato_output" (PROD)
            - Input: "output" → Output: "kfp123_modelops_docato_output" (DEV)
            - Input: "modelops_docato_output" → Output: "modelops_docato_output"
            
        Example:
            >>> # Using config key (recommended)
            >>> table_name = self._get_table_name_from_config("output")
            >>> print(table_name)  # "modelops_docato_output" or "kfp123_modelops_docato_output"
            
            >>> # Using direct table name
            >>> table_name = self._get_table_name_from_config("modelops_docato_output")
            >>> print(table_name)  # "modelops_docato_output"
        """
        # Check if it's a key in table_names (like "output" -> "modelops_docato_output")
        if requested_table in self._db_config.table_names:
            return self._db_config.table_names[requested_table]
        
        # If not found in config, use as provided
        logger.warning(f"Table '{requested_table}' not found in config. Using as-is.")
        return requested_table
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from config.py system.
        
        Returns:
            DatabaseConfig: Loaded configuration.
            
        Raises:
            ValueError: If configuration cannot be loaded.
        """
        try:
            # Get database configuration from config.py
            db_config = get_db_config()
            
            return DatabaseConfig(
                environment=db_config.environment,
                database=db_config.database,
                schema=db_config.schema,
                table_names=db_config.table_names
            )
            
        except Exception as e:
            logger.error(f"Failed to load database configuration: {e}")
            raise ValueError(f"Database configuration error: {e}")
    
    def _build_full_table_name(self) -> str:
        """Build the fully qualified table name for SQL queries.
        
        Constructs the complete table identifier by combining database name,
        schema name, and table name according to the current environment configuration.
        
        The structure follows the pattern: [database].[schema].[table_name]
        
        Returns:
            Fully qualified table name ready for use in SQL queries.
            
        Environment Examples:
            DEV Environment (config.yaml):
                database: edw
                schema: ptap
                table_names:
                  output: "kfp123_modelops_docato_output"  # User-prefixed
                Result: "edw.ptap.kfp123_modelops_docato_output"
                
            PROD Environment (config.yaml):
                database: edw  
                schema: pmodel
                table_names:
                  output: "modelops_docato_output"
                Result: "edw.pmodel.modelops_docato_output"
                
            LOCAL Environment (config.yaml):
                database: local.db
                schema: null
                table_names:
                  output: "modelops_docato_output"
                Result: "local.db.modelops_docato_output"
        
        SQL Query Usage:
            >>> full_name = repo._build_full_table_name()
            >>> query = f"SELECT * FROM {full_name} WHERE field_name = 'model_review_date'"
            >>> # DEV: "SELECT * FROM edw.ptap.kfp123_modelops_docato_output WHERE..."
            >>> # PROD: "SELECT * FROM edw.pmodel.modelops_docato_output WHERE..."
        """
        parts = []
        
        # Always include database if available
        if self._db_config.database:
            parts.append(self._db_config.database)
        
        # Always include schema if available  
        if self._db_config.schema:
            parts.append(self._db_config.schema)
        
        # Always include table name
        parts.append(self._table_name)
        
        full_name = ".".join(parts)
        logger.debug(f"Built full table name: {full_name}")
        return full_name
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from config.py system.
        
        Returns:
            DatabaseConfig: Loaded configuration.
            
        Raises:
            ValueError: If configuration cannot be loaded.
        """
        try:
            # Get database configuration from config.py
            db_config = get_db_config()
            
            return DatabaseConfig(
                environment=db_config.environment,
                database=db_config.database,
                schema=db_config.schema,
                table_names=db_config.table_names
            )
            
        except Exception as e:
            logger.error(f"Failed to load database configuration: {e}")
            raise ValueError(f"Database configuration error: {e}")
    
    def _build_full_table_name(self) -> str:
        """Build the full table name including database and schema if applicable.
        
        Returns:
            Fully qualified table name.
        """
        parts = []
        
        if self._db_config.database:
            parts.append(self._db_config.database)
        
        if self._db_config.schema:
            parts.append(self._db_config.schema)
        
        parts.append(self._table_name)
        
        return ".".join(parts)
    
    def _build_review_dates_query(self, field_name: str = None) -> str:
        """Build SQL query for retrieving model review dates.
        
        Constructs a SELECT query to get model metadata from the configured table.
        The query specifically looks for records with a given field name (typically
        'model_review_date') and active records (where end_dttm IS NULL).
        
        Args:
            field_name: Field name to filter by in the WHERE clause. 
                       Defaults to FIELD_NAME_MODEL_REVIEW ("model_review_date").
            
        Returns:
            Complete SQL query string ready for execution.
            
        Query Structure:
            The resulting query will look like:
            ```sql
            SELECT *
            FROM [database].[schema].[table_name]  
            WHERE field_name = 'model_review_date';
            ```
            
        Example Queries by Environment:
            DEV:
            ```sql
            SELECT *
            FROM edw.ptap.kfp123_modelops_docato_output
            WHERE field_name = 'model_review_date';
            ```
            
            PROD:
            ```sql  
            SELECT *
            FROM edw.pmodel.modelops_docato_output
            WHERE field_name = 'model_review_date';
            ```
            
        Expected Table Structure:
            The target table should have columns like:
            - model_name (str): Name of the ML model
            - field_name (str): Type of metadata field
            - field_value (str): Value of the metadata field  
            - end_dttm (datetime): End timestamp (NULL for active records)
            - Additional columns for audit/tracking
            
        Sample Data:
            | model_name    | field_name        | field_value  | end_dttm |
            |---------------|-------------------|--------------|----------|
            | my_model_v1   | model_review_date | 2024-01-15   | NULL     |
            | my_model_v2   | model_review_date | 2024-06-01   | NULL     |
            | old_model     | model_review_date | 2023-12-01   | 2024-01-01 |
        """
        field_to_query = field_name or self.FIELD_NAME_MODEL_REVIEW
        full_table_name = self._build_full_table_name()
        
        query = f"""
            SELECT *
            FROM {full_table_name}
            WHERE {self.COLUMN_FIELD_NAME} = '{field_to_query}';
        """
        
        return query
    
    def _extract_models_data(self, field_name: str = None) -> Optional[pd.DataFrame]:
        """Extract model data from the database.
        
        Args:
            field_name: Optional field name to filter by. If None, defaults
                       to FIELD_NAME_MODEL_REVIEW.
            
        Returns:
            DataFrame containing model data, or None if an error occurs.
            
        Raises:
            None: All exceptions are caught and logged, None is returned on error.
        """
        try:
            query = self._build_review_dates_query(field_name)
            logger.debug(f"Executing query: {query}")
            
            # Use tdwh to connect to Teradata
            with tdwh.teradata_connect() as con:
                output_table = tdwh.run_query(session=con, query=query)
                
            if output_table is not None and not output_table.empty:
                logger.info(f"Retrieved {len(output_table)} records from database")
                return output_table
            else:
                logger.warning("Query returned empty result set")
                return None
                
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return None
    
    def get_model_review_dates(self) -> Optional[Dict[str, str]]:
        """Get all model review dates from the database.
        
        Retrieves model review dates for models that have active records
        (where end_dttm is NULL) and match the model review date field.
        
        This method filters the data to only include:
        - Active records (end_dttm IS NULL)
        - Records with field_name = 'model_review_date'
        - Records with valid model_name and field_value
        
        Returns:
            Dictionary mapping model_name to review_date string,
            or None if an error occurs or no data is found.
            
        Example:
            >>> repo = ModelDatabaseRepository()
            >>> dates = repo.get_model_review_dates()
            >>> if dates:
            ...     print(f"Found review dates for {len(dates)} models")
            ...     for model, date in dates.items():
            ...         print(f"{model}: {date}")
            
        Data Processing:
            Input data from database:
            | model_name  | field_name        | field_value | end_dttm |
            |-------------|-------------------|-------------|----------|
            | model_a     | model_review_date | 2024-01-15  | NULL     |
            | model_b     | model_review_date | 2024-06-01  | NULL     |
            | old_model   | model_review_date | 2023-12-01  | 2024-01-01 | ← Filtered out
            
            Returned dictionary:
            {
                'model_a': '2024-01-15',
                'model_b': '2024-06-01'
            }
        """
        data = self._extract_models_data()
        if data is None:
            logger.warning("No data returned from database query")
            return None
        
        try:
            result = {}
            processed_count = 0
            
            for _, row in data.iterrows():
                processed_count += 1
                
                # Filter for active records with model review dates
                if (pd.isna(row[self.COLUMN_END_DTTM]) and 
                    row[self.COLUMN_FIELD_NAME] == self.FIELD_NAME_MODEL_REVIEW):
                    
                    model_name = row[self.COLUMN_MODEL_NAME]
                    review_date = row[self.COLUMN_FIELD_VALUE]
                    
                    if model_name and review_date:
                        result[model_name] = review_date
            
            logger.info(f"Processed {processed_count} records, "
                       f"retrieved review dates for {len(result)} models")
            
            return result if result else None
            
        except Exception as e:
            logger.error(f"Error processing database results: {e}")
            return None
    
    def get_models_by_field(self, field_name: str) -> Optional[Dict[str, str]]:
        """Get all models and their values for a specific field.
        
        This is a more generic method that can retrieve any field values,
        not just review dates.
        
        Args:
            field_name: The field name to query for.
            
        Returns:
            Dictionary mapping model_name to field_value,
            or None if an error occurs or no data is found.
            
        Example:
            >>> repo = ModelDatabaseRepository()
            >>> performance_data = repo.get_models_by_field("performance_score")
        """
        data = self._extract_models_data(field_name)
        if data is None:
            logger.warning(f"No data returned for field: {field_name}")
            return None
        
        try:
            result = {}
            
            for _, row in data.iterrows():
                if (pd.isna(row[self.COLUMN_END_DTTM]) and 
                    row[self.COLUMN_FIELD_NAME] == field_name):
                    
                    model_name = row[self.COLUMN_MODEL_NAME]
                    field_value = row[self.COLUMN_FIELD_VALUE]
                    
                    if model_name and field_value is not None:
                        result[model_name] = field_value
            
            logger.info(f"Retrieved {field_name} for {len(result)} models")
            return result if result else None
            
        except Exception as e:
            logger.error(f"Error processing results for field {field_name}: {e}")
            return None
    
    @property
    def database_config(self) -> DatabaseConfig:
        """Get the current database configuration.
        
        Returns:
            DatabaseConfig: The immutable database configuration object.
        """
        return self._db_config
    
    @property
    def table_name(self) -> str:
        """Get the current table name being used.
        
        Returns:
            Actual table name from config.
        """
        return self._table_name
    
    @property
    def full_table_name(self) -> str:
        """Get the full qualified table name.
        
        Returns:
            Fully qualified table name including database and schema.
        """
        return self._build_full_table_name()
    
    def health_check(self) -> bool:
        """Check if the database connection and table are accessible.
        
        Performs a simple query to verify connectivity and table existence.
        
        Returns:
            True if database is accessible, False otherwise.
        """
        try:
            full_table_name = self._build_full_table_name()
            test_query = f"""
                SELECT COUNT(*) as record_count 
                FROM {full_table_name} 
                LIMIT 1;
            """
            
            with tdwh.teradata_connect() as con:
                result = tdwh.run_query(session=con, query=test_query)
                
            if result is not None:
                logger.info(f"Database health check passed for table: {full_table_name}")
                return True
            else:
                logger.warning("Database health check failed - no result returned")
                return False
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_environment_info(self) -> Dict[str, str]:
        """Get information about the current database environment.
        
        Returns:
            Dictionary with environment configuration details.
        """
        return {
            'environment': self._db_config.environment.value,
            'database': self._db_config.database,
            'schema': self._db_config.schema or 'None',
            'table_name': self._table_name,
            'full_table_name': self._build_full_table_name(),
            'available_tables': list(self._db_config.table_names.values()),
            'table_config': dict(self._db_config.table_names)
        }

# Factory function for creating repository instances
def create_database_repository(table_name: str = "output") -> ModelDatabaseRepository:
    """Create database repository using current environment configuration.
    
    This factory function creates a repository that automatically uses the
    current environment configuration from config.py (DEV, PROD, etc.).
    
    Args:
        table_name: Table identifier to use. Can be either:
                   - Config key like "output" (recommended)
                   - Direct table name like "modelops_docato_output"
        
    Returns:
        ModelDatabaseRepository configured for current environment.
        
    Example:
        >>> # Recommended: use config key
        >>> repo = create_database_repository("output")
        >>> 
        >>> # Alternative: use direct table name  
        >>> repo = create_database_repository("modelops_docato_output")
    """
    return ModelDatabaseRepository(table_name)