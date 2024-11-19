import sys
from pathlib import Path
from typing import Any, List, Dict
import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock
from my_package.cli.extract_tables import extract_tables
from io import StringIO
from loguru import logger

@pytest.fixture
def runner() -> CliRunner:
    """Fixture to create a Click CliRunner instance."""
    return CliRunner()

@pytest.fixture
def loguru_caplog():
    """Fixture to capture Loguru logs."""
    log_stream = StringIO()
    handler_id = logger.add(log_stream, format="{message}")
    yield log_stream
    logger.remove(handler_id)

@pytest.mark.parametrize("modules, sql_file_paths, expected_tables, expected_warnings, expected_exit_code", [
    (
        ['module1', 'module2'],
        {'module1': '/path/to/module1.sql', 'module2': '/path/to/module2.sql'},
        ['table1', 'table2'],
        [],
        0
    ),
    (
        ['module1', 'module1'],  # Duplicate modules
        {'module1': '/path/to/module1.sql'},
        ['table1'],
        ["Duplicate module detected and ignored: module1"],
        0
    ),
    (
        ['module1', 'module3'],  # Module3 not found
        {'module1': '/path/to/module1.sql'},
        ['table1'],
        ["Modules not found: ['module3']"],
        0
    ),
    (
        [''],  # Empty module name
        {},
        [],
        ["Module not found for name: "],
        1
    ),
    (
        ['module@'],  # Module with invalid character
        {},
        [],
        ["Modules not found: ['module@']"],
        1
    ),
])
def test_extract_tables_with_flib_modules(
    mocker: Any,
    runner: CliRunner,
    modules: List[str],
    sql_file_paths: Dict[str, str],
    expected_tables: List[str],
    expected_warnings: List[str],
    expected_exit_code: int,
    loguru_caplog
) -> None:
    """Test the extract_tables command with flib_modules provided.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        modules (List[str]): List of modules to test.
        sql_file_paths (Dict[str, str]): Mocked return value of get_sql_file_paths.
        expected_tables (List[str]): Expected list of extracted tables.
        expected_warnings (List[str]): Expected warning messages.
        expected_exit_code (int): Expected exit code of the command.
        loguru_caplog: Fixture to capture Loguru logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.get_sql_file_paths',
        return_value=sql_file_paths
    )
    mocker.patch(
        'my_package.cli.extract_tables.extract_source_tables',
        return_value=expected_tables
    )

    args = []
    for module in modules:
        args.extend(['--flib-modules', module])

    result = runner.invoke(extract_tables, args)

    assert result.exit_code == expected_exit_code

    log_output = loguru_caplog.getvalue()

    for warning in expected_warnings:
        assert warning in log_output

    if expected_tables:
        for table in expected_tables:
            assert f"    - {table}" in result.output

@pytest.mark.parametrize("sql_files, exception_message", [
    (['nonexistent.sql'], "File not found"),
    (['invalid.sql'], "Invalid SQL file"),
])
def test_extract_tables_with_invalid_sql_files(
    mocker: Any,
    runner: CliRunner,
    sql_files: List[str],
    exception_message: str,
    loguru_caplog
) -> None:
    """Test the extract_tables command with invalid SQL files.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        sql_files (List[str]): List of SQL files to test.
        exception_message (str): Exception message to simulate.
        loguru_caplog: Fixture to capture Loguru logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.extract_source_tables',
        side_effect=Exception(exception_message)
    )

    args = []
    for sql_file in sql_files:
        args.extend(['--sql-file', sql_file])

    result = runner.invoke(extract_tables, args)

    assert result.exit_code == 1
    log_output = loguru_caplog.getvalue()
    assert f"An error occurred while extracting source tables: {exception_message}" in log_output

def test_extract_tables_no_sql_files_found(mocker: Any, runner: CliRunner, loguru_caplog) -> None:
    """Test the extract_tables command when no SQL files are found for the specified modules.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        loguru_caplog: Fixture to capture Loguru logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.get_sql_file_paths',
        return_value={}
    )

    args = ['--flib-modules', 'module1']

    result = runner.invoke(extract_tables, args)
    assert result.exit_code == 1
    log_output = loguru_caplog.getvalue()
    assert "Modules not found: ['module1']" in log_output
    assert "No SQL files found for the specified modules." in log_output

def test_extract_tables_no_tables_found(mocker: Any, runner: CliRunner, loguru_caplog) -> None:
    """Test the extract_tables command when no source tables are found in the SQL files.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        loguru_caplog: Fixture to capture Loguru logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.extract_source_tables',
        return_value=[]
    )

    sql_files = ['file1.sql']
    args = []
    for sql_file in sql_files:
        args.extend(['--sql-file', sql_file])

    result = runner.invoke(extract_tables, args)
    assert result.exit_code == 1
    log_output = loguru_caplog.getvalue()
    assert f"No source tables were found in {[Path(f) for f in sql_files]}" in log_output

def test_extract_tables_with_invalid_module_name(mocker: Any, runner: CliRunner, loguru_caplog) -> None:
    """Test the extract_tables command with invalid module names.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        loguru_caplog: Fixture to capture Loguru logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.get_sql_file_paths',
        return_value={}
    )

    args = ['--flib-modules', 'invalid/module']

    result = runner.invoke(extract_tables, args)
    assert result.exit_code == 1
    log_output = loguru_caplog.getvalue()
    assert "Modules not found: ['invalid/module']" in log_output
    assert "No SQL files found for the specified modules." in log_output

def test_extract_tables_with_mixed_inputs(mocker: Any, runner: CliRunner, loguru_caplog) -> None:
    """Test the extract_tables command with both SQL files and flib_modules provided.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        loguru_caplog: Fixture to capture Loguru logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.get_sql_file_paths',
        return_value={'module1': '/path/to/module1.sql'}
    )
    mocker.patch(
        'my_package.cli.extract_tables.extract_source_tables',
        return_value=['table1', 'table2']
    )

    args = ['--sql-file', 'file1.sql', '--flib-modules', 'module1']

    result = runner.invoke(extract_tables, args)
    assert result.exit_code == 0
    log_output = loguru_caplog.getvalue()
    assert "Source tables have been found." in log_output
    for table in ['table1', 'table2']:
        assert f"    - {table}" in result.output
