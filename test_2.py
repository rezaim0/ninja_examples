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

    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    assert "Missing table names for keys:" in str(exc_info.value)

def test_get_db_config_invalid_env(mocker: MockerFixture):
    """Tests that get_db_config raises ValueError for an invalid environment."""
    mocker.patch.dict(os.environ, {'AEP_ENV': 'invalid_env'}, clear=True)

    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    assert "Invalid environment specified in AEP_ENV:" in str(exc_info.value)
