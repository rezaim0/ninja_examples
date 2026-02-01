"""
Email Data Generation with Clean Architecture and Logging

Improvements:
- Added loguru logging throughout
- Added proper error handling with Result type pattern
- Added validation
- Maintained separation of concerns
- Type hints enhanced
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Tuple, Optional

import pandas as pd
from loguru import logger


# ============================================================================
# RESULT TYPE (for better error handling)
# ============================================================================

class Status(Enum):
    """Status of email file generation."""
    SUCCESS = "successful"
    FAILURE = "unsuccessful"


@dataclass(frozen=True)
class Result:
    """Result of an operation with success/failure tracking."""
    status: Status
    filepath: Optional[Path] = None
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == Status.SUCCESS
    
    @property
    def is_failure(self) -> bool:
        return self.status == Status.FAILURE


# ============================================================================
# DOMAIN MODEL
# ============================================================================

@dataclass(frozen=True)
class EmailFile:
    """Immutable email file data structure."""
    aap_group_id: str
    subject: str
    environment: str
    body: str
    model_name: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            "aap_group_id": self.aap_group_id,
            "subject": self.subject,
            "environment": self.environment,
            "body": self.body,
            "model_name": self.model_name,
        }
    
    def __post_init__(self):
        """Validate EmailFile after initialization."""
        if not self.aap_group_id:
            raise ValueError("aap_group_id cannot be empty")
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        if not self.subject:
            raise ValueError("subject cannot be empty")


# ============================================================================
# PRESENTATION / RENDERING
# ============================================================================

def generate_model_review_html(
    model_name: str,
    model_repo: str,
    review_date: str,
    days_due: str,
) -> str:
    """
    Generate HTML content for model review email.
    
    Args:
        model_name: Name of the model
        model_repo: Repository URL
        review_date: Date of review
        days_due: Number of days until due
        
    Returns:
        HTML formatted string
    """
    logger.debug(f"Generating HTML for model: {model_name}")
    
    return f"""
    <html>
      <body>
        <h2>Model Review Required</h2>
        <p><strong>Model:</strong> {model_name}</p>
        <p><strong>Repository:</strong> {model_repo}</p>
        <p><strong>Review Date:</strong> {review_date}</p>
        <p><strong>Days Due:</strong> {days_due}</p>
      </body>
    </html>
    """


# ============================================================================
# UTILITIES
# ============================================================================

def sanitise_json_file_name(aap_group_id: str, model_name: str) -> str:
    """
    Sanitize and format JSON filename.
    
    Args:
        aap_group_id: AAP Group ID
        model_name: Model name
        
    Returns:
        Sanitized filename in format: {aap_group_id}_{model_name}.json
    """
    clean_aap_id = re.sub(r"[^\w\-]", "_", str(aap_group_id))
    clean_model_name = re.sub(r"[^\w\-]", "_", str(model_name))
    filename = f"{clean_aap_id}_{clean_model_name}.json"
    
    logger.trace(f"Sanitized filename: {filename}")
    return filename


def validate_column_mapping(
    df: pd.DataFrame,
    column_mapping: Dict[str, str]
) -> None:
    """
    Validate that all required columns exist in DataFrame.
    
    Args:
        df: Input DataFrame
        column_mapping: Column mapping dictionary
        
    Raises:
        ValueError: If required columns are missing
    """
    required_keys = ["model_name", "repo_link", "review_date", "days_due", "aap_group_id"]
    missing_keys = [key for key in required_keys if key not in column_mapping]
    
    if missing_keys:
        raise ValueError(f"Missing required keys in column_mapping: {missing_keys}")
    
    # Check if mapped columns exist in DataFrame
    missing_columns = [
        column_mapping[key] 
        for key in required_keys 
        if column_mapping[key] not in df.columns
    ]
    
    if missing_columns:
        raise ValueError(f"Columns not found in DataFrame: {missing_columns}")
    
    logger.debug("Column mapping validation passed")


# ============================================================================
# CORE TRANSFORMATION LOGIC
# ============================================================================

HtmlRenderer = Callable[..., str]


def create_email_data(
    row: pd.Series,
    column_mapping: Dict[str, str],
    html_renderer: HtmlRenderer,
) -> EmailFile:
    """
    Pure function to transform DataFrame row into EmailFile.
    
    Args:
        row: DataFrame row
        column_mapping: Mapping of logical to actual column names
        html_renderer: Function to generate HTML body
        
    Returns:
        EmailFile instance
        
    Raises:
        ValueError: If required data is missing or invalid
    """
    try:
        # Extract data
        model_name = str(row[column_mapping["model_name"]])
        model_repo = str(row[column_mapping["repo_link"]])
        review_date = str(row[column_mapping["review_date"]])
        days_due = str(row[column_mapping["days_due"]])
        aap_group_id = str(row[column_mapping["aap_group_id"]])
        
        logger.trace(f"Creating email data for model: {model_name}, AAP: {aap_group_id}")
        
        # Generate HTML body
        body = html_renderer(
            model_name=model_name,
            model_repo=model_repo,
            review_date=review_date,
            days_due=days_due,
        )
        
        # Generate subject
        subject = f"ACTION REQUIRED: Model Review Due - {model_name}"
        
        # Create and return EmailFile
        email_file = EmailFile(
            aap_group_id=aap_group_id,
            subject=subject,
            environment="Discovery",
            body=body,
            model_name=model_name,
        )
        
        logger.debug(f"Successfully created EmailFile for {model_name}")
        return email_file
        
    except KeyError as e:
        logger.error(f"Missing column in row: {e}")
        raise ValueError(f"Required column not found: {e}") from e
    except Exception as e:
        logger.error(f"Error creating email data: {e}")
        raise


# ============================================================================
# INFRASTRUCTURE (FILE SYSTEM)
# ============================================================================

def write_email_json_file(
    email_file: EmailFile,
    output_dir: str,
) -> Result:
    """
    Write EmailFile to JSON file on disk.
    
    Args:
        email_file: EmailFile to write
        output_dir: Output directory path
        
    Returns:
        Result object with success/failure status
    """
    try:
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Output directory ensured: {output_path}")
        
        # Generate filename
        filename = sanitise_json_file_name(
            email_file.aap_group_id,
            email_file.model_name,
        )
        filepath = output_path / filename
        
        # Write JSON file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(email_file.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully wrote email file: {filepath}")
        return Result(status=Status.SUCCESS, filepath=filepath)
        
    except OSError as e:
        error_msg = f"File system error: {e}"
        logger.error(error_msg)
        return Result(status=Status.FAILURE, error=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error writing file: {e}"
        logger.exception(error_msg)  # Logs full traceback
        return Result(status=Status.FAILURE, error=error_msg)


# ============================================================================
# ORCHESTRATION (MAPPING FUNCTION)
# ============================================================================

def generate_email_data(
    df: pd.DataFrame,
    column_mapping: Dict[str, str],
    output_dir: str = "./email_data",
    html_renderer: HtmlRenderer = generate_model_review_html,
) -> pd.DataFrame:
    """
    MAPPING FUNCTION: Process DataFrame rows to generate email JSON files.
    
    This function:
    1. Validates input DataFrame and column mapping
    2. Processes each row to create EmailFile
    3. Writes JSON files to disk
    4. Tracks success/failure in "json_writing" column
    
    Args:
        df: Input DataFrame with email data
        column_mapping: Mapping of logical to actual column names
        output_dir: Directory for output JSON files
        html_renderer: Function to generate HTML body (injectable for testing)
        
    Returns:
        DataFrame with added "json_writing" column containing "successful" or "unsuccessful"
    """
    logger.info(f"Starting email data generation for {len(df)} rows")
    logger.debug(f"Output directory: {output_dir}")
    logger.debug(f"Column mapping: {column_mapping}")
    
    # Validate inputs
    try:
        validate_column_mapping(df, column_mapping)
    except ValueError as e:
        logger.error(f"Validation failed: {e}")
        raise
    
    # Create copy to avoid modifying original
    df_result = df.copy()
    
    # Initialize tracking column
    df_result["json_writing"] = Status.FAILURE.value
    
    # Track statistics
    success_count = 0
    failure_count = 0
    
    # Process each row
    for idx, row in df_result.iterrows():
        try:
            logger.debug(f"Processing row {idx}")
            
            # Step 1: Create EmailFile (pure transformation)
            email_file = create_email_data(
                row=row,
                column_mapping=column_mapping,
                html_renderer=html_renderer,
            )
            
            # Step 2: Write to file system
            result = write_email_json_file(
                email_file=email_file,
                output_dir=output_dir,
            )
            
            # Step 3: Update tracking column
            if result.is_success:
                df_result.at[idx, "json_writing"] = Status.SUCCESS.value
                success_count += 1
                logger.debug(f"Row {idx} processed successfully")
            else:
                df_result.at[idx, "json_writing"] = Status.FAILURE.value
                failure_count += 1
                logger.warning(f"Row {idx} failed: {result.error}")
                
        except Exception as e:
            # Catch-all for unexpected errors
            df_result.at[idx, "json_writing"] = Status.FAILURE.value
            failure_count += 1
            logger.error(f"Unexpected error processing row {idx}: {e}", exc_info=True)
    
    # Log summary
    logger.info(
        f"Email generation complete: "
        f"{success_count} successful, {failure_count} failed, "
        f"{len(df)} total"
    )
    
    if failure_count > 0:
        logger.warning(f"{failure_count} rows failed to generate email files")
    
    return df_result


# ============================================================================
# CONFIGURATION
# ============================================================================

def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "1 week",
) -> None:
    """
    Configure loguru logger.
    
    Args:
        level: Logging level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        rotation: When to rotate log file (size or time based)
        retention: How long to keep old logs
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler with color
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level=level,
        colorize=True,
    )
    
    # Add file handler if specified
    if log_file:
        logger.add(
            sink=log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip",
        )
        logger.info(f"Logging to file: {log_file}")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    """Example usage with logging."""
    
    # Configure logging
    configure_logging(
        level="DEBUG",  # Change to "INFO" for production
        log_file="email_generation.log",
    )
    
    logger.info("="*60)
    logger.info("Email Data Generation - Enhanced Version")
    logger.info("="*60)
    
    # Define column mapping
    column_mapping = {
        "model_name": "model_name",
        "repo_link": "repo_link",
        "review_date": "review_date",
        "days_due": "days_due",
        "aap_group_id": "aap_group_id",
    }
    
    # Sample data
    df_input = pd.DataFrame({
        "model_name": ["ModelA", "ModelB", "ModelC"],
        "repo_link": [
            "https://repo.com/modelA",
            "https://repo.com/modelB",
            "https://repo.com/modelC",
        ],
        "review_date": ["2026-02-15", "2026-02-20", "2026-02-25"],
        "days_due": ["14", "19", "24"],
        "aap_group_id": ["AAP001", "AAP002", "AAP003"],
    })
    
    logger.info(f"Input DataFrame: {len(df_input)} rows")
    
    # Generate email data
    df_output = generate_email_data(
        df=df_input,
        column_mapping=column_mapping,
        output_dir="./model_review_emails",
    )
    
    # Show results
    logger.info("Results:")
    logger.info(f"\n{df_output[['model_name', 'aap_group_id', 'json_writing']]}")
    
    # Summary
    success_count = (df_output["json_writing"] == Status.SUCCESS.value).sum()
    failure_count = len(df_output) - success_count
    
    logger.info(f"Total: {len(df_output)}, Success: {success_count}, Failure: {failure_count}")
    
    return df_output


if __name__ == "__main__":
    df_result = main()