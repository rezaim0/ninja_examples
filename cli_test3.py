import pytest
from click.testing import CliRunner
from cli_v2 import cli, log_buffer

@pytest.fixture(autouse=True)
def clear_log_buffer():
    """
    Fixture to clear the log buffer before and after each test.

    This ensures that logs from one test do not interfere with another.
    """
    log_buffer.seek(0)
    log_buffer.truncate(0)
    yield
    log_buffer.seek(0)
    log_buffer.truncate(0)

def test_update_all_with_model():
    """
    Test the update-table command with --all option and valid model.

    Ensures that all tables are updated correctly when the --all flag is used.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ['update-table', '--all', '--model', 'path/to/valid_model.pkl'])

    # Check if the command ran successfully
    assert result.exit_code == 0
    # Check log buffer for success messages
    log_output = log_buffer.getvalue()
    assert 'Model loaded successfully from path/to/valid_model.pkl' in log_output
    assert 'Fields table updated successfully.' in log_output
    assert 'Versions table updated successfully.' in log_output
    assert 'Output table updated successfully.' in log_output

def test_update_fields():
    """
    Test the update-table command with --fields option.

    Verifies that only the fields table is updated when --fields flag is used.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ['update-table', '--fields'])

    # Check if the command ran successfully
    assert result.exit_code == 0
    # Check log buffer for the fields table update message
    log_output = log_buffer.getvalue()
    assert 'Fields table updated successfully.' in log_output

def test_update_versions():
    """
    Test the update-table command with --versions option.

    Ensures that only the versions table is updated when --versions flag is used.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ['update-table', '--versions'])

    # Check if the command ran successfully
    assert result.exit_code == 0
    # Check log buffer for the versions table update message
    log_output = log_buffer.getvalue()
    assert 'Versions table updated successfully.' in log_output

def test_update_output_requires_model():
    """
    Test the update-table command with --output option without model.

    Verifies that the CLI raises an error when --output is used without a model.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ['update-table', '--output'])

    # Check if the exit code indicates failure
    assert result.exit_code == 1
    # Check log buffer for the error message
    log_output = log_buffer.getvalue()
    assert 'Error: --model is required when updating output' in log_output

def test_update_output_with_model():
    """
    Test the update-table command with --output option and valid model.

    Ensures that the output table is updated when --output and --model are provided.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ['update-table', '--output', '--model', 'path/to/valid_model.pkl'])

    # Check if the command ran successfully
    assert result.exit_code == 0
    # Check log buffer for success messages
    log_output = log_buffer.getvalue()
    assert 'Model loaded successfully from path/to/valid_model.pkl' in log_output
    assert 'Output table updated successfully.' in log_output

def test_no_update_flags():
    """
    Test the update-table command with no update flags.

    Ensures that the CLI raises an error when no flags are provided.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ['update-table'])

    # Check if the exit code indicates failure
    assert result.exit_code == 1
    # Check log buffer for the error message
    log_output = log_buffer.getvalue()
    assert 'Error: No update options provided.' in log_output

def test_update_all_without_model():
    """
    Test the update-table command with --all option without providing model.

    Verifies that the CLI raises an error when --all is used without a model.
    """
    runner = CliRunner()
    result = runner.invoke(cli, ['update-table', '--all'])

    # Check if the exit code indicates failure
    assert result.exit_code == 1
    # Check log buffer for the error message
    log_output = log_buffer.getvalue()
    assert 'Error: --model is required when using --all' in log_output
