import re
import datetime
from typing import Dict, List


def extract_models_info(file_paths: List[str]) -> Dict[str, str]:
    """
    Extract model names and dates from full file paths.
    
    Args:
        file_paths (List[str]): List of file paths with pattern:
                               "/path/to/docato_<model_name>_YYYYMMDD_HHMMSS.pkl"
                         
    Returns:
        Dict[str, str]: A dictionary where:
            - key: The model name portion of the filename (without path, prefix, and date)
            - value: The formatted date and time in "YYYY-MM-DD HH:MM:SS" format.
            
    Examples:
        >>> files = [
        ...     "/efs/shared/MACATO_test_data/docato_titanic_survivability_prediction_model_20241022_165531.pkl",
        ...     "/efs/shared/MACATO_test_data/docato_wre_nexus_pipeline_-_claim_relevance_model_20241021_153632.pkl"
        ... ]
        >>> extract_models_info(files)
        {
            'titanic_survivability_prediction_model': '2024-10-22 16:55:31',
            'wre_nexus_pipeline_-_claim_relevance_model': '2024-10-21 15:36:32'
        }
    """
    result = {}
    
    for file_path in file_paths:
        # Extract just the filename from the path
        filename = file_path.split("/")[-1]
        
        # Use regex to extract the model name and date components
        pattern = r"docato_(.+)_(\d{8})_(\d{6})\.pkl$"
        match = re.search(pattern, filename)
        
        if not match:
            raise ValueError(f"Filename '{filename}' doesn't match the expected pattern.")
        
        model_name, date_part, time_part = match.groups()
        
        # Format the date-time
        try:
            year = int(date_part[:4])
            month = int(date_part[4:6])
            day = int(date_part[6:8])
            hour = int(time_part[:2])
            minute = int(time_part[2:4])
            second = int(time_part[4:6])
            
            date_obj = datetime.datetime(year, month, day, hour, minute, second)
            date_time_formatted = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid date-time format in filename: {e}")
        
        result[model_name] = date_time_formatted
    
    return result


# Test example
if __name__ == "__main__":
    file_paths = [
        "/efs/shared/MACATO_test_data/docato_titanic_survivability_prediction_model_20241022_165531.pkl",
        "/efs/shared/MACATO_test_data/docato_wre_nexus_pipeline_-_claim_relevance_model_20241021_153632.pkl"
    ]
    
    try:
        models_info = extract_models_info(file_paths)
        print("Models Dictionary:")
        for model, date in models_info.items():
            print(f"  {model}: {date}")
    except ValueError as e:
        print(f"Error: {e}")