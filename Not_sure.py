from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner
from loguru import logger
from pytest_mock import MockerFixture

from my_package.cli.extract_table import extract_tables


@pytest.fixture
def custom_caplog() -> StringIO:
    """A fixture to capture log messages produced by the logger.

    Yields:
        StringIO: An in-memory stream that captures logged messages.
    """
    log_stream = StringIO()
    handler_id = logger.add(log_stream, format="{level} {message}")
    yield log_stream
    logger.remove(handler_id)


@pytest.mark.parametrize(
    "args, expected_message",
    [
        (
            ["--sql-file", "myquery.sql", "--flib-modules", "mod1"],
            "ERROR Please provide either SQL files or module names, but not both.",
        ),
        (
            [],
            "ERROR No SQL files or modules have been provided.",
        ),
    ],
)
def test_extract_tables_arg_validation(
    args: List[str],
    expected_message: str,
    custom_caplog: StringIO,
    mocker: MockerFixture,
) -> None:
    """Test argument validation scenarios for the extract_tables CLI.

    Args:
        args (List[str]): Command-line arguments to simulate.
        expected_message (str): The expected error message in the logs.
        custom_caplog (StringIO): Captures the log output.
        mocker (MockerFixture): Allows mocking dependencies.
    """
    runner = CliRunner()
    result = runner.invoke(extract_tables, args)
    assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"
    assert expected_message in custom_caplog.getvalue(), (
        f"Log '{expected_message}' not found in logs: {custom_caplog.getvalue()}"
    )


@pytest.mark.parametrize(
    "mock_get_sql_paths, expected_logs",
    [
        # No SQL files found for modules scenario
        (
            {"return_value": {}},
            [
                "INFO Fetching SQL files for modules: ['mod1']",
                "ERROR No SQL files found for the specified modules.",
            ],
        ),
        # ModuleNotFoundError scenario
        (
            {"side_effect": ModuleNotFoundError("Base package not found.")},
            [
                "INFO Fetching SQL files for modules: ['mod1']",
                "ERROR Failed to find project modules: Base package not found.",
            ],
        ),
        # TypeError scenario
        (
            {"side_effect": TypeError("Invalid input for modules.")},
            [
                "INFO Fetching SQL files for modules: ['mod1']",
                "ERROR Invalid input for modules: Invalid input for modules.",
            ],
        ),
        # Unexpected Exception scenario
        (
            {"side_effect": Exception("Unknown error")},
            [
                "INFO Fetching SQL files for modules: ['mod1']",
                "ERROR An unexpected error occurred while fetching SQL files: Unknown error",
            ],
        ),
    ],
)
def test_extract_tables_modules_errors(
    mock_get_sql_paths: Dict[str, Union[Dict[str, str], Exception]],
    expected_logs: List[str],
    custom_caplog: StringIO,
    mocker: MockerFixture,
) -> None:
    """Test module-related failures when using --flib-modules.

    Covers:
    - No SQL files found
    - ModuleNotFoundError
    - TypeError
    - Unexpected Exception

    Args:
        mock_get_sql_paths (Dict[str, Union[Dict[str,str], Exception]]): Configuration for get_sql_file_paths mock.
        expected_logs (List[str]): Expected log messages.
        custom_caplog (StringIO): Captures the log output.
        mocker (MockerFixture): Allows mocking dependencies.
    """
    get_sql_file_paths_mock = mocker.patch("my_package.cli.extract_table.get_sql_file_paths")

    if "return_value" in mock_get_sql_paths:
        get_sql_file_paths_mock.return_value = mock_get_sql_paths["return_value"]
    if "side_effect" in mock_get_sql_paths:
        get_sql_file_paths_mock.side_effect = mock_get_sql_paths["side_effect"]

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--flib-modules", "mod1"])
    assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

    logs = custom_caplog.getvalue()
    for log_msg in expected_logs:
        assert log_msg in logs, f"Expected '{log_msg}' in logs, got: {logs}"


def test_extract_tables_flib_modules_success(
    custom_caplog: StringIO,
    mocker: MockerFixture,
) -> None:
    """Test a successful scenario when using --flib-modules.

    This scenario covers:
    - get_sql_file_paths returns a valid mapping
    - extract_source_tables returns a list of tables

    Args:
        custom_caplog (StringIO): Captures the log output.
        mocker (MockerFixture): Allows mocking dependencies.
    """
    mocker.patch("my_package.cli.extract_table.get_sql_file_paths", return_value={"mod1": "/path/to/mod1.sql"})
    mocker.patch("my_package.cli.extract_table.extract_source_tables", return_value=["tableA", "tableB"])

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--flib-modules", "mod1"])
    assert result.exit_code == 0
    logs = custom_caplog.getvalue()
    assert "INFO Fetching SQL files for modules: ['mod1']" in logs
    assert "INFO Source tables have been found." in logs
    assert result.output == "    - tableA\n    - tableB\n"


def test_extract_tables_sql_file_success(
    custom_caplog: StringIO,
    mocker: MockerFixture,
) -> None:
    """Test a successful scenario when providing a --sql-file directly.

    Args:
        custom_caplog (StringIO): Captures the log output.
        mocker (MockerFixture): Allows mocking dependencies.
    """
    mocker.patch("my_package.cli.extract_table.extract_source_tables", return_value=["tableC"])

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--sql-file", "myquery.sql"])
    assert result.exit_code == 0
    logs = custom_caplog.getvalue()
    assert "INFO Source tables have been found." in logs
    assert result.output == "    - tableC\n"


@pytest.mark.parametrize(
    "extract_return, expected_exit, expected_log",
    [
        ([], 1, "WARNING No source tables were found in ['myquery.sql']"),
        (pytest.raises(FileNotFoundError("File missing.sql not found.")), 1, "ERROR SQL file not found: File missing.sql not found."),
        (pytest.raises(PermissionError("No permission to read secret.sql")), 1, "ERROR Permission error while reading SQL files: No permission to read secret.sql"),
        (pytest.raises(Exception("Some unexpected error")), 1, "ERROR An error occurred while extracting source tables: Some unexpected error"),
    ],
    ids=[
        "no_tables_found",
        "file_not_found",
        "permission_error",
        "unexpected_error",
    ]
)
def test_extract_tables_sql_file_errors(
    extract_return: Union[List[str], pytest.raises],
    expected_exit: int,
    expected_log: str,
    custom_caplog: StringIO,
    mocker: MockerFixture,
) -> None:
    """Test scenarios where an SQL file is provided, but extracting tables fails.

    Covers:
    - No tables found
    - FileNotFoundError
    - PermissionError
    - Unexpected Exception

    Args:
        extract_return (Union[List[str], pytest.raises]): The return value or exception side effect for extract_source_tables.
        expected_exit (int): The expected exit code.
        expected_log (str): The expected log message.
        custom_caplog (StringIO): Captures the log output.
        mocker (MockerFixture): Allows mocking dependencies.
    """
    extract_source_tables_mock = mocker.patch("my_package.cli.extract_table.extract_source_tables")

    if isinstance(extract_return, list):
        # Normal return scenario
        extract_source_tables_mock.return_value = extract_return
    else:
        # Exception scenario
        with extract_return:
            extract_source_tables_mock.side_effect = extract_return._raises

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--sql-file", "myquery.sql"])
    assert result.exit_code == expected_exit
    logs = custom_caplog.getvalue()
    assert expected_log in logs, f"Expected '{expected_log}' in logs, got: {logs}"