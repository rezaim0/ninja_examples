"""Test module for configuration management functionality.

This module contains test cases for the config module's functionality, including 
configuration loading, user ID validation, and database configuration management.
"""

import os
import pytest
from pytest_mock import MockerFixture
from config import (
    load_config,
    get_user_id,
    get_db_config,
    DBConfig,
    Environment,
)
from loguru import logger

# Constants for test values
TEST_USER_ID = 'u1234'
TEST_NOTEBOOK_PATH = '/user/notebook'
DEFAULT_TABLE_NAMES = {
    'fields': 'modelops_docato_fields',
    'output': 'modelops_docato_output',
    'version': 'modelops_docato_version'
}
TEST_DATABASE_EDW = 'edw'
TEST_DATABASE_LOCAL = 'local.db'
TEST_SCHEMA_PTAP = 'ptap'
TEST_SCHEMA_PMODEL = 'pmodel'

# Mock configuration for tests
mock_config = {
    'local': {
        'database': TEST_DATABASE_LOCAL,
        'schema': None,
        'table_names': list(DEFAULT_TABLE_NAMES.values()),
    },
    'dev': {
        'database': TEST_DATABASE_EDW,
        'schema': TEST_SCHEMA_PTAP,
        'table_names': list(DEFAULT_TABLE_NAMES.values()),
    },
    'staging': {
        'database': TEST_DATABASE_EDW,
        'schema': TEST_SCHEMA_PTAP,
        'table_names': list(DEFAULT_TABLE_NAMES.values()),
    },
    'prod': {
        'database': TEST_DATABASE_EDW,
        'schema': TEST_SCHEMA_PMODEL,
        'table_names': list(DEFAULT_TABLE_NAMES.values()),
    },
}

def test_load_config_success(mocker: MockerFixture):
    """Test that `load_config` successfully loads the configuration."""
    sample_yaml = f"""
local:
    database: {TEST_DATABASE_LOCAL}
    schema: null
    table_names:
        - modelops_docato_fields
        - modelops_docato_output
        - modelops_docato_version
dev:
    database: {TEST_DATABASE_EDW}
    schema: {TEST_SCHEMA_PTAP}
    table_names:
        - modelops_docato_fields
        - modelops_docato_output
        - modelops_docato_version
    """
    mocker.patch('builtins.open', mocker.mock_open(read_data=sample_yaml))
    config = load_config("dummy/path/config.yaml")
    
    # Test local environment config
    assert config['local']['database'] == TEST_DATABASE_LOCAL
    assert config['local']['schema'] is None
    assert config['local']['table_names'] == list(DEFAULT_TABLE_NAMES.values())

def test_load_config_file_not_found(mocker: MockerFixture):
    """Test that `load_config` raises FileNotFoundError when the file does not exist."""
    mocker.patch('builtins.open', side_effect=FileNotFoundError)
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent/config.yaml")

def test_get_user_id_validations(mocker: MockerFixture):
    """Tests user ID extraction with different notebook prefix patterns."""
    test_cases = [
        (f'{TEST_NOTEBOOK_PATH}/{TEST_USER_ID}-notebook', TEST_USER_ID),
        (f'{TEST_NOTEBOOK_PATH}/invalid', None),
        (f'{TEST_NOTEBOOK_PATH}/12345-notebook', None),
    ]
    for nb_prefix, expected in test_cases:
        mocker.patch.dict(os.environ, {'NB_PREFIX': nb_prefix})
        result = get_user_id()
        assert result == expected

@pytest.mark.parametrize("env,expected_db,expected_schema,expected_table_prefix", [
    ("local", TEST_DATABASE_LOCAL, None, ""),
    ("dev", TEST_DATABASE_EDW, TEST_SCHEMA_PTAP, f"{TEST_USER_ID}_"),
    ("staging", TEST_DATABASE_EDW, TEST_SCHEMA_PTAP, ""),
    ("prod", TEST_DATABASE_EDW, TEST_SCHEMA_PMODEL, ""),
])
def test_get_db_config_environments(mocker: MockerFixture, env, expected_db, expected_schema, expected_table_prefix):
    """Tests database configuration for different environments."""
    mocker.patch('config.load_config', return_value=mock_config)
    mocker.patch('config.get_user_id', return_value=TEST_USER_ID if env == "dev" else None)
    mocker.patch.dict(os.environ, {'AEP_ENV': env}, clear=True)

    config = get_db_config()
    assert config.database == expected_db
    assert config.schema == expected_schema
    assert config.table_names == {key: f"{expected_table_prefix}{name}" for key, name in DEFAULT_TABLE_NAMES.items()}

def test_get_db_config_missing_table_names(mocker: MockerFixture):
    """Tests that get_db_config raises an error if required table names are missing."""
    mock_incomplete_config = {
        'local': {
            'database': TEST_DATABASE_LOCAL,
            'table_names': ['modelops_docato_fields'],  # Missing 'output' and 'version'
        }
    }
    mocker.patch('config.load_config', return_value=mock_incomplete_config)
    mocker.patch.dict(os.environ, {'AEP_ENV': 'local'}, clear=True)
    mock_logger = mocker.patch('config.logger')

    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    assert "Missing table names for keys:" in str(exc_info.value)
    mock_logger.error.assert_called_once_with("Missing table names for keys: {'version', 'output'}")

def test_get_db_config_invalid_env(mocker: MockerFixture):
    """Tests that get_db_config raises ValueError for an invalid environment."""
    mocker.patch.dict(os.environ, {'AEP_ENV': 'invalid_env'}, clear=True)
    mock_logger = mocker.patch('config.logger')

    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    assert "Invalid environment specified in AEP_ENV:" in str(exc_info.value)
    mock_logger.error.assert_called_once_with("Invalid environment specified in AEP_ENV: invalid_env")

def test_get_user_id_nb_prefix_not_set(mocker: MockerFixture):
    """Test `get_user_id` returns None when NB_PREFIX is not set and logs an error."""
    mocker.patch.dict(os.environ, {}, clear=True)
    mock_logger = mocker.patch('config.logger')

    user_id = get_user_id()
    assert user_id is None
    mock_logger.error.assert_called_once_with("NB_PREFIX environment variable is not set.")

def test_get_user_id_insufficient_parts(mocker: MockerFixture):
    """Test `get_user_id` returns None when NB_PREFIX does not have enough parts and logs an error."""
    mocker.patch.dict(os.environ, {'NB_PREFIX': '/user'}, clear=True)
    mock_logger = mocker.patch('config.logger')

    user_id = get_user_id()
    assert user_id is None
    mock_logger.error.assert_called_once_with("NB_PREFIX does not contain enough parts to extract user ID.")

def test_get_user_id_exception(mocker: MockerFixture):
    """Test `get_user_id` handles exceptions and logs an exception message."""
    mocker.patch('os.getenv', side_effect=Exception('Unexpected error'))
    mock_logger = mocker.patch('config.logger')

    user_id = get_user_id()
    assert user_id is None
    mock_logger.exception.assert_called_once_with("An error occurred while retrieving the user ID: Unexpected error")

@pytest.mark.parametrize("env_config,expected_error", [
    ({}, "No configuration found for environment: local"),
    ({'local': {}}, None),
    ({'local': {'database': TEST_DATABASE_LOCAL}}, None),
    ({'local': {'schema': None}}, None),
])
def test_get_db_config_structure_variations(mocker: MockerFixture, env_config, expected_error):
    """Tests database configuration with different config structure variations and checks for missing fields."""
    mocker.patch('config.load_config', return_value=env_config)
    mocker.patch.dict(os.environ, {'AEP_ENV': 'local'}, clear=True)
    mock_logger = mocker.patch('config.logger')

    if expected_error:
        with pytest.raises(ValueError) as exc_info:
            get_db_config()
        assert expected_error in str(exc_info.value)
        mock_logger.error.assert_called_once_with(expected_error)
    else:
        config = get_db_config()
        assert isinstance(config, DBConfig)
        assert config.environment == Environment.LOCAL
