import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
import joblib

from cli_v2 import cli

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_macato_agent(mocker):
    return mocker.patch('cli_v2.MacatoAgent').return_value

@pytest.fixture
def temp_model_file():
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp_file:
        joblib.dump({}, tmp_file.name)
        yield tmp_file.name
    Path(tmp_file.name).unlink()  # Clean up the temporary file

def test_update_fields(runner, mock_macato_agent):
    result = runner.invoke(cli, ['update-table', '--fields'])
    assert result.exit_code == 0
    assert "Fields table updated successfully." in result.output
    mock_macato_agent.update_fields.assert_called_once()

def test_update_versions(runner, mock_macato_agent):
    result = runner.invoke(cli, ['update-table', '--versions'])
    assert result.exit_code == 0
    assert "Versions table updated successfully." in result.output
    mock_macato_agent.update_docato_version.assert_called_once()

def test_update_output(runner, mock_macato_agent, temp_model_file):
    result = runner.invoke(cli, ['update-table', '--output', '--model', temp_model_file])
    assert result.exit_code == 0
    assert f"Model loaded successfully from {temp_model_file}" in result.output
    assert "Output table updated successfully." in result.output
    mock_macato_agent.load_model.assert_called_once_with(Path(temp_model_file))
    mock_macato_agent.update_output.assert_called_once()

def test_update_multiple_tables(runner, mock_macato_agent):
    result = runner.invoke(cli, ['update-table', '--fields', '--versions'])
    assert result.exit_code == 0
    assert "Fields table updated successfully." in result.output
    assert "Versions table updated successfully." in result.output
    mock_macato_agent.update_fields.assert_called_once()
    mock_macato_agent.update_docato_version.assert_called_once()

def test_update_all_tables(runner, mock_macato_agent, temp_model_file):
    result = runner.invoke(cli, ['update-table', '--all', '--model', temp_model_file])
    assert result.exit_code == 0
    assert f"Model loaded successfully from {temp_model_file}" in result.output
    assert "Fields table updated successfully." in result.output
    assert "Versions table updated successfully." in result.output
    assert "Output table updated successfully." in result.output
    assert "All tables updated successfully." in result.output
    mock_macato_agent.load_model.assert_called_once_with(Path(temp_model_file))
    mock_macato_agent.update_fields.assert_called_once()
    mock_macato_agent.update_docato_version.assert_called_once()
    mock_macato_agent.update_output.assert_called_once()

def test_update_all_without_model(runner, mock_macato_agent):
    result = runner.invoke(cli, ['update-table', '--all'])
    assert result.exit_code == 0
    assert "Error: --model is required when using --all" in result.output
    mock_macato_agent.update_fields.assert_not_called()
    mock_macato_agent.update_docato_version.assert_not_called()
    mock_macato_agent.update_output.assert_not_called()

def test_update_output_without_model(runner, mock_macato_agent):
    result = runner.invoke(cli, ['update-table', '--output'])
    assert result.exit_code == 0
    assert "Error: --model is required when updating output" in result.output
    mock_macato_agent.update_output.assert_not_called()

def test_update_all_with_exception(runner, mock_macato_agent, temp_model_file):
    mock_macato_agent.update_fields.side_effect = Exception("Update error")
    result = runner.invoke(cli, ['update-table', '--all', '--model', temp_model_file])
    assert result.exit_code == 0
    assert "Error updating all tables: Update error" in result.output
    mock_macato_agent.load_model.assert_called_once_with(Path(temp_model_file))
    mock_macato_agent.update_fields.assert_called_once()
    mock_macato_agent.update_docato_version.assert_not_called()
    mock_macato_agent.update_output.assert_not_called()

def test_individual_update_with_exception(runner, mock_macato_agent):
    mock_macato_agent.update_fields.side_effect = Exception("Update error")
    result = runner.invoke(cli, ['update-table', '--fields'])
    assert result.exit_code == 0
    assert "Error updating tables: Update error" in result.output
    mock_macato_agent.update_fields.assert_called_once()