import pytest
from unittest.mock import MagicMock
from typing import Any, Dict
from pathlib import Path
from my_package.shared.util import get_sql_file_paths


@pytest.fixture
def mock_resources_files(mocker: Any) -> MagicMock:
    """Fixture to mock importlib.resources.files.

    Args:
        mocker (Any): pytest-mock fixture for mocking.

    Returns:
        MagicMock: The mocked resources.files function.
    """
    return mocker.patch('my_package.shared.util.resources.files')


@pytest.fixture
def mock_logger(mocker: Any) -> Dict[str, MagicMock]:
    """Fixture to mock logger methods.

    Args:
        mocker (Any): pytest-mock fixture for mocking.

    Returns:
        Dict[str, MagicMock]: A dictionary of mocked logger methods.
    """
    return {
        'warning': mocker.patch('my_package.shared.util.logger.warning'),
        'error': mocker.patch('my_package.shared.util.logger.error'),
    }


@pytest.fixture
def mock_modules_pkg(mocker: Any) -> MagicMock:
    """Fixture to create the mock modules package.

    Args:
        mocker (Any): pytest-mock fixture for mocking.

    Returns:
        MagicMock: The mocked modules package.
    """
    return MagicMock()


@pytest.fixture
def create_entry(mocker: Any):
    """Fixture to create mock directory entries.

    Args:
        mocker (Any): pytest-mock fixture for mocking.

    Returns:
        Callable: A function to create a mock directory entry.
    """
    def _create_entry(name: str, has_sql_file: bool) -> MagicMock:
        """Create a mock directory entry.

        Args:
            name (str): The name of the module.
            has_sql_file (bool): Whether the SQL file exists.

        Returns:
            MagicMock: The mocked directory entry.
        """
        entry = MagicMock(spec=Path)
        entry.is_dir.return_value = True
        entry.name = name

        # Mock the SQL file path and its existence
        sql_file = MagicMock(spec=Path)
        sql_file.is_file.return_value = has_sql_file
        sql_file.resolve.return_value = Path(f"/fake/path/{name}/{name}.sql")

        # Simulate the / operator (path joining)
        def truediv_mock(other: str) -> MagicMock:
            if other == f"{name}.sql":
                return sql_file
            else:
                other_path = MagicMock(spec=Path)
                return other_path
        entry.__truediv__.side_effect = truediv_mock
        return entry
    return _create_entry


def test_get_sql_file_paths(
    mock_resources_files: MagicMock,
    mock_logger: Dict[str, MagicMock],
    mock_modules_pkg: MagicMock,
    create_entry: Any
) -> None:
    """Test the get_sql_file_paths function with various module names.

    Args:
        mock_resources_files (MagicMock): Mocked resources.files function.
        mock_logger (Dict[str, MagicMock]): Mocked logger methods.
        mock_modules_pkg (MagicMock): Mocked modules package.
        create_entry (Callable): Function to create mock directory entries.
    """
    # Mock the resources.files function to return the mocked modules package
    mock_resources_files.return_value = mock_modules_pkg

    # Create mock entries for modules
    entry_a = create_entry('ModuleA', True)   # Module with SQL file
    entry_b = create_entry('ModuleB', True)   # Module with SQL file
    entry_c = create_entry('ModuleC', False)  # Module without SQL file

    # Mock the iterdir method to return our mock entries
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
            if actual_mod_name == 'ModuleD':
                # Simulate ModuleNotFoundError for ModuleD
                raise ModuleNotFoundError(f"No module named '{package_name}'")
            mod_pkg = MagicMock()
            resource_name = f"{actual_mod_name}.sql"
            sql_file = MagicMock(spec=Path)

            if actual_mod_name in ['ModuleA', 'ModuleB']:
                # Modules with SQL files
                sql_file.is_file.return_value = True
                sql_file.resolve.return_value = Path(f"/fake/path/{actual_mod_name}/{resource_name}")
            else:
                # Modules without SQL files
                sql_file.is_file.return_value = False

            def truediv_mock(other: str) -> MagicMock:
                if other == resource_name:
                    return sql_file
                else:
                    other_path = MagicMock(spec=Path)
                    return other_path

            mod_pkg.__truediv__.side_effect = truediv_mock
            return mod_pkg
        else:
            raise ModuleNotFoundError(f"No module named '{package_name}'")

    # Set the side effect for resources.files mock
    mock_resources_files.side_effect = mock_files_side_effect

    # Test the function with various module names, including edge cases
    test_modules = ['ModuleA', 'moduleb', 'modulec', 'ModuleD', '', 'Mod@uleE']
    result = get_sql_file_paths(test_modules)

    expected_result = {
        'ModuleA': str(Path('/fake/path/ModuleA/ModuleA.sql')),
        'moduleb': str(Path('/fake/path/ModuleB/ModuleB.sql')),
    }

    assert result == expected_result

    # Verify that warnings and errors were logged appropriately
    mock_logger['warning'].assert_any_call("SQL file not found for module: ModuleC")
    mock_logger['warning'].assert_any_call("Module not found for name: ModuleD")
    mock_logger['warning'].assert_any_call("Module not found for name: ")
    mock_logger['warning'].assert_any_call("Module not found for name: Mod@uleE")
    assert mock_logger['warning'].call_count == 4

    # Ensure that errors were logged for exceptions
    mock_logger['error'].assert_any_call("Module package not found: project_name.modules.ModuleD")
    assert mock_logger['error'].call_count == 1
