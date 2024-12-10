import pytest
from unittest.mock import MagicMock
from io import StringIO
from click.testing import CliRunner
from loguru import logger

from my_package.cli.extract_table import extract_tables

@pytest.fixture
def custom_caplog():
    log_stream = StringIO()
    handler_id = logger.add(log_stream, format="{level} {message}")
    yield log_stream
    logger.remove(handler_id)

#
# Tests for Argument Validation
#
@pytest.mark.parametrize("args,expected_message", [
    (["--sql-file", "myquery.sql", "--flib-modules", "mod1"], "ERROR Please provide either SQL files or module names, but not both."),
    ([], "ERROR No SQL files or modules have been provided."),
])
def test_extract_tables_arg_validation(args, expected_message, custom_caplog, mocker):
    runner = CliRunner()
    result = runner.invoke(extract_tables, args)
    assert result.exit_code == 1
    assert expected_message in custom_caplog.getvalue()


#
# Tests for flib_modules with no SQL files returned
#
def test_extract_tables_no_sql_files_for_modules(custom_caplog, mocker):
    get_sql_file_paths_mock = mocker.patch("my_package.cli.extract_table.get_sql_file_paths")
    get_sql_file_paths_mock.return_value = {}

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--flib-modules", "mod1"])
    assert result.exit_code == 1
    logs = custom_caplog.getvalue()
    assert "INFO Fetching SQL files for modules: ['mod1']" in logs
    assert "ERROR No SQL files found for the specified modules." in logs


#
# Tests for ModuleNotFoundError from get_sql_file_paths
#
def test_extract_tables_module_not_found_error(custom_caplog, mocker):
    get_sql_file_paths_mock = mocker.patch("my_package.cli.extract_table.get_sql_file_paths")
    get_sql_file_paths_mock.side_effect = ModuleNotFoundError("Base package not found.")

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--flib-modules", "mod1"])
    assert result.exit_code == 1
    logs = custom_caplog.getvalue()
    assert "INFO Fetching SQL files for modules: ['mod1']" in logs
    assert "ERROR Failed to find project modules: Base package not found." in logs


#
# Tests for TypeError from get_sql_file_paths
#
def test_extract_tables_type_error(custom_caplog, mocker):
    get_sql_file_paths_mock = mocker.patch("my_package.cli.extract_table.get_sql_file_paths")
    get_sql_file_paths_mock.side_effect = TypeError("Invalid input for modules.")

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--flib-modules", "mod1"])
    assert result.exit_code == 1
    logs = custom_caplog.getvalue()
    assert "INFO Fetching SQL files for modules: ['mod1']" in logs
    assert "ERROR Invalid input for modules: Invalid input for modules." in logs


#
# Tests for unexpected Exception from get_sql_file_paths
#
def test_extract_tables_unexpected_error(custom_caplog, mocker):
    get_sql_file_paths_mock = mocker.patch("my_package.cli.extract_table.get_sql_file_paths")
    get_sql_file_paths_mock.side_effect = Exception("Unknown error")

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--flib-modules", "mod1"])
    assert result.exit_code == 1
    logs = custom_caplog.getvalue()
    assert "INFO Fetching SQL files for modules: ['mod1']" in logs
    assert "ERROR An unexpected error occurred while fetching SQL files: Unknown error" in logs


#
# Test successful scenario with flib-modules
#
def test_extract_tables_flib_modules_success(custom_caplog, mocker):
    mocker.patch("my_package.cli.extract_table.get_sql_file_paths", return_value={"mod1": "/path/to/mod1.sql"})
    mocker.patch("my_package.cli.extract_table.extract_source_tables", return_value=["tableA", "tableB"])

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--flib-modules", "mod1"])
    assert result.exit_code == 0
    logs = custom_caplog.getvalue()
    assert "INFO Fetching SQL files for modules: ['mod1']" in logs
    assert "INFO Source tables have been found." in logs
    assert result.output == "    - tableA\n    - tableB\n"


#
# Test successful scenario with sql-file directly
#
def test_extract_tables_sql_file_success(custom_caplog, mocker):
    mocker.patch("my_package.cli.extract_table.extract_source_tables", return_value=["tableC"])

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--sql-file", "myquery.sql"])
    assert result.exit_code == 0
    logs = custom_caplog.getvalue()
    assert "INFO Source tables have been found." in logs
    assert result.output == "    - tableC\n"


#
# No tables found scenario
#
def test_extract_tables_no_tables_found(custom_caplog, mocker):
    mocker.patch("my_package.cli.extract_table.extract_source_tables", return_value=[])

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--sql-file", "myquery.sql"])
    assert result.exit_code == 1
    logs = custom_caplog.getvalue()
    assert "WARNING No source tables were found in ['myquery.sql']" in logs


#
# FileNotFoundError scenario
#
def test_extract_tables_file_not_found_error(custom_caplog, mocker):
    mocker.patch("my_package.cli.extract_table.extract_source_tables", side_effect=FileNotFoundError("File missing.sql not found."))

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--sql-file", "missing.sql"])
    assert result.exit_code == 1
    logs = custom_caplog.getvalue()
    assert "ERROR SQL file not found: File missing.sql not found." in logs


#
# PermissionError scenario
#
def test_extract_tables_permission_error(custom_caplog, mocker):
    mocker.patch("my_package.cli.extract_table.extract_source_tables", side_effect=PermissionError("No permission to read secret.sql"))

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--sql-file", "secret.sql"])
    assert result.exit_code == 1
    logs = custom_caplog.getvalue()
    assert "ERROR Permission error while reading SQL files: No permission to read secret.sql" in logs


#
# Unexpected error scenario during table extraction
#
def test_extract_tables_unexpected_table_extraction_error(custom_caplog, mocker):
    mocker.patch("my_package.cli.extract_table.extract_source_tables", side_effect=Exception("Some unexpected error"))

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--sql-file", "broken.sql"])
    assert result.exit_code == 1
    logs = custom_caplog.getvalue()
    assert "ERROR An error occurred while extracting source tables: Some unexpected error" in logs