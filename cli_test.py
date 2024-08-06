# File: test_cli_v1.py

import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
import joblib
from unittest.mock import patch, MagicMock

from cli_v1 import cli, MacatoAgent

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_macato_agent():
    with patch('cli_v1.MacatoAgent', autospec=True) as mock:
        yield mock.return_value

@pytest.mark.parametrize("command,expected_output", [
    (['update', 'fields'], "Fields updated successfully."),
    (['update', 'versions'], "Versions updated successfully."),
])
def test_update_commands(runner, mock_macato_agent, command, expected_output):
    result = runner.invoke(cli, command)
    assert result.exit_code == 0
    assert expected_output in result.output
    if 'fields' in command:
        mock_macato_agent.update_fields.assert_called_once()
    elif 'versions' in command:
        mock_macato_agent.update_docato_version.assert_called_once()

def test_update_output(runner, mock_macato_agent):
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp_file:
        joblib.dump({}, tmp_file.name)
        result = runner.invoke(cli, ['update', 'output', '--model', tmp_file.name])
        assert result.exit_code == 0
        assert f"Output updated successfully with model from {tmp_file.name}" in result.output
        mock_macato_agent.load_model.assert_called_once_with(Path(tmp_file.name))
        mock_macato_agent.update_output.assert_called_once()
    Path(tmp_file.name).unlink()  # Clean up the temporary file

def test_update_all_tables(runner, mock_macato_agent):
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp_file:
        joblib.dump({}, tmp_file.name)
        result = runner.invoke(cli, ['update', 'all_tables', '--model', tmp_file.name])
        assert result.exit_code == 0
        assert "Fields updated successfully." in result.output
        assert f"Output updated successfully with model from {tmp_file.name}" in result.output
        assert "Versions updated successfully." in result.output
        assert "All tables updated successfully." in result.output
        mock_macato_agent.update_fields.assert_called_once()
        mock_macato_agent.load_model.assert_called_once_with(Path(tmp_file.name))
        mock_macato_agent.update_output.assert_called_once()
        mock_macato_agent.update_docato_version.assert_called_once()
    Path(tmp_file.name).unlink()  # Clean up the temporary file

@pytest.mark.parametrize("command,error_message", [
    (['update', 'output', '--model', 'non_existent_file.pkl'], "Error updating output: "),
    (['update', 'all_tables', '--model', 'non_existent_file.pkl'], "Error updating all tables: "),
])
def test_file_not_found_errors(runner, mock_macato_agent, command, error_message):
    mock_macato_agent.load_model.side_effect = FileNotFoundError("File not found")
    result = runner.invoke(cli, command)
    assert result.exit_code != 0
    assert error_message in result.output

@pytest.mark.parametrize("command,method_to_mock,error_message", [
    (['update', 'fields'], 'update_fields', "Error updating fields: "),
    (['update', 'versions'], 'update_docato_version', "Error updating versions: "),
])
def test_update_exceptions(runner, mock_macato_agent, command, method_to_mock, error_message):
    getattr(mock_macato_agent, method_to_mock).side_effect = Exception("Test error")
    result = runner.invoke(cli, command)
    assert result.exit_code != 0
    assert error_message in result.output

# Instructions to run the tests:
# 1. Save this file as test_cli_v1.py in the same directory as your cli_v1.py file.
# 2. Open a terminal or command prompt.
# 3. Navigate to the directory containing test_cli_v1.py and cli_v1.py.
# 4. Run the command: pytest test_cli_v1.py
# 5. Pytest will discover and run all the test functions, displaying the results in the terminal.