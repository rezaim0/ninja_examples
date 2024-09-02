import pytest
from click.testing import CliRunner
from pathlib import Path
from typing import Generator, Any
import tempfile
import joblib
from loguru import logger
from cli_v3 import cli, MacatoAgent  # Import from the updated CLI script

@pytest.fixture()
def caplog(capfd):
    logger.remove()
    logger.add(capfd.handle, format="{level}: {message}")
    yield capfd

@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()

@pytest.fixture
def mock_macato_agent(mocker: Any) -> Any:
    return mocker.patch('cli_v3.MacatoAgent', autospec=True)

@pytest.fixture
def temp_model_file() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp_file:
        joblib.dump({}, tmp_file.name)
        yield tmp_file.name
    Path(tmp_file.name).unlink()

def test_update_fields(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    result = runner.invoke(cli, ['update-table', '--fields'])
    assert result.exit_code == 0
    assert "INFO: Fields table updated successfully." in caplog.readouterr().err

def test_update_versions(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    result = runner.invoke(cli, ['update-table', '--versions'])
    assert result.exit_code == 0
    assert "INFO: Versions table updated successfully." in caplog.readouterr().err

def test_update_output(runner: CliRunner, mock_macato_agent: Any, temp_model_file: str, caplog) -> None:
    result = runner.invoke(cli, ['update-table', '--output', '--model', temp_model_file])
    assert result.exit_code == 0
    captured = caplog.readouterr().err
    assert f"INFO: Model loaded successfully from {temp_model_file}" in captured
    assert "INFO: Output table updated successfully." in captured

def test_update_all_tables(runner: CliRunner, mock_macato_agent: Any, temp_model_file: str, caplog) -> None:
    result = runner.invoke(cli, ['update-table', '--all', '--model', temp_model_file])
    assert result.exit_code == 0
    captured = caplog.readouterr().err
    assert f"INFO: Model loaded successfully from {temp_model_file}" in captured
    assert "INFO: Fields table updated successfully." in captured
    assert "INFO: Versions table updated successfully." in captured
    assert "INFO: Output table updated successfully." in captured
    assert "SUCCESS: All tables updated successfully." in captured

def test_update_all_without_model(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    result = runner.invoke(cli, ['update-table', '--all'])
    assert result.exit_code != 0
    assert "Error: --model is required when using --all" in result.output
    assert "ERROR: --model is required when using --all" in caplog.readouterr().err

def test_update_output_without_model(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    result = runner.invoke(cli, ['update-table', '--output'])
    assert result.exit_code != 0
    assert "Error: --model is required when updating output" in result.output
    assert "ERROR: --model is required when updating output" in caplog.readouterr().err

def test_update_with_exception(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    mock_macato_agent.return_value.update_fields.side_effect = Exception("Update error")
    result = runner.invoke(cli, ['update-table', '--fields'])
    assert result.exit_code != 0
    assert "Error: Update error" in result.output
    assert "ERROR: Error updating tables: Update error" in caplog.readouterr().err

def test_no_options_specified(runner: CliRunner, mock_macato_agent: Any, caplog) -> None:
    result = runner.invoke(cli, ['update-table'])
    assert result.exit_code == 0
    assert "No update option specified. Please use --fields, --versions, --output, or --all." in result.output
    captured = caplog.readouterr().err
    assert "WARNING: No update options provided." in captured
    assert "No update option specified. Please use --fields, --versions, --output, or --all." in result.output