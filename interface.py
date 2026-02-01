

import pandas as pd
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple, Optional
import re

# ======================================================
# PLACEHOLDER for generate_model_review_html 
# ======================================================

def generate_model_review_html(
    model_name: str,
    model_repo: str,
    review_date: str,
    days_due: str
) -> str:
    """
    Generate HTML content for model review email.
    Replace this with your actual implementation.
    """
    # This is a placeholder - use your actual function
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

@dataclass
class EmailFile:
    """Data class for email file information."""
    aap_group_id: str
    subject: str
    environment: str
    body: str
    model_name: str


def create_email_data(
    row: pd.Series,
    column_mapping: dict[str, str]
) -> EmailFile:
    """
    Pure function to create EmailFile dataclass from a DataFrame row.
    
    Args:
        row: A pandas Series (DataFrame row)
        column_mapping: Dictionary mapping logical names to actual column names
        
    Returns:
        EmailFile dataclass instance
    """
    # Extract data from row using column mapping
    model_name = str(row[column_mapping["model_name"]])
    model_repo = str(row[column_mapping["repo_link"]])
    review_date = str(row[column_mapping["review_date"]])  
    days_due = str(row[column_mapping["days_due"]])        
    aap_group_id = str(row[column_mapping["aap_group_id"]])
    
    # Generate HTML content
    html_content = generate_model_review_html(
        model_name=model_name,
        model_repo=model_repo,
        review_date=review_date,  # Fixed: was "review_data"
        days_due=days_due,
    )
    
    # Generate email subject
    email_subject_name = f"ACTION REQUIRED: Model Review Due - {model_name}"  # Fixed: was "Revirew"
    
    return EmailFile(
        aap_group_id=aap_group_id,  # Fixed: matches dataclass field name
        subject=email_subject_name,
        environment="Discovery", 
        body=html_content,
        model_name=model_name,
    )





# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitise_json_file_name(aap_group_id: str, model_name: str) -> str:
    """
    Create sanitized filename in format: {aap_group_id}_{model_name}.json
    
    Args:
        aap_group_id: AAP Group ID
        model_name: Model name
        
    Returns:
        Sanitized filename string
    """
    # Remove special characters, keep alphanumeric, underscore, hyphen
    clean_aap_id = re.sub(r'[^\w\-]', '_', str(aap_group_id))
    clean_model_name = re.sub(r'[^\w\-]', '_', str(model_name))
    
    return f"{clean_aap_id}_{clean_model_name}.json"


def write_email_json_file(
    email_file: EmailFile,
    output_dir: str = './email_data'
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Write EmailFile to JSON with filename: {aap_group_id}_{model_name}.json
    
    Args:
        email_file: EmailFile dataclass instance
        output_dir: Directory for JSON files
        
    Returns:
        (success: bool, filepath: str|None, error: str|None)
    """
    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate filename: {aap_group_id}_{model_name}.json
        filename = sanitise_json_file_name(
            email_file.aap_group_id,
            email_file.model_name
        )
        filepath = Path(output_dir) / filename
        
        # Convert dataclass to dict for JSON serialization
        email_dict = {
            'aap_group_id': email_file.aap_group_id,
            'subject': email_file.subject,
            'environment': email_file.environment,
            'body': email_file.body,
            'model_name': email_file.model_name
        }
        
        # Write JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(email_dict, f, indent=2, ensure_ascii=False)
        
        return (True, str(filepath), None)
        
    except Exception as e:
        return (False, None, str(e))


# ============================================================================
# MAPPING FUNCTION
# ============================================================================

def generate_email_data(
    df: pd.DataFrame,
    column_mapping: dict[str, str],
    output_dir: str = './email_data'
) -> pd.DataFrame:
    """
    MAPPING FUNCTION: Generate email JSON files and track success/failure.
    
    Process:
    1. Take DataFrame input
    2. Validate/clean data
    3. For each row:
       - Create EmailFile using create_email_data()
       - Write JSON using write_email_json_file()
       - Track success/failure
    4. Return DataFrame with "json_writing" column
    
    Args:
        df: Input DataFrame with email data
        column_mapping: Dictionary mapping logical column names to actual column names
        output_dir: Directory where JSON files will be saved
        
    Returns:
        DataFrame with added "json_writing" column:
        - "successful": JSON file written successfully
        - "unsuccessful": JSON file writing failed
    """
    # Create copy to avoid modifying original
    df_result = df.copy()
    
    # TODO: Add your validation/cleaning logic here
    # Example:
    # df_result = validate_required_columns(df_result, column_mapping)
    # df_result = clean_data(df_result)
    
    # Initialize tracking column (default to unsuccessful)
    df_result['json_writing'] = 'unsuccessful'
    
    # Process each row
    for idx, row in df_result.iterrows():
        try:
            # Step 1: Create EmailFile from row (pure function)
            email_file = create_email_data(row, column_mapping)
            
            # Step 2: Write JSON file
            success, filepath, error = write_email_json_file(
                email_file,
                output_dir=output_dir
            )
            
            # Step 3: Update tracking based on result
            if success:
                df_result.at[idx, 'json_writing'] = 'successful'
            else:
                df_result.at[idx, 'json_writing'] = 'unsuccessful'
                # Optional: Log error for debugging
                print(f"Row {idx} failed: {error}")
                
        except Exception as e:
            # Handle unexpected errors
            df_result.at[idx, 'json_writing'] = 'unsuccessful'
            print(f"Unexpected error at row {idx}: {e}")
    
    return df_result


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def main():
    """Example usage with your actual structure."""
    
    print("Email Data Generation - Your Implementation")
    print("="*60)
    
    # Define column mapping (maps logical names to your actual column names)
    column_mapping = {
        "model_name": "model_name",        # Replace with your actual column name
        "repo_link": "repo_link",          # Replace with your actual column name
        "review_date": "review_date",      # Replace with your actual column name
        "days_due": "days_due",            # Replace with your actual column name
        "aap_group_id": "aap_group_id"     # Replace with your actual column name
    }
    
    # Sample input data (matching your structure)
    df_input = pd.DataFrame({
        'model_name': ['ModelA', 'ModelB', 'ModelC'],
        'repo_link': ['https://repo.com/modelA', 'https://repo.com/modelB', 'https://repo.com/modelC'],
        'review_date': ['2026-02-15', '2026-02-20', '2026-02-25'],
        'days_due': ['14', '19', '24'],
        'aap_group_id': ['AAP001', 'AAP002', 'AAP003']
    })
    
    print("\n1. Input DataFrame:")
    print(df_input)
    
    print("\n2. Generating email data files...\n")
    
    # Call the mapping function
    df_output = generate_email_data(
        df_input, 
        column_mapping=column_mapping,
        output_dir='./model_review_emails'
    )
    
    print("3. Output DataFrame (with tracking):")
    print(df_output[['model_name', 'aap_group_id', 'json_writing']])
    
    # Summary
    successful = (df_output['json_writing'] == 'successful').sum()
    unsuccessful = len(df_output) - successful
    
    print(f"\n4. Summary:")
    print(f"   Total rows: {len(df_output)}")
    print(f"   Successful: {successful}")
    print(f"   Unsuccessful: {unsuccessful}")
    
    # Show next steps
    print("\n5. Next steps in your code:")
    print("   df_successful = df_output[df_output['json_writing'] == 'successful']")
    print("   log_table = update_log_table(df_successful)")
    
    return df_output


if __name__ == "__main__":
    df_result = main()
    
    print("\n" + "="*60)
    print("FILES GENERATED")
    print("="*60)
    print("\nFormat: {aap_group_id}_{model_name}.json")
    print("Example: AAP001_ModelA.json")