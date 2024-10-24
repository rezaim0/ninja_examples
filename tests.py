"""Test module for configuration management functionality.

This module contains test cases for the config module's functionality including 
configuration loading, user ID validation, and database configuration management.
"""

import os
import pytest
from pytest_mock import MockerFixture
import yaml

from config import (
    load_config,
    get_user_id,
    get_db_config,
    DBConfig,
    Environment,
)

# Constants for test values
TEST_USER_ID = 'u1234'
TEST_NOTEBOOK_PATH = '/user/notebook'
DEFAULT_TABLE_NAMES = [
    'modelops_docato_fields',
    'modelops_docato_output',
    'modelops_docato_version'
]
TEST_DATABASE_EDW = 'edw'
TEST_DATABASE_LOCAL = 'local.db'
TEST_SCHEMA_PTAP = 'ptap'
TEST_SCHEMA_PMODEL = 'pmodel'

# Mock configuration for tests
mock_config: dict = {
    'default': {
        'table_names': DEFAULT_TABLE_NAMES,
    },
    'local': {
        'database': TEST_DATABASE_LOCAL,
        'schema': None,
        'table_names': DEFAULT_TABLE_NAMES,
    },
    'dev': {
        'database': TEST_DATABASE_EDW,
        'schema': TEST_SCHEMA_PTAP,
        'table_names': DEFAULT_TABLE_NAMES,
    },
    'staging': {
        'database': TEST_DATABASE_EDW,
        'schema': TEST_SCHEMA_PTAP,
        'table_names': DEFAULT_TABLE_NAMES,
    },
    'prod': {
        'database': TEST_DATABASE_EDW,
        'schema': TEST_SCHEMA_PMODEL,
        'table_names': DEFAULT_TABLE_NAMES,
    },
}

def test_load_config_success(mocker: MockerFixture) -> None:
    """Test that `load_config` successfully loads the configuration.

    Args:
        mocker: The pytest-mock fixture for mocking.

    Returns:
        None
    """
    sample_yaml: str = f"""
default: &default
    table_names:
        - {DEFAULT_TABLE_NAMES[0]}
        - {DEFAULT_TABLE_NAMES[1]}
        - {DEFAULT_TABLE_NAMES[2]}
local:
    <<: *default
    database: {TEST_DATABASE_LOCAL}
    schema: null
staging:
    <<: *default
    database: {TEST_DATABASE_EDW}
    schema: {TEST_SCHEMA_PTAP}
dev:
    <<: *default
    database: {TEST_DATABASE_EDW}
    schema: {TEST_SCHEMA_PTAP}
"""
    mocker.patch('builtins.open', mocker.mock_open(read_data=sample_yaml))
    config: dict = load_config("dummy/path/config.yaml")
    
    # Test local environment config
    assert config['local']['database'] == TEST_DATABASE_LOCAL
    assert config['local']['schema'] is None
    
    # Test staging environment config
    assert config['staging']['database'] == TEST_DATABASE_EDW
    assert config['staging']['schema'] == TEST_SCHEMA_PTAP
    
    # Test dev environment config
    assert config['dev']['schema'] == TEST_SCHEMA_PTAP
    assert config['dev']['database'] == TEST_DATABASE_EDW
    
    # Test default configuration
    assert config['default']['table_names'] == DEFAULT_TABLE_NAMES
    
    # Verify inherited table_names in each environment
    assert config['local']['table_names'] == DEFAULT_TABLE_NAMES
    assert config['staging']['table_names'] == DEFAULT_TABLE_NAMES
    assert config['dev']['table_names'] == DEFAULT_TABLE_NAMES

def test_load_config_file_not_found(mocker: MockerFixture) -> None:
    """Test that `load_config` raises FileNotFoundError when the file does not exist.

    Args:
        mocker: The pytest-mock fixture for mocking.

    Returns:
        None

    Raises:
        FileNotFoundError: Expected to be raised when file is not found.
    """
    mocker.patch('builtins.open', side_effect=FileNotFoundError)
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent/config.yaml")

@pytest.mark.parametrize("nb_prefix,expected_result", [
    (f'{TEST_NOTEBOOK_PATH}/{TEST_USER_ID}-notebook', TEST_USER_ID),
    (f'{TEST_NOTEBOOK_PATH}/U1234-notebook', TEST_USER_ID),
    (f'{TEST_NOTEBOOK_PATH}/invalid', None),
    (f'{TEST_NOTEBOOK_PATH}/12345-notebook', None),
    (f'{TEST_NOTEBOOK_PATH}/u123-notebook', None),
])
def test_get_user_id_variations(mocker: MockerFixture, nb_prefix: str, expected_result: str) -> None:
    """Tests user ID extraction with different notebook prefix patterns.

    Args:
        mocker: Pytest fixture for mocking.
        nb_prefix: Notebook prefix path to test.
        expected_result: Expected user ID or None.

    Returns:
        None
    """
    mocker.patch.dict(os.environ, {'NB_PREFIX': nb_prefix}, clear=True)
    mock_logger = mocker.patch('config.logger')
    
    result = get_user_id()
    assert result == expected_result

def test_get_user_id_nb_prefix_not_set(mocker: MockerFixture) -> None:
    """Test `get_user_id` returns None when NB_PREFIX is not set.

    Args:
        mocker: The pytest-mock fixture for mocking.

    Returns:
        None
    """
    mocker.patch.dict(os.environ, {}, clear=True)
    mock_logger = mocker.patch('config.logger')

    user_id: None = get_user_id()
    assert user_id is None
    mock_logger.error.assert_called_with("NB_PREFIX environment variable is not set.")

def test_get_user_id_insufficient_parts(mocker: MockerFixture) -> None:
    """Test `get_user_id` returns None when NB_PREFIX does not have enough parts.

    Args:
        mocker: The pytest-mock fixture for mocking.

    Returns:
        None
    """
    mocker.patch.dict(os.environ, {'NB_PREFIX': '/user'}, clear=True)
    mock_logger = mocker.patch('config.logger')

    user_id: None = get_user_id()
    assert user_id is None
    mock_logger.error.assert_called_with("NB_PREFIX does not contain enough parts to extract user ID.")

def test_get_user_id_exception(mocker: MockerFixture) -> None:
    """Test `get_user_id` handles exceptions and returns None.

    Args:
        mocker: The pytest-mock fixture for mocking.

    Returns:
        None
    """
    mocker.patch('os.getenv', side_effect=Exception('Unexpected error'))
    mock_logger = mocker.patch('config.logger')

    user_id: None = get_user_id()
    assert user_id is None
    mock_logger.exception.assert_called_once()

@pytest.mark.parametrize("env,expected_db,expected_schema", [
    ("local", TEST_DATABASE_LOCAL, None),
    ("dev", TEST_DATABASE_EDW, TEST_SCHEMA_PTAP),
    ("staging", TEST_DATABASE_EDW, TEST_SCHEMA_PTAP),
    ("prod", TEST_DATABASE_EDW, TEST_SCHEMA_PMODEL),
])
def test_get_db_config_environments(mocker: MockerFixture, env: str, expected_db: str, expected_schema: str) -> None:
    """Tests database configuration for different environments.

    Args:
        mocker: Pytest fixture for mocking.
        env: Environment name to test.
        expected_db: Expected database name.
        expected_schema: Expected schema name.

    Returns:
        None
    """
    mocker.patch('config.load_config', return_value=mock_config)
    if env == "dev":
        mocker.patch('config.get_user_id', return_value=TEST_USER_ID)
    mocker.patch.dict(os.environ, {'AEP_ENV': env}, clear=True)
    
    config = get_db_config()
    assert config.database == expected_db
    assert config.schema == expected_schema
    assert isinstance(config.table_names, list)

@pytest.mark.parametrize("config_data,expected_error", [
    ({}, "No configuration found for environment: local"),
    ({'local': {}}, None),
    ({'local': {'database': TEST_DATABASE_LOCAL}}, None),
    ({'local': {'schema': None}}, None),
])
def test_get_db_config_structure_variations(mocker: MockerFixture, config_data: dict, expected_error: str) -> None:
    """Tests database configuration with different config structure variations.

    Args:
        mocker: Pytest fixture for mocking.
        config_data: Configuration dictionary to test.
        expected_error: Expected error message or None.

    Returns:
        None
    """
    mocker.patch('config.load_config', return_value=config_data)
    mocker.patch.dict(os.environ, {'AEP_ENV': 'local'}, clear=True)
    
    if expected_error:
        with pytest.raises(ValueError) as exc_info:
            get_db_config()
        assert expected_error in str(exc_info.value)
    else:
        config = get_db_config()
        assert isinstance(config, DBConfig)
        assert config.environment == Environment.LOCAL

def test_get_db_config_dev_valid_userid(mocker: MockerFixture) -> None:
    """Test `get_db_config` for dev environment with a valid user ID.

    Args:
        mocker: The pytest-mock fixture for mocking.

    Returns:
        None
    """
    mocker.patch('config.load_config', return_value=mock_config)
    mocker.patch('config.get_user_id', return_value=TEST_USER_ID)
    mocker.patch.dict(os.environ, {'AEP_ENV': 'dev'}, clear=True)

    db_config: DBConfig = get_db_config()
    expected_table_names: list = [
        f'{TEST_USER_ID}_{name}' for name in DEFAULT_TABLE_NAMES
    ]
    assert db_config.environment == Environment.DEV
    assert db_config.database == TEST_DATABASE_EDW
    assert db_config.schema == TEST_SCHEMA_PTAP
    assert db_config.table_names == expected_table_names

def test_get_db_config_dev_no_userid(mocker: MockerFixture) -> None:
    """Test `get_db_config` raises ValueError when user ID cannot be extracted in dev environment.

    Args:
        mocker: The pytest-mock fixture for mocking.

    Returns:
        None

    Raises:
        ValueError: Expected to be raised when user ID cannot be extracted.
    """
    mocker.patch('config.load_config', return_value=mock_config)
    mocker.patch('config.get_user_id', return_value=None)
    mocker.patch.dict(os.environ, {'AEP_ENV': 'dev'}, clear=True)

    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    assert "USERID could not be extracted for dev environment." in str(exc_info.value)

def test_get_db_config_invalid_env(mocker: MockerFixture) -> None:
    """Test `get_db_config` raises ValueError when AEP_ENV is invalid.

    Args:
        mocker: The pytest-mock fixture for mocking.

    Returns:
        None

    Raises:
        ValueError: Expected to be raised when AEP_ENV is invalid.
    """
    mocker.patch.dict(os.environ, {'AEP_ENV': 'invalid_env'}, clear=True)

    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    assert "Invalid environment specified in AEP_ENV: invalid_env" in str(exc_info.value)