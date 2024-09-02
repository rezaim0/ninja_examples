import pytest
from click.testing import CliRunner
from pathlib import Path
from cli_v3 import cli  # Make sure to import from cli_v3 instead of cli_v2

# Existing fixtures and imports remain unchanged

def test_no_options_provided(runner: CliRunner, caplog) -> None:
    """
    Test the behavior when no update options are specified.
    """
    result = runner.invoke(cli, ['update-table'])
    captured_log = caplog.getvalue()
    assert result.exit_code == 0
    assert "No update option specified. Please use --fields, --versions, --output, or --all." in result.output
    assert "No update options provided." in captured_log

def test_invalid_model_path(runner: CliRunner, caplog) -> None:
    """
    Test error handling when an invalid model file path is provided.
    """
    result = runner.invoke(cli, ['update-table', '--output', '--model', 'invalid_path.pkl'])
    assert result.exit_code == 1
    assert "Error: Invalid value for '--model'" in result.output

def test_exception_handling(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    """
    Test exception handling in the CLI.
    """
    mock_macato_agent.update_fields.side_effect = Exception("Test exception")
    result = runner.invoke(cli, ['update-table', '--fields'])
    assert result.exit_code == 1
    assert "Error updating tables: Test exception" in result.output

def test_log_output_format(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    """
    Test the format of log outputs for each operation.
    """
    result = runner.invoke(cli, ['update-table', '--fields', '--versions'])
    captured_log = caplog.getvalue()
    assert "Fields table updated successfully." in captured_log
    assert "Versions table updated successfully." in captured_log

def test_cli_help_output(runner: CliRunner) -> None:
    """
    Test the help text output of the CLI.
    """
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "Macato CLI for updating various tables." in result.output
    assert "--fields" in result.output
    assert "--versions" in result.output
    assert "--output" in result.output
    assert "--model" in result.output
    assert "--all" in result.output

def test_invalid_option_combination(runner: CliRunner, caplog) -> None:
    """
    Test for invalid combinations of options (e.g., using --all with individual flags).
    """
    result = runner.invoke(cli, ['update-table', '--all', '--fields', '--model', 'test.pkl'])
    assert result.exit_code == 0  # Keeping the existing behavior
    assert "Fields table updated successfully." in caplog.getvalue()
    assert "Versions table updated successfully." in caplog.getvalue()
    assert "Output table updated successfully." in caplog.getvalue()

def test_model_loading(runner: CliRunner, mock_macato_agent: Any, temp_model_file: str, caplog) -> None:
    """
    Test that the model is only loaded when necessary.
    """
    # Test without output update (should not load model)
    result = runner.invoke(cli, ['update-table', '--fields', '--versions'])
    assert result.exit_code == 0
    mock_macato_agent.load_model.assert_not_called()

    # Test with output update (should load model)
    result = runner.invoke(cli, ['update-table', '--output', '--model', temp_model_file])
    assert result.exit_code == 0
    mock_macato_agent.load_model.assert_called_once_with(Path(temp_model_file))

# Update the existing error handling tests

def test_update_all_without_model(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    """
    Test the update-table command with --all option but without --model.
    """
    result = runner.invoke(cli, ['update-table', '--all'])
    captured_log = caplog.getvalue()

    assert result.exit_code == 1  # Changed from 0 to 1
    assert "Error: --model is required when using --all" in captured_log
    mock_macato_agent.update_fields.assert_not_called()
    mock_macato_agent.update_docato_version.assert_not_called()
    mock_macato_agent.update_output.assert_not_called()

def test_update_output_without_model(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    """
    Test the update-table command with --output option but without --model.
    """
    result = runner.invoke(cli, ['update-table', '--output'])
    captured_log = caplog.getvalue()

    assert result.exit_code == 1  # Changed from 0 to 1
    assert "Error: --model is required when updating output" in captured_log
    mock_macato_agent.update_output.assert_not_called()