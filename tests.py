# test_config.py

import os
import pytest
from unittest.mock import patch
from pytest_mock import MockerFixture

from config import get_db_config, Environment, get_user_id_tdm


def test_get_user_id_tdm_success(mocker: MockerFixture):
    # Mock os.getuid and pwd.getpwuid to return a specific username
    mocker.patch('config.os.getuid', return_value=1000)
    mocker.patch('config.pwd.getpwuid', return_value=type('pwdstruct', (object,), {'pw_name': 'jdoe@domain.com'}))

    user_id = get_user_id_tdm()
    assert user_id == 'jdoe'

def test_get_user_id_tdm_no_at_symbol(mocker: MockerFixture):
    # Mock os.getuid and pwd.getpwuid to return a username without '@'
    mocker.patch('config.os.getuid', return_value=1000)
    mocker.patch('config.pwd.getpwuid', return_value=type('pwdstruct', (object,), {'pw_name': 'jdoe'}))

    user_id = get_user_id_tdm()
    assert user_id == 'jdoe'

def test_get_user_id_tdm_key_error(mocker: MockerFixture, caplog):
    # Mock pwd.getpwuid to raise KeyError
    mocker.patch('config.os.getuid', return_value=1000)
    mocker.patch('config.pwd.getpwuid', side_effect=KeyError)

    user_id = get_user_id_tdm()
    assert user_id is None
    assert "User ID not found in the password database." in caplog.text

def test_get_user_id_tdm_exception(mocker: MockerFixture, caplog):
    # Mock pwd.getpwuid to raise an unexpected exception
    mocker.patch('config.os.getuid', return_value=1000)
    mocker.patch('config.pwd.getpwuid', side_effect=Exception("Test exception"))

    user_id = get_user_id_tdm()
    assert user_id is None
    assert "An unexpected error occurred: Test exception" in caplog.text

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
    # Mock get_user_id_tdm to return a specific user ID
    mocker.patch('config.get_user_id_tdm', return_value='jdoe')

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
    # Mock get_user_id_tdm to return None
    mocker.patch('config.get_user_id_tdm', return_value=None)

    mocker.patch.dict(os.environ, {'AEP_ENV': 'dev'}, clear=True)
    with pytest.raises(ValueError) as excinfo:
        get_db_config()
    assert 'USERID could not be obtained for dev environment.' in str(excinfo.value)

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
