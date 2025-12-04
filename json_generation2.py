import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def generate_model_review_html(model_name: str, model_repo: str, review_date: str, days_overdue: int) -> str:
    """
    Generate HTML email content for a single model review notification.
    
    Parameters:
    -----------
    model_name : str
        Name of the model requiring review
    model_repo : str
        Git repository URL for the model
    review_date : str
        Last review date (format: YYYY-MM-DD)
    days_overdue : int
        Number of days overdue for review
    
    Returns:
    --------
    str
        Complete HTML email content
    """
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Model Review Due</title>
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #3a3a3a;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #3a3a3a;">
        <tr>
            <td align="center" style="padding: 20px;">
                <table width="900" cellpadding="0" cellspacing="0" border="0" style="background-color: #3a3a3a; color: #ffffff;">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 30px 40px; text-align: center;">
                            <h1 style="margin: 0; font-size: 42px; font-weight: bold; color: #b8c5d6;">Model Review Due</h1>
                        </td>
                    </tr>
                    
                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 0 40px 20px 40px;">
                            <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6; color: #d0d0d0;">Hello,</p>
                            
                            <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6; color: #d0d0d0;">
                                Our records indicate that one of your models currently in production is overdue for its scheduled review. Timely reviews help maintain trust in our AI systems, support responsible innovation, and safeguard operational integrity.
                            </p>
                            
                            <p style="margin: 0 0 30px 0; font-size: 14px; line-height: 1.6; color: #d0d0d0;">
                                If this model is no longer required, please follow the decommissioning steps outlined in <a href="#" style="color: #6ba3d4; text-decoration: underline;">Model Development Lifecycle</a> documentation.
                            </p>
                            
                            <!-- Model Details Section -->
                            <h2 style="margin: 0 0 15px 0; font-size: 20px; font-weight: bold; color: #4db8ff;">Model Details</h2>
                            
                            <table width="100%" cellpadding="12" cellspacing="0" border="1" style="border-collapse: collapse; border: 1px solid #666666; margin-bottom: 30px;">
                                <tr>
                                    <td style="background-color: #2a2a2a; color: #ffffff; font-weight: bold; border: 1px solid #666666; padding: 12px; width: 30%;">Field</td>
                                    <td style="background-color: #2a2a2a; color: #ffffff; font-weight: bold; border: 1px solid #666666; padding: 12px;">Value</td>
                                </tr>
                                <tr>
                                    <td style="background-color: #3a3a3a; color: #d0d0d0; border: 1px solid #666666; padding: 12px;">Model Name</td>
                                    <td style="background-color: #3a3a3a; color: #d0d0d0; border: 1px solid #666666; padding: 12px;">{model_name}</td>
                                </tr>
                                <tr>
                                    <td style="background-color: #3a3a3a; color: #d0d0d0; border: 1px solid #666666; padding: 12px;">Model Repo</td>
                                    <td style="background-color: #3a3a3a; color: #d0d0d0; border: 1px solid #666666; padding: 12px;">
                                        <a href="{model_repo}" style="color: #6ba3d4; text-decoration: underline;">{model_repo}</a>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="background-color: #3a3a3a; color: #d0d0d0; border: 1px solid #666666; padding: 12px;">Last review date</td>
                                    <td style="background-color: #3a3a3a; color: #d0d0d0; border: 1px solid #666666; padding: 12px;">{review_date}</td>
                                </tr>
                                <tr>
                                    <td style="background-color: #3a3a3a; color: #d0d0d0; border: 1px solid #666666; padding: 12px;">Days overdue</td>
                                    <td style="background-color: #3a3a3a; color: #ff4444; font-weight: bold; border: 1px solid #666666; padding: 12px;">{days_overdue} days</td>
                                </tr>
                            </table>
                            
                            <!-- Action Required Section -->
                            <h2 style="margin: 0 0 15px 0; font-size: 20px; font-weight: bold; color: #4db8ff;">Action Required</h2>
                            
                            <p style="margin: 0 0 15px 0; font-size: 14px; line-height: 1.6; color: #d0d0d0;">
                                Please initiate a full review of the model as soon as possible. This should include:
                            </p>
                            
                            <table cellpadding="0" cellspacing="0" border="0" style="margin: 0 0 30px 20px;">
                                <tr>
                                    <td style="color: #d0d0d0; font-size: 14px; padding: 4px 0; vertical-align: top;">•</td>
                                    <td style="color: #d0d0d0; font-size: 14px; padding: 4px 0 4px 10px;">Performance validation against current production data.</td>
                                </tr>
                                <tr>
                                    <td style="color: #d0d0d0; font-size: 14px; padding: 4px 0; vertical-align: top;">•</td>
                                    <td style="color: #d0d0d0; font-size: 14px; padding: 4px 0 4px 10px;">Review of model assumptions and input features.</td>
                                </tr>
                                <tr>
                                    <td style="color: #d0d0d0; font-size: 14px; padding: 4px 0; vertical-align: top;">•</td>
                                    <td style="color: #d0d0d0; font-size: 14px; padding: 4px 0 4px 10px;">Renew of approval and sign-off from relevant stakeholders.</td>
                                </tr>
                                <tr>
                                    <td style="color: #d0d0d0; font-size: 14px; padding: 4px 0; vertical-align: top;">•</td>
                                    <td style="color: #d0d0d0; font-size: 14px; padding: 4px 0 4px 10px;">Update of model documentation, including DOCATO files.</td>
                                </tr>
                            </table>
                            
                            <!-- Note Box -->
                            <table width="100%" cellpadding="15" cellspacing="0" border="0" style="margin-bottom: 30px; background-color: #2a2a2a; border-top: 2px solid #666666; border-bottom: 2px solid #666666;">
                                <tr>
                                    <td style="text-align: center;">
                                        <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #d0d0d0;">
                                            <strong>Note:</strong> You will continue to receive this notification until the DOCATO record is updated to reflect the completed review.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Footer Text -->
                            <p style="margin: 0 0 10px 0; font-size: 14px; line-height: 1.6; color: #d0d0d0;">
                                This review supports our broader strategy for model governance, ensuring that all deployed models remain fit-for-purpose, compliant, and aligned with enterprise standards.
                            </p>
                            
                            <p style="margin: 0 0 40px 0; font-size: 14px; line-height: 1.6; color: #d0d0d0;">
                                For further assistance please refer to our <a href="#" style="color: #6ba3d4; text-decoration: underline;">Support Page</a>.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Signature -->
                    <tr>
                        <td style="padding: 0 40px 40px 40px; background-color: #4a4a5a;">
                            <p style="margin: 0 0 5px 0; font-size: 16px; font-weight: bold; color: #ffffff;">ModelOps Team</p>
                            <p style="margin: 0 0 5px 0; font-size: 14px; color: #d0d0d0;">Data Science - Model Operations</p>
                            <p style="margin: 0; font-size: 14px; color: #d0d0d0;">Australian Taxation Office</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    return html_template


def sanitize_filename(text: str) -> str:
    """
    Sanitize text for use in filenames.
    
    Parameters:
    -----------
    text : str
        Text to sanitize
    
    Returns:
    --------
    str
        Sanitized text safe for use in filenames
    """
    safe_text = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in text)
    return safe_text.replace(' ', '_')


def create_email_data(
    row: pd.Series,
    column_mapping: Dict[str, str]
) -> Dict[str, any]:
    """
    Create email data dictionary from a DataFrame row.
    
    This is a pure function with no side effects - it only transforms data.
    
    Parameters:
    -----------
    row : pd.Series
        Single row from DataFrame containing model information
    column_mapping : Dict[str, str]
        Dictionary mapping standard field names to DataFrame column names
        Expected keys: 'model_name', 'model_repo', 'review_date', 'days_overdue', 'group_id'
    
    Returns:
    --------
    Dict[str, any]
        Dictionary containing model data and HTML content
        
    Example:
    --------
    >>> column_mapping = {
    ...     'model_name': 'model_name',
    ...     'model_repo': 'model_repo',
    ...     'review_date': 'model_review_date',
    ...     'days_overdue': 'days_overdue',
    ...     'group_id': 'group_id'
    ... }
    >>> email_data = create_email_data(df.iloc[0], column_mapping)
    """
    # Extract data using column mapping
    model_name = str(row[column_mapping['model_name']])
    model_repo = str(row[column_mapping['model_repo']])
    review_date = str(row[column_mapping['review_date']])
    days_overdue = int(row[column_mapping['days_overdue']])
    group_id = str(row[column_mapping['group_id']])
    
    # Generate HTML content
    html_content = generate_model_review_html(
        model_name=model_name,
        model_repo=model_repo,
        review_date=review_date,
        days_overdue=days_overdue
    )
    
    # Create email data structure
    email_data = {
        "model_name": model_name,
        "group_id": group_id,
        "review_date": review_date,
        "days_overdue": days_overdue,
        "model_repo": model_repo,
        "html_content": html_content,
        "filename": f"{sanitize_filename(model_name)}_review_notification.json"
    }
    
    return email_data


def generate_emails_data(
    df: pd.DataFrame,
    column_mapping: Optional[Dict[str, str]] = None
) -> List[Dict[str, any]]:
    """
    Generate email data for all models in DataFrame.
    
    This is a pure function that returns data without performing I/O operations.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing models requiring review
    column_mapping : Optional[Dict[str, str]]
        Dictionary mapping standard field names to DataFrame column names
        If None, uses default column names
    
    Returns:
    --------
    List[Dict[str, any]]
        List of email data dictionaries, one per model
        
    Raises:
    -------
    ValueError
        If DataFrame is empty or missing required columns
    """
    # Input validation
    if df is None or df.empty:
        logger.warning("Empty or None DataFrame provided. Returning empty list.")
        return []
    
    # Default column mapping
    if column_mapping is None:
        column_mapping = {
            'model_name': 'model_name',
            'model_repo': 'model_repo',
            'review_date': 'model_review_date',
            'days_overdue': 'days_overdue',
            'group_id': 'group_id'
        }
    
    # Validate required columns exist
    missing_cols = [col for col in column_mapping.values() if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in DataFrame: {missing_cols}")
    
    # Generate email data for each row
    emails_data = []
    for idx, row in df.iterrows():
        try:
            email_data = create_email_data(row, column_mapping)
            emails_data.append(email_data)
        except Exception as e:
            logger.error(f"Error processing row {idx}: {e}")
            continue
    
    logger.info(f"Generated email data for {len(emails_data)} models.")
    return emails_data


def write_email_json_files(
    emails_data: List[Dict[str, any]],
    output_dir: str = './email_notifications'
) -> None:
    """
    Write email data to JSON files.
    
    This function handles all filesystem I/O operations.
    
    Parameters:
    -----------
    emails_data : List[Dict[str, any]]
        List of email data dictionaries from generate_emails_data()
    output_dir : str
        Directory path where JSON files will be saved
    
    Returns:
    --------
    None
        Writes JSON files to disk
        
    Raises:
    -------
    IOError
        If unable to create directory or write files
    """
    if not emails_data:
        logger.warning("No email data provided. Nothing to write.")
        return
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output directory {output_dir}: {e}")
        raise
    
    logger.info(f"Writing email JSON files to: {output_path.absolute()}")
    
    # Write each email to a JSON file
    success_count = 0
    for email_data in emails_data:
        filename = email_data.get('filename', 'unknown_model.json')
        filepath = output_path / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(email_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Generated email JSON: {filename}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to write file {filename}: {e}")
            continue
    
    logger.info(f"Successfully wrote {success_count}/{len(emails_data)} email JSON files.")


def process_model_reviews(
    df: pd.DataFrame,
    output_dir: str = './email_notifications',
    column_mapping: Optional[Dict[str, str]] = None
) -> List[Dict[str, any]]:
    """
    Main orchestration function for processing model reviews.
    
    This function coordinates the entire workflow:
    1. Generate email data from DataFrame
    2. Write email data to JSON files
    3. Return the generated data for inspection/testing
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing models requiring review
    output_dir : str
        Directory path where JSON files will be saved
    column_mapping : Optional[Dict[str, str]]
        Dictionary mapping standard field names to DataFrame column names
    
    Returns:
    --------
    List[Dict[str, any]]
        List of generated email data (useful for verification/testing)
    """
    # Step 1: Generate email data (pure transformation)
    emails_data = generate_emails_data(df, column_mapping)
    
    # Step 2: Write to files (I/O operation)
    if emails_data:
        write_email_json_files(emails_data, output_dir)
    
    return emails_data


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Sample data (simulating output from get_model_required_review + calculate_days_overdue)
    sample_data = pd.DataFrame({
        'model_name': [
            'Titanic Survivability Prediction Model',
            'Customer Churn Prediction Model',
            'Fraud Detection Model'
        ],
        'model_repo': [
            'https://gitlab.sdpaep.aws.prod.atohnet.gov.au/modelops/titanic-classification-example.git',
            'https://gitlab.sdpaep.aws.prod.atohnet.gov.au/modelops/churn-prediction.git',
            'https://gitlab.sdpaep.aws.prod.atohnet.gov.au/modelops/fraud-detection.git'
        ],
        'model_review_date': ['2024-03-28', '2024-02-15', '2024-04-10'],
        'days_overdue': [325, 367, 302],
        'group_id': ['DS-001', 'DS-002', 'DS-003']
    })
    
    print("Sample DataFrame:")
    print(sample_data)
    print("\n" + "="*80 + "\n")
    
    # Method 1: Use the orchestration function (recommended for production)
    emails_data = process_model_reviews(
        df=sample_data,
        output_dir='./email_notifications'
    )
    
    print("\nJSON files generated successfully!")
    print(f"Generated {len(emails_data)} email notifications.")
    
    # Method 2: Use functions separately (useful for testing/debugging)
    print("\n" + "="*80)
    print("Alternative: Using functions separately\n")
    
    # Generate data (testable without I/O)
    emails_data_test = generate_emails_data(sample_data)
    print(f"Generated {len(emails_data_test)} email data objects")
    
    # Inspect first email (without writing to disk)
    if emails_data_test:
        first_email = emails_data_test[0]
        print(f"\nFirst email filename: {first_email['filename']}")
        print(f"Model: {first_email['model_name']}")
        print(f"Days overdue: {first_email['days_overdue']}")
    
    # Write to different location
    write_email_json_files(emails_data_test, './test_output')