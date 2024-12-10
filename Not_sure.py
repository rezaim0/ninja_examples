import pytest
from unittest.mock import MagicMock, patch
from typing import List, Dict
from pathlib import Path
from loguru import logger

from my_package.shared.util import get_sql_file_paths

@pytest.fixture
def mock_resources_files(mocker):
    """Fixture to mock importlib.resources.files so we can control package contents."""
    return mocker.patch("my_package.shared.util.files")

def create_mock_module_dir(module_name: str, has_sql_file: bool = True, file_extension: str = ".sql") -> MagicMock:
    """
    Create a mock directory entry representing a module directory with optional SQL file.

    If has_sql_file=True, a SQL file named {module_name}{file_extension} is considered present.
    Otherwise, no matching file is found.

    Only files named exactly {module_name}.sql or {module_name}.SQL are considered valid matches.
    """
    mock_entry = MagicMock()
    mock_entry.name = module_name
    mock_entry.is_dir.return_value = True

    mock_sql_file = MagicMock()
    if has_sql_file:
        mock_sql_file.is_file.return_value = True
        mock_sql_file.resolve.return_value = Path(f'/path/to/{module_name}/{module_name}{file_extension}')
    else:
        mock_sql_file.is_file.return_value = False

    def truediv_side_effect(x):
        # Return the mock_sql_file if the requested file matches the module and extension
        if has_sql_file:
            if (x == f"{module_name}.sql" and file_extension == ".sql") or \
               (x == f"{module_name}.SQL" and file_extension == ".SQL"):
                return mock_sql_file
        # Otherwise, return a mock non-file
        non_file_mock = MagicMock()
        non_file_mock.is_file.return_value = False
        return non_file_mock

    mock_entry.__truediv__.side_effect = truediv_side_effect
    return mock_entry

@pytest.mark.parametrize("input_modules, expected_output, expected_warnings", [
    # All modules found with .sql files
    (
        ['tma', 'as_ano'], 
        {'tma': '/path/to/TMA/TMA.sql', 'as_ano': '/path/to/AS_ano/AS_ano.sql'},
        []
    ),
    # Partial success - one module found, one not found
    (
        ['tma', 'unknown'], 
        {'tma': '/path/to/TMA/TMA.sql'},
        ["Module not found: unknown"]
    ),
    # No modules found at all
    (
        ['unknown'], 
        {},
        ["Module not found: unknown"]
    ),
    # Case-insensitive matching
    # If actual dirs are 'TMA' and 'AS_ano', requesting 'TMA', 'As_Ano' should succeed
    (
        ['TMA', 'As_Ano'], 
        {'TMA': '/path/to/TMA/TMA.sql', 'As_Ano': '/path/to/AS_ano/AS_ano.sql'},
        []
    )
])
def test_get_sql_file_paths_scenarios(mock_resources_files, caplog, input_modules: List[str], expected_output: Dict[str, str], expected_warnings: List[str]):
    package_base = 'project_name.modules'

    # Setup a directory with 'TMA' and 'AS_ano', both with .sql files
    mock_modules_dir = MagicMock()
    mock_modules_dir.iterdir.return_value = [
        create_mock_module_dir("TMA", True, ".sql"),
        create_mock_module_dir("AS_ano", True, ".sql")
    ]

    def files_side_effect(arg):
        if arg == package_base:
            return mock_modules_dir
        # If asked for a sub-package, return a dir with the respective file structure
        if arg == f"{package_base}.TMA":
            return create_mock_module_dir("TMA", True, ".sql")
        if arg == f"{package_base}.AS_ano":
            return create_mock_module_dir("AS_ano", True, ".sql")
        raise ModuleNotFoundError("Package not found.")

    mock_resources_files.side_effect = files_side_effect

    with caplog.at_level("WARNING"):
        result = get_sql_file_paths(input_modules)

    assert result == expected_output

    # Check that expected warnings appear in logs
    for wmsg in expected_warnings:
        assert wmsg in caplog.text

@pytest.mark.parametrize("invalid_input", [None, 123, [1,2,3], ['tma', 123], ['tma', None]])
def test_get_sql_file_paths_invalid_inputs(invalid_input):
    # Expect TypeError for invalid inputs
    with pytest.raises(TypeError):
        get_sql_file_paths(invalid_input)

def test_get_sql_file_paths_no_sql_files_found(mock_resources_files, caplog):
    package_base = 'project_name.modules'

    # Directory TMA exists but has no sql file
    mock_modules_dir = MagicMock()
    mock_modules_dir.iterdir.return_value = [
        create_mock_module_dir("TMA", has_sql_file=False)
    ]

    def files_side_effect(arg):
        if arg == package_base:
            return mock_modules_dir
        if arg == f"{package_base}.TMA":
            return create_mock_module_dir("TMA", has_sql_file=False)
        raise ModuleNotFoundError("Package not found.")

    mock_resources_files.side_effect = files_side_effect

    with caplog.at_level("WARNING"):
        result = get_sql_file_paths(['tma'])
    assert result == {}
    # We expect a warning that says no SQL files found for that module
    assert "No SQL files found for modules: ['tma']" in caplog.text

def test_get_sql_file_paths_package_not_found(mock_resources_files):
    # If the base package does not exist, we raise ModuleNotFoundError
    mock_resources_files.side_effect = ModuleNotFoundError("Package 'project_name.modules' not found.")

    with pytest.raises(ModuleNotFoundError, match="Package 'project_name.modules' not found."):
        get_sql_file_paths(['tma'])

def test_get_sql_file_paths_no_modules_at_all(mock_resources_files, caplog):
    package_base = 'project_name.modules'
    mock_modules_dir = MagicMock()
    # No directories at all
    mock_modules_dir.iterdir.return_value = []

    def files_side_effect(arg):
        if arg == package_base:
            return mock_modules_dir
        raise ModuleNotFoundError("Package not found.")

    mock_resources_files.side_effect = files_side_effect

    with caplog.at_level("WARNING"):
        # Request modules that don't exist since none exist at all
        result = get_sql_file_paths(['tma', 'as_ano'])
    assert result == {}
    # Both modules should be logged as not found
    assert "Module not found: tma" in caplog.text
    assert "Module not found: as_ano" in caplog.text

def test_get_sql_file_paths_with_sql_extension_variant(mock_resources_files, caplog):
    package_base = 'project_name.modules'

    # One module with a .sql file, another with a .SQL file
    mock_modules_dir = MagicMock()
    mock_modules_dir.iterdir.return_value = [
        create_mock_module_dir("TMA", has_sql_file=True, file_extension=".sql"),
        create_mock_module_dir("MOD2", has_sql_file=True, file_extension=".SQL")
    ]

    def files_side_effect(arg):
        if arg == package_base:
            return mock_modules_dir
        if arg == f"{package_base}.TMA":
            return create_mock_module_dir("TMA", True, ".sql")
        if arg == f"{package_base}.MOD2":
            return create_mock_module_dir("MOD2", True, ".SQL")
        raise ModuleNotFoundError("Package not found.")

    mock_resources_files.side_effect = files_side_effect

    with caplog.at_level("WARNING"):
        result = get_sql_file_paths(['tma', 'mod2', 'unknown'])

    # TMA and MOD2 should be found with their respective files
    assert result == {
        'tma': '/path/to/TMA/TMA.sql',
        'mod2': '/path/to/MOD2/MOD2.SQL'
    }
    # 'unknown' should be logged as not found
    assert "Module not found: unknown" in caplog.text