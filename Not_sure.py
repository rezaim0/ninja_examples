# ... (other imports and test functions)

def test_module_package_access_error(custom_caplog):
    """
    Test scenario where accessing a module's package raises ModuleNotFoundError
    """
    with patch('importlib.resources.files') as mock_files:
        # Set up mock modules package
        mock_modules_pkg = MagicMock()
        mock_entry_TMA = create_mock_module_entry('TMA')
        mock_modules_pkg.iterdir.return_value = [mock_entry_TMA]
        
        # Configure mock_files to return our mock modules_pkg or raise ModuleNotFoundError
        def mock_files_side_effect(package):
            if package == 'project_name.modules':
                return mock_modules_pkg
            elif package == 'project_name.modules.TMA':
                raise ModuleNotFoundError(f"No module named '{package}'")
            else:
                raise ModuleNotFoundError(f"No module named '{package}'")
        
        mock_files.side_effect = mock_files_side_effect
        
        # Call the function
        result = get_sql_file_paths(['TMA'])
        
        # Assert an empty dictionary is returned
        assert result == {}
        
        # Retrieve log contents
        log_contents = custom_caplog.getvalue()
        
        # Assert the expected warning message is present
        assert f"An error occurred while accessing project_name.modules.TMA: No module named 'project_name.modules.TMA'" in log_contents

def test_sql_file_access_error(custom_caplog):
    """
    Test scenario where accessing the SQL file raises FileNotFoundError
    """
    with patch('importlib.resources.files') as mock_files:
        # Set up mock modules package
        mock_modules_pkg = MagicMock()
        mock_entry_TMA = create_mock_module_entry('TMA')
        mock_modules_pkg.iterdir.return_value = [mock_entry_TMA]
        
        # Configure mock SQL file to raise FileNotFoundError on resolve()
        mock_sql_file = MagicMock()
        mock_sql_file.is_file.return_value = True
        mock_sql_file.resolve.side_effect = FileNotFoundError("File not found")
        
        # Configure mock for module package
        mock_module_pkg = MagicMock()
        mock_module_pkg.__truediv__.return_value = mock_sql_file
        
        # Configure mock_files to return our mock objects
        def mock_files_side_effect(package):
            if package == 'project_name.modules':
                return mock_modules_pkg
            elif package == 'project_name.modules.TMA':
                return mock_module_pkg
            else:
                raise ModuleNotFoundError(f"No module named '{package}'")
        
        mock_files.side_effect = mock_files_side_effect
        
        # Call the function
        result = get_sql_file_paths(['TMA'])
        
        # Assert an empty dictionary is returned
        assert result == {}
        
        # Retrieve log contents
        log_contents = custom_caplog.getvalue()
        
        # Assert the expected warning message is present
        assert "An error occurred while accessing project_name.modules.TMA: File not found" in log_contents
