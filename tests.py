import os
import pytest
import re
from pytest_mock import MockerFixture

from config import get_db_config, Environment, get_userid_from_log


# Test data for get_userid_from_log
LOG_DIRECTORY = '/efs/ngh764@prod.abcnet.au'
LOG_FILE_CONTENT = "/efs/jdoe@prod.abcnet.au Some log content"


def test_get_userid_from_log_success(mocker: MockerFixture):
    # Mock os.getenv to return a custom log directory
    mocker.patch('os.getenv', return_value=LOG_DIRECTORY)

    # Mock os.listdir to return a list containing one log file
    mocker.patch('os.listdir', return_value=['test.log'])

    # Mock os.path.join to behave normally
    mocker.patch('os.path.join', side_effect=lambda a, b: f"{a}/{b}")

    # Mock open function to read the log file content
    mocker.patch('builtins.open', mocker.mock_open(read_data=LOG_FILE_CONTENT))

    # Mock re.compile to return a compiled pattern
    mocker.patch('re.compile', return_value=re.compile(r'/efs/(\w+)@prod\.abcnet\.au'))

    user_id = get_userid_from_log()
    assert user_id == 'jdoe'


def test_get_userid_from_log_no_log_files(mocker: MockerFixture, caplog):
    # Mock os.getenv to return a custom log directory
    mocker.patch('os.getenv', return_value=LOG_DIRECTORY)

    # Mock os.listdir to return an empty list
    mocker.patch('os.listdir', return_value=[])

    user_id = get_userid_from_log()
    assert user_id is None
    assert "No .log file found in the directory" in caplog.text


def test_get_userid_from_log_no_matching_userid(mocker: MockerFixture, caplog):
    # Mock os.getenv to return a custom log directory
    mocker.patch('os.getenv', return_value=LOG_DIRECTORY)

    # Mock os.listdir to return a list containing one log file
    mocker.patch('os.listdir', return_value=['test.log'])

    # Mock os.path.join
    mocker.patch('os.path.join', side_effect=lambda a, b: f"{a}/{b}")

    # Mock open function to read log content without matching user ID
    mocker.patch('builtins.open', mocker.mock_open(read_data="No matching content"))

    # Mock re.compile
    mocker.patch('re.compile', return_value=re.compile(r'/efs/(\w+)@prod\.abcnet\.au'))

    user_id = get_userid_from_log()
    assert user_id is None
    assert "No user ID found in any files" in caplog.text


def test_get_userid_from_log_oserror(mocker: MockerFixture, caplog):
    # Mock os.getenv to return a custom log directory
    mocker.patch('os.getenv', return_value=LOG_DIRECTORY)

    # Mock os.listdir to raise an OSError
    mocker.patch('os.listdir', side_effect=OSError("Test OSError"))

    user_id = get_userid_from_log()
    assert user_id is None
    assert "An error occurred: Test OSError" in caplog.text


def test_local_environment(mocker: MockerFixture):
    mocker.patch.dict(os.environ, {'AEP_ENV': 'local'}, clear=True)
    db_config = get_db_config()
    assert db_config.environment == Environment.LOCAL
    assert db_config.database == 'local.db'
    assert db_config.schema is None
    expected_table_names = [
        'modelops_docato_fields',
        'modelops_docato_output',
        'modelops_docato_version',
    ]
    assert db_config.table_names == expected_table_names


def test_dev_environment_with_userid(mocker: MockerFixture):
    # Mock get_userid_from_log to return a specific user ID
    mocker.patch('config.get_userid_from_log', return_value='jdoe')

    mocker.patch.dict(os.environ, {'AEP_ENV': 'dev'}, clear=True)
    db_config = get_db_config()
    assert db_config.environment == Environment.DEV
    assert db_config.database == 'edw'
    assert db_config.schema == 'ptap'
    expected_table_names = [
        'jdoe_modelops_docato_fields',
        'jdoe_modelops_docato_output',
        'jdoe_modelops_docato_version',
    ]
    assert db_config.table_names == expected_table_names


def test_dev_environment_missing_userid(mocker: MockerFixture):
    # Mock get_userid_from_log to return None
    mocker.patch('config.get_userid_from_log', return_value=None)

    mocker.patch.dict(os.environ, {'AEP_ENV': 'dev'}, clear=True)
    with pytest.raises(ValueError) as excinfo:
        get_db_config()
    assert 'USERID could not be extracted from logs for dev environment.' in str(excinfo.value)


def test_staging_environment(mocker: MockerFixture):
    mocker.patch.dict(os.environ, {'AEP_ENV': 'staging'}, clear=True)
    db_config = get_db_config()
    assert db_config.environment == Environment.STAGING
    assert db_config.database == 'edw'
    assert db_config.schema == 'ptap'
    expected_table_names = [
        'modelops_docato_fields',
        'modelops_docato_output',
        'modelops_docato_version',
    ]
    assert db_config.table_names == expected_table_names


def test_prod_environment(mocker: MockerFixture):
    mocker.patch.dict(os.environ, {'AEP_ENV': 'prod'}, clear=True)
    db_config = get_db_config()
    assert db_config.environment == Environment.PROD
    assert db_config.database == 'edw'
    assert db_config.schema == 'pmodel'
    expected_table_names = [
        'modelops_docato_fields',
        'modelops_docato_output',
        'modelops_docato_version',
    ]
    assert db_config.table_names == expected_table_names


def test_invalid_environment(mocker: MockerFixture):
    mocker.patch.dict(os.environ, {'AEP_ENV': 'invalid_env'}, clear=True)
    with pytest.raises(ValueError) as excinfo:
        get_db_config()
    assert 'Invalid environment specified in AEP_ENV' in str(excinfo.value)
