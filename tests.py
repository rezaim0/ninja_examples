# Filter and sort pickle files based on models that appear more than once
def get_duplicate_models(pickle_file_paths):
    # Extract base model names (removing timestamps)
    base_model_names = {}
    for file_path in pickle_file_paths:
        # Extract just the file name from the path
        file_name = os.path.basename(file_path)
        # Remove the timestamp pattern (assuming format like _YYYYMMDD_HHMMSS.pkl)
        base_name = re.sub(r'_\d{8}_\d{6}\.pkl$', '', file_name)
        if base_name in base_model_names:
            base_model_names[base_name].append(file_path)
        else:
            base_model_names[base_name] = [file_path]
    
    # Find models that appear exactly twice
    duplicate_models = {model: paths for model, paths in base_model_names.items() 
                       if len(paths) == 2}
    
    # If no models appear exactly twice, try models that appear more than once
    if not duplicate_models:
        duplicate_models = {model: paths for model, paths in base_model_names.items() 
                           if len(paths) > 1}
    
    # If still empty, just take the first model
    if not duplicate_models and base_model_names:
        first_model = next(iter(base_model_names))
        duplicate_models = {first_model: base_model_names[first_model]}
    
    # Return the first duplicate model found (or empty if none)
    return next(iter(duplicate_models.values())) if duplicate_models else []