@pytest.mark.parametrize(
    "extract_return, expected_exit, expected_log",
    [
        ([], 1, "WARNING No source tables were found in ['myquery.sql']"),
        (FileNotFoundError("File missing.sql not found."), 1, "ERROR SQL file not found: File missing.sql not found."),
        (PermissionError("No permission to read secret.sql"), 1, "ERROR Permission error while reading SQL files: No permission to read secret.sql"),
        (Exception("Some unexpected error"), 1, "ERROR An error occurred while extracting source tables: Some unexpected error"),
    ],
    ids=[
        "no_tables_found",
        "file_not_found",
        "permission_error",
        "unexpected_error",
    ]
)
def test_extract_tables_sql_file_errors(
    extract_return: Union[List[str], Exception],
    expected_exit: int,
    expected_log: str,
    custom_caplog: StringIO,
    mocker: MockerFixture,
) -> None:
    """Test scenarios where an SQL file is provided, but extracting tables fails."""
    extract_source_tables_mock = mocker.patch("my_package.cli.extract_table.extract_source_tables")

    if isinstance(extract_return, list):
        # Normal return scenario
        extract_source_tables_mock.return_value = extract_return
    else:
        # Exception scenario
        extract_source_tables_mock.side_effect = extract_return

    runner = CliRunner()
    result = runner.invoke(extract_tables, ["--sql-file", "myquery.sql"])
    
    assert result.exit_code == expected_exit
    logs = custom_caplog.getvalue()
    assert expected_log in logs, f"Expected '{expected_log}' in logs, got: {logs}"