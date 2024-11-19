import sys
from pathlib import Path
from typing import Any, List, Dict
import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch
from my_package.cli.extract_tables import extract_tables

@pytest.fixture
def runner() -> CliRunner:
    """Fixture to create a Click CliRunner instance."""
    return CliRunner()

def test_extract_tables_no_arguments(mocker: Any, runner: CliRunner, caplog: Any) -> None:
    """Test the extract_tables command with no arguments provided.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        caplog (Any): Pytest fixture to capture logs.
    """
    with mocker.patch('sys.exit') as mock_sys_exit:
        result = runner.invoke(extract_tables, [])
        assert result.exit_code == 1
        assert "No SQL files or modules have been provided." in caplog.text
        mock_sys_exit.assert_called_once_with(1)

@pytest.mark.parametrize("sql_files, expected_tables", [
    (['file1.sql'], ['table1', 'table2']),
    (['file2.sql', 'file3.sql'], ['table3', 'table4']),
])
def test_extract_tables_with_sql_files(
    mocker: Any,
    runner: CliRunner,
    sql_files: List[str],
    expected_tables: List[str],
    caplog: Any
) -> None:
    """Test the extract_tables command with SQL files provided.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        sql_files (List[str]): List of SQL files to test.
        expected_tables (List[str]): Expected list of extracted tables.
        caplog (Any): Pytest fixture to capture logs.
    """
    # Mock extract_source_tables to return expected_tables
    mocker.patch(
        'my_package.cli.extract_tables.extract_source_tables',
        return_value=expected_tables
    )
    args = []
    for sql_file in sql_files:
        args.extend(['--sql-file', sql_file])

    result = runner.invoke(extract_tables, args)

    assert result.exit_code == 0
    assert "Source tables have been found." in caplog.text
    for table in expected_tables:
        assert f"    - {table}" in result.output

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
    caplog: Any
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
        caplog (Any): Pytest fixture to capture logs.
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

    with mocker.patch('sys.exit') as mock_sys_exit:
        result = runner.invoke(extract_tables, args)

        assert result.exit_code == expected_exit_code

        for warning in expected_warnings:
            assert warning in caplog.text

        if expected_tables:
            for table in expected_tables:
                assert f"    - {table}" in result.output

        if expected_exit_code != 0:
            mock_sys_exit.assert_called_once_with(expected_exit_code)
        else:
            mock_sys_exit.assert_not_called()

@pytest.mark.parametrize("sql_files, exception_message", [
    (['nonexistent.sql'], "File not found"),
    (['invalid.sql'], "Invalid SQL file"),
])
def test_extract_tables_with_invalid_sql_files(
    mocker: Any,
    runner: CliRunner,
    sql_files: List[str],
    exception_message: str,
    caplog: Any
) -> None:
    """Test the extract_tables command with invalid SQL files.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        sql_files (List[str]): List of SQL files to test.
        exception_message (str): Exception message to simulate.
        caplog (Any): Pytest fixture to capture logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.extract_source_tables',
        side_effect=Exception(exception_message)
    )

    args = []
    for sql_file in sql_files:
        args.extend(['--sql-file', sql_file])

    with mocker.patch('sys.exit') as mock_sys_exit:
        result = runner.invoke(extract_tables, args)

        assert result.exit_code == 1
        assert f"An error occurred while extracting source tables: {exception_message}" in caplog.text
        mock_sys_exit.assert_called_once_with(1)

def test_extract_tables_no_sql_files_found(mocker: Any, runner: CliRunner, caplog: Any) -> None:
    """Test the extract_tables command when no SQL files are found for the specified modules.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        caplog (Any): Pytest fixture to capture logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.get_sql_file_paths',
        return_value={}
    )

    args = ['--flib-modules', 'module1']

    with mocker.patch('sys.exit') as mock_sys_exit:
        result = runner.invoke(extract_tables, args)
        assert result.exit_code == 1
        assert "Modules not found: ['module1']" in caplog.text
        assert "No SQL files found for the specified modules." in caplog.text
        mock_sys_exit.assert_called_once_with(1)

def test_extract_tables_no_tables_found(mocker: Any, runner: CliRunner, caplog: Any) -> None:
    """Test the extract_tables command when no source tables are found in the SQL files.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        caplog (Any): Pytest fixture to capture logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.extract_source_tables',
        return_value=[]
    )

    sql_files = ['file1.sql']
    args = []
    for sql_file in sql_files:
        args.extend(['--sql-file', sql_file])

    with mocker.patch('sys.exit') as mock_sys_exit:
        result = runner.invoke(extract_tables, args)
        assert result.exit_code == 1
        assert f"No source tables were found in {[Path(f) for f in sql_files]}" in caplog.text
        mock_sys_exit.assert_called_once_with(1)

def test_extract_tables_with_invalid_module_name(mocker: Any, runner: CliRunner, caplog: Any) -> None:
    """Test the extract_tables command with invalid module names.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        caplog (Any): Pytest fixture to capture logs.
    """
    mocker.patch(
        'my_package.cli.extract_tables.get_sql_file_paths',
        return_value={}
    )

    args = ['--flib-modules', 'invalid/module']

    with mocker.patch('sys.exit') as mock_sys_exit:
        result = runner.invoke(extract_tables, args)
        assert result.exit_code == 1
        assert "Modules not found: ['invalid/module']" in caplog.text
        assert "No SQL files found for the specified modules." in caplog.text
        mock_sys_exit.assert_called_once_with(1)

def test_extract_tables_with_mixed_inputs(mocker: Any, runner: CliRunner, caplog: Any) -> None:
    """Test the extract_tables command with both SQL files and flib_modules provided.

    Args:
        mocker (Any): pytest-mock fixture for mocking.
        runner (CliRunner): Click test runner fixture.
        caplog (Any): Pytest fixture to capture logs.
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
    assert "Source tables have been found." in caplog.text
    for table in ['table1', 'table2']:
        assert f"    - {table}" in result.output

