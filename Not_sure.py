import pytest
from unittest.mock import MagicMock
from util import find_sql_file_for_module

@pytest.fixture
def mock_resources_files(mocker):
    """Fixture to mock importlib.resources.files."""
    return mocker.patch("util.resources.files")


@pytest.mark.parametrize("file_exists_lower,file_exists_upper,expected", [
    # file_exists_lower, file_exists_upper, expected_result
    # If lowercase file exists, return its path
    (True, False, "/abs/path/my_package/modules/mod1/mod1.sql"),
    # If lowercase file doesn't exist, but uppercase does, return uppercase file path
    (False, True, "/abs/path/my_package/modules/mod2/mod2.SQL"),
    # If neither exists, return None
    (False, False, None),
])
def test_find_sql_file_for_module_variations(mock_resources_files, file_exists_lower, file_exists_upper, expected):
    # We will simulate a generic package and module name, and adjust the mock return values
    package = "my_package.modules.modX"
    mod_name = "modX"

    # Mock path objects
    mock_lower_path = MagicMock()
    mock_lower_path.is_file.return_value = file_exists_lower
    if file_exists_lower:
        mock_lower_path.resolve.return_value = "/abs/path/my_package/modules/modX/modX.sql"

    mock_upper_path = MagicMock()
    mock_upper_path.is_file.return_value = file_exists_upper
    if file_exists_upper:
        mock_upper_path.resolve.return_value = "/abs/path/my_package/modules/modX/modX.SQL"

    mock_dir = MagicMock()

    def mock_div(name):
        if name == "modX.sql":
            return mock_lower_path
        if name == "modX.SQL":
            return mock_upper_path

    mock_dir.__truediv__.side_effect = mock_div
    mock_resources_files.return_value = mock_dir

    # Act
    result = find_sql_file_for_module(package, mod_name)

    # Assert
    assert result == expected


def test_find_sql_file_for_module_package_not_found(mock_resources_files):
    package = "my_package.modules.modY"
    mod_name = "modY"
    # Simulate that calling resources.files(package) raises ModuleNotFoundError
    mock_resources_files.side_effect = ModuleNotFoundError("Package not found.")

    with pytest.raises(ModuleNotFoundError, match="Package not found."):
        find_sql_file_for_module(package, mod_name)


def test_find_sql_file_for_module_file_not_found(mock_resources_files):
    package = "my_package.modules.modZ"
    mod_name = "modZ"

    # Simulate that accessing files raises FileNotFoundError
    mock_dir = MagicMock()
    mock_dir.__truediv__.side_effect = FileNotFoundError("File not found.")
    mock_resources_files.return_value = mock_dir

    with pytest.raises(FileNotFoundError, match="File not found."):
        find_sql_file_for_module(package, mod_name)