import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import List, Dict
from my_package.shared.util import get_sql_file_paths

def create_mock_module_entry(name: str, has_sql_file: bool = True):
    """
    Helper function to create a mock module entry for testing.

    Args:
        name (str): Name of the module
        has_sql_file (bool, optional): Whether the module should have an SQL file. Defaults to True.

    Returns:
        MagicMock: A mock module entry
    """
    mock_entry = MagicMock()
    mock_entry.name = name
    mock_entry.is_dir.return_value = True

    # Create mock for SQL file
    mock_sql_file = MagicMock()
    mock_sql_file.is_file.return_value = has_sql_file
    mock_sql_file.resolve.return_value = Path(f'/path/to/{name}/{name}.sql')

    # Configure __truediv__ to return the mock SQL file
    def truediv_side_effect(x):
        if x == f"{name}.sql":
            return mock_sql_file
        else:
            return MagicMock()
    mock_entry.__truediv__.side_effect = truediv_side_effect

    return mock_entry

def test_get_sql_file_paths():
    with patch('importlib.resources.files') as mock_files:
        # Set up mock modules package
        mock_modules_pkg = MagicMock()
        mock_entry_TMA = create_mock_module_entry('TMA')
        mock_entry_AS_Ano = create_mock_module_entry('AS_Ano')
        mock_modules_pkg.iterdir.return_value = [mock_entry_TMA, mock_entry_AS_Ano]

        # Configure mock_files to return our mock modules_pkg
        def mock_files_side_effect(package):
            if package == 'project_name.modules':
                return mock_modules_pkg
            elif package == 'project_name.modules.TMA':
                return create_mock_module_entry('TMA')
            elif package == 'project_name.modules.AS_Ano':
                return create_mock_module_entry('AS_Ano')
            else:
                raise ModuleNotFoundError(f"No module named '{package}'")

        mock_files.side_effect = mock_files_side_effect

        # Call the function
        result = get_sql_file_paths(['tma', 'as_ano'])

        # Assert the result matches expected output
        expected_output = {
            'tma': '/path/to/TMA/TMA.sql',
            'as_ano': '/path/to/AS_Ano/AS_Ano.sql',
        }
        assert result == expected_output

def test_module_package_not_found():
    with patch('importlib.resources.files', side_effect=ModuleNotFoundError("Package not found")):
        result = get_sql_file_paths(['test'])
        assert result == {}
        # Optionally, you can check for logged error messages

def test_module_sql_file_not_found():
    with patch('importlib.resources.files') as mock_files:
        # Set up mock modules package
        mock_modules_pkg = MagicMock()
        mock_entry_TMA = create_mock_module_entry('TMA', has_sql_file=False)
        mock_modules_pkg.iterdir.return_value = [mock_entry_TMA]

        # Configure mock_files to return our mock modules_pkg
        def mock_files_side_effect(package):
            if package == 'project_name.modules':
                return mock_modules_pkg
            elif package == 'project_name.modules.TMA':
                return create_mock_module_entry('TMA', has_sql_file=False)
            else:
                raise ModuleNotFoundError(f"No module named '{package}'")

        mock_files.side_effect = mock_files_side_effect

        # Call the function
        result = get_sql_file_paths(['tma'])

        # Assert an empty dictionary is returned
        assert result == {}
        # Optionally, you can check for logged warning messages
