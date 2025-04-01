import re
import datetime
from typing import Dict, List


def extract_models_info(file_names: List[str]) -> Dict[str, str]:
    """
    Extract model names and formatted date-times from a list of filenames.
    
    Args:
        file_names (List[str]): List of filenames containing model information.
                                Expected basic pattern: "<prefix>_<model_name>_YYYYMMDD_HHMMSS.<extension>"
                         
    Returns:
        Dict[str, str]: A dictionary where:
            - key: model_name (str): The extracted and formatted model name.
            - value: date_time (str): The formatted date and time in "YYYY-MM-DD HH:MM:SS" format.
            
    Raises:
        ValueError: If a filename doesn't match the expected pattern.
        
    Examples:
        >>> files = [
        ...     "docato_titanic_survivability_prediction_model_20241022_165531.pkl",
        ...     "docato_wre_nexus_pipeline_-_claim_relevance_model_20241021_153632.pkl"
        ... ]
        >>> extract_models_info(files)
        {
            'Titanic Survivability Prediction Model': '2024-10-22 16:55:31',
            'Wre Nexus Pipeline - Claim Relevance Model': '2024-10-21 15:36:32'
        }
    """
    result = {}
    
    for file_name in file_names:
        model_name, date_time = _parse_single_file(file_name)
        result[model_name] = date_time
    
    return result


def _parse_single_file(file_name: str) -> tuple[str, str]:
    """
    Parse a single filename to extract model name and date-time.
    Helper function for extract_models_info.
    """
    # Match the date and time pattern at the end of the filename
    date_time_pattern = r"_(\d{8})_(\d{6})(?:\.\w+)?$"
    date_time_match = re.search(date_time_pattern, file_name)
    
    if not date_time_match:
        raise ValueError(f"Filename '{file_name}' doesn't contain the expected date-time pattern (YYYYMMDD_HHMMSS).")
    
    # Extract date and time parts
    date_part, time_part = date_time_match.groups()
    
    # Extract the model name by removing the prefix, extension, and date-time part
    # First remove any extension
    base_name = re.sub(r"\.\w+$", "", file_name)
    
    # Remove the date-time part
    base_name = re.sub(rf"_{date_part}_{time_part}$", "", base_name)
    
    # Remove any common prefix (like "docato_")
    if base_name.startswith("docato_"):
        model_name_raw = base_name[len("docato_"):]
    else:
        # Find the first underscore as the potential prefix separator
        first_underscore = base_name.find("_")
        if first_underscore > 0:
            model_name_raw = base_name[first_underscore+1:]
        else:
            model_name_raw = base_name
    
    # Format the model name (replace underscores with spaces and capitalize words)
    # Handle special case of hyphen with spaces around it
    model_name_raw = model_name_raw.replace("_-_", " - ")
    
    # Replace remaining underscores with spaces
    words = model_name_raw.replace("_", " ").split()
    
    # Special handling for hyphen - don't add spaces around lone hyphens
    model_name = ""
    for i, word in enumerate(words):
        if word == "-" and i > 0 and i < len(words) - 1:
            model_name += " - "
        else:
            if i > 0:
                model_name += " "
            model_name += word.capitalize()
    
    # Parse and format the date-time
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
    
    return model_name, date_time_formatted


# For backward compatibility, maintain the original function name 
# but adapt it to work with a single file
def extract_model_info(file_name: str) -> tuple[str, str]:
    """
    Extract the model name and formatted date-time from a given filename.
    
    Args:
        file_name (str): The name of the file containing model information.
                         
    Returns:
        tuple[str, str]: A tuple containing:
            - model_name (str): The extracted and formatted model name.
            - date_time (str): The formatted date and time in "YYYY-MM-DD HH:MM:SS" format.
    """
    return _parse_single_file(file_name)


# Test examples
if __name__ == "__main__":
    file_names = [
        "docato_titanic_survivability_prediction_model_20241022_165531.pkl",
        "docato_wre_nexus_pipeline_-_claim_relevance_model_20241021_153632.pkl",
        # Additional test cases can be added here
    ]
    
    # Test the single file function
    print("Testing single file function:")
    for fn in file_names:
        try:
            model_name, date_time = extract_model_info(fn)
            print(f"File: {fn}")
            print(f"Model Name: {model_name}")
            print(f"Date Time: {date_time}")
            print("-" * 50)
        except ValueError as e:
            print(f"Error with {fn}: {e}")
            print("-" * 50)
    
    # Test the multi-file function
    print("\nTesting multi-file function:")
    try:
        models_info = extract_models_info(file_names)
        print("Models Dictionary:")
        for model, date in models_info.items():
            print(f"  {model}: {date}")
    except ValueError as e:
        print(f"Error: {e}")