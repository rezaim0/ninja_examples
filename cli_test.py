
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
    with patch('cli_v1.MacatoAgent') as mock:
        yield mock.return_value

def test_update_fields(runner, mock_macato_agent):
    result = runner.invoke(cli, ['update', 'fields'])
    assert result.exit_code == 0
    assert "Fields updated successfully." in result.output
    mock_macato_agent.update_fields.assert_called_once()

def test_update_output(runner, mock_macato_agent):
    with tempfile.NamedTemporaryFile(suffix='.pkl') as tmp_file:
        joblib.dump({}, tmp_file.name)
        result = runner.invoke(cli, ['update', 'output', '--model', tmp_file.name])
        assert result.exit_code == 0
        assert f"Output updated successfully with model from {tmp_file.name}" in result.output
        mock_macato_agent.load_model.assert_called_once_with(Path(tmp_file.name))
        mock_macato_agent.update_output.assert_called_once()

def test_update_versions(runner, mock_macato_agent):
    result = runner.invoke(cli, ['update', 'versions'])
    assert result.exit_code == 0
    assert "Versions updated successfully." in result.output
    mock_macato_agent.update_docato_version.assert_called_once()

def test_update_all_tables(runner, mock_macato_agent):
    with tempfile.NamedTemporaryFile(suffix='.pkl') as tmp_file:
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

def test_update_output_file_not_found(runner, mock_macato_agent):
    mock_macato_agent.load_model.side_effect = FileNotFoundError("File not found")
    result = runner.invoke(cli, ['update', 'output', '--model', 'non_existent_file.pkl'])
    assert result.exit_code != 0
    assert "Error updating output: File not found" in result.output

def test_update_all_tables_file_not_found(runner, mock_macato_agent):
    mock_macato_agent.load_model.side_effect = FileNotFoundError("File not found")
    result = runner.invoke(cli, ['update', 'all_tables', '--model', 'non_existent_file.pkl'])
    assert result.exit_code != 0
    assert "Error updating all tables: File not found" in result.output

def test_update_fields_exception(runner, mock_macato_agent):
    mock_macato_agent.update_fields.side_effect = Exception("Database error")
    result = runner.invoke(cli, ['update', 'fields'])
    assert result.exit_code != 0
    assert "Error updating fields: Database error" in result.output

def test_update_versions_exception(runner, mock_macato_agent):
    mock_macato_agent.update_docato_version.side_effect = Exception("Version update failed")
    result = runner.invoke(cli, ['update', 'versions'])
    assert result.exit_code != 0
    assert "Error updating versions: Version update failed" in result.output

