import pytest
from unittest.mock import MagicMock
from typing import Any, Dict, List
from my_package.shared.util import get_sql_file_paths


def test_get_sql_file_paths(mocker: Any) -> None:
    """Test the get_sql_file_paths function with various module names.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
    """
    # Mock the resources.files function
    mock_files = mocker.patch('my_package.shared.util.resources.files')

    # Mock the logger methods
    mock_logger_warning = mocker.patch('my_package.shared.util.logger.warning')
    mock_logger_error = mocker.patch('my_package.shared.util.logger.error')

    # Prepare the mock modules package and entries
    mock_modules_pkg = MagicMock()
    mock_files.return_value = mock_modules_pkg

    def create_entry(name: str, has_sql_file: bool) -> MagicMock:
        """Create a mock directory entry.

        Args:
            name (str): The name of the module.
            has_sql_file (bool): Whether the SQL file exists.

        Returns:
            MagicMock: The mocked directory entry.
        """
        entry = MagicMock()
        entry.is_dir.return_value = True
        entry.name = name

        # Mock the SQL file path and its existence
        sql_file = MagicMock()
        sql_file.is_file.return_value = has_sql_file

        def truediv_mock(other: str) -> MagicMock:
            if other == f"{name}.sql":
                return sql_file
            else:
                return MagicMock()

        entry.__truediv__.side_effect = truediv_mock
        return entry

    # Create mock entries
    entry_a = create_entry('ModuleA', True)
    entry_b = create_entry('ModuleB', True)
    entry_c = create_entry('ModuleC', False)  # No SQL file

    mock_modules_pkg.iterdir.return_value = [entry_a, entry_b, entry_c]

    def mock_files_side_effect(package_name: str) -> MagicMock:
        """Side effect function for resources.files mock.

        Args:
            package_name (str): The package name requested.

        Returns:
            MagicMock: The mocked package or raises an error.

        Raises:
            ModuleNotFoundError: If the package does not exist.
        """
        if package_name == 'project_name.modules':
            return mock_modules_pkg
        elif package_name.startswith('project_name.modules.'):
            actual_mod_name = package_name.split('.')[-1]
            mod_pkg = MagicMock()
            resource_name = f"{actual_mod_name}.sql"
            sql_file = MagicMock()

            if actual_mod_name in ['ModuleA', 'ModuleB']:
                sql_file.is_file.return_value = True
                sql_file.resolve.return_value = f"/fake/path/{actual_mod_name}/{resource_name}"
            else:
                sql_file.is_file.return_value = False

            def truediv_mock(other: str) -> MagicMock:
                if other == resource_name:
                    return sql_file
                else:
                    return MagicMock()

            mod_pkg.__truediv__.side_effect = truediv_mock
            return mod_pkg
        else:
            raise ModuleNotFoundError(f"No module named '{package_name}'")

    mock_files.side_effect = mock_files_side_effect

    # Test the function with various module names
    test_modules = ['ModuleA', 'moduleb', 'modulec', 'ModuleD']
    result = get_sql_file_paths(test_modules)

    expected_result = {
        'ModuleA': '/fake/path/ModuleA/ModuleA.sql',
        'moduleb': '/fake/path/ModuleB/ModuleB.sql',
    }

    assert result == expected_result

    # Verify that warnings were logged for missing modules or SQL files
    mock_logger_warning.assert_any_call("SQL file not found for module: ModuleC")
    mock_logger_warning.assert_any_call("Module not found for name: ModuleD")
    assert mock_logger_warning.call_count == 2

    # Ensure that no errors were logged
    mock_logger_error.assert_not_called()
