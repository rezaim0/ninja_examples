from __future__ import annotations

import pytest
from io import StringIO
from pathlib import Path
from typing import List
from unittest.mock import MagicMock
from click.testing import CliRunner
from loguru import logger
from pytest_mock import MockerFixture

from my_package.cli.extract_table import extract_tables

@pytest.fixture
def custom_caplog() -> StringIO:
    """A fixture to capture log messages produced by the logger."""
    log_stream = StringIO()
    handler_id = logger.add(log_stream, format="{level} {message}")
    yield log_stream
    logger.remove(handler_id)

@pytest.mark.parametrize(
    "modules_arg,sql_file_paths_return,expected_tables,expected_logs",
    [
        # Single module, no duplicates
        (
            ["mod1"],
            {"mod1": "/path/to/mod1.sql"},
            ["tableA", "tableB"],
            ["INFO Fetching SQL files for modules: ['mod1']", "INFO Source tables have been found."]
        ),
        # Multiple modules, including duplicates
        (
            ["mod1", "mod1", "mod2", "mod2"],  # duplicates present
            {"mod1": "/path/to/mod1.sql", "mod2": "/path/to/mod2.sql"},
            ["tableA", "tableB"],
            [
                "INFO Fetching SQL files for modules: ['mod1', 'mod1', 'mod2', 'mod2']",
                "INFO Source tables have been found."
            ]
        ),
    ],
    ids=["single_module", "duplicates_present"]
)
def test_extract_tables_flib_modules_success(
    modules_arg: List[str],
    sql_file_paths_return: dict,
    expected_tables: List[str],
    expected_logs: List[str],
    custom_caplog: StringIO,
    mocker: MockerFixture
) -> None:
    """Test successful scenarios when using --flib-modules, including duplicates.

    Args:
        modules_arg (List[str]): The modules passed to the CLI.
        sql_file_paths_return (dict): The return value for get_sql_file_paths.
        expected_tables (List[str]): The tables that extract_source_tables will return.
        expected_logs (List[str]): The expected log messages.
        custom_caplog (StringIO): Captures the log output.
        mocker (MockerFixture): Allows mocking dependencies.
    """
    mocker.patch("my_package.cli.extract_table.get_sql_file_paths", return_value=sql_file_paths_return)
    mocker.patch("my_package.cli.extract_table.extract_source_tables", return_value=expected_tables)

    runner = CliRunner()
    args = ["--flib-modules", ",".join(modules_arg)]
    result = runner.invoke(extract_tables, args)
    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"

    logs = custom_caplog.getvalue()
    for log_msg in expected_logs:
        assert log_msg in logs, f"Expected '{log_msg}' in logs, got: {logs}"

    # Check output
    expected_output = "".join(f"    - {table}\n" for table in expected_tables)
    assert result.output == expected_output, f"Expected output '{expected_output}', got '{result.output}'"


@pytest.mark.parametrize(
    "sql_filename,tables,expected_logs",
    [
        # .sql extension
        (
            "myquery.sql",
            ["tableC"],
            ["INFO Source tables have been found."]
        ),
        # .SQL extension
        (
            "myquery.SQL",
            ["tableD", "tableE"],
            ["INFO Source tables have been found."]
        ),
    ],
    ids=["lowercase_sql_extension", "uppercase_SQL_extension"]
)
def test_extract_tables_sql_file_success(
    sql_filename: str,
    tables: List[str],
    expected_logs: List[str],
    custom_caplog: StringIO,
    mocker: MockerFixture
) -> None:
    """Test successful scenarios when providing a --sql-file directly, covering both .sql and .SQL files.

    Args:
        sql_filename (str): The SQL file name (with extension) to pass as argument.
        tables (List[str]): The list of tables returned by extract_source_tables.
        expected_logs (List[str]): The expected log messages.
        custom_caplog (StringIO): Captures the log output.
        mocker (MockerFixture): Allows mocking dependencies.
    """
    mocker.patch("my_package.cli.extract_table.extract_source_tables", return_value=tables)

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--sql-file", sql_filename])
    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"

    logs = custom_caplog.getvalue()
    for log_msg in expected_logs:
        assert log_msg in logs, f"Expected '{log_msg}' in logs, got: {logs}"

    # Check output
    expected_output = "".join(f"    - {table}\n" for table in tables)
    assert result.output == expected_output, f"Expected output '{expected_output}', got '{result.output}'"