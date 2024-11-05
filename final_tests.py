"""Database Configuration Test Module.

This module contains comprehensive test cases for the database configuration module.
It tests the loading and parsing of configuration files, environment handling,
user ID extraction, and database configuration management across different environments.

The test suite uses pytest and pytest-mock for mocking external dependencies and
verifies the behavior of all major components of the configuration system.

Typical usage example:
    pytest test_config.py -v

Note:
    All test functions use pytest fixtures and mocking to isolate tests from
    external dependencies and ensure consistent test execution.
"""

from typing import Dict, Optional, Any
import pytest
from pathlib import Path
from unittest.mock import mock_open
import yaml
from enum import Enum

from macato.config import (
    Environment,
    DBConfig,
    load_config,
    get_user_id,
    get_db_config,
)

# Test configuration dictionary
TEST_CONFIG: Dict[str, Any] = {
    "default": {
        "table_names": [
            "modelops_docato_fields",
            "modelops_docato_output",
            "modelops_docato_version"
        ]
    },
    "local": {
        "table_names": [
            "modelops_docato_fields",
            "modelops_docato_output",
            "modelops_docato_version"
        ],
        "database": "local.db",
        "schema": None
    },
    "dev": {
        "table_names": [
            "modelops_docato_fields",
            "modelops_docato_output",
            "modelops_docato_version"
        ],
        "database": "edw",
        "schema": "ptap"
    },
    "staging": {
        "table_names": [
            "modelops_docato_fields",
            "modelops_docato_output",
            "modelops_docato_version"
        ],
        "database": "edw",
        "schema": "ptap"
    },
    "prod": {
        "table_names": [
            "modelops_docato_fields",
            "modelops_docato_output",
            "modelops_docato_version"
        ],
        "database": "edw",
        "schema": "pmodel"
    }
}

def test_environment_enum() -> None:
    """Test the Environment enumeration values.
    
    Verifies that all environment values in the Environment enum are correctly
    defined and match the expected string values.
    """
    assert Environment.LOCAL.value == "local"
    assert Environment.DEV.value == "dev"
    assert Environment.STAGING.value == "staging"
    assert Environment.PROD.value == "prod"

def test_dbconfig_initialization() -> None:
    """Test DBConfig dataclass initialization and attribute assignment.
    
    Verifies that the DBConfig dataclass correctly initializes with provided
    values and maintains proper attribute access.
    """
    config = DBConfig(
        environment=Environment.LOCAL,
        database="local.db",
        schema=None,
        table_names={
            "fields": "modelops_docato_fields",
            "output": "modelops_docato_output",
            "version": "modelops_docato_version"
        }
    )
    
    assert config.environment == Environment.LOCAL
    assert config.database == "local.db"
    assert config.schema is None
    assert config.table_names == {
        "fields": "modelops_docato_fields",
        "output": "modelops_docato_output",
        "version": "modelops_docato_version"
    }

def test_load_config(mocker: Any) -> None:
    """Test configuration loading from YAML file.
    
    Args:
        mocker: Pytest fixture for mocking.
        
    Tests loading of configuration with YAML anchors and verifies the
    correct inheritance and override of values across environments.
    """
    yaml_content = """
default: &default
 table_names:
 - modelops_docato_fields
 - modelops_docato_output
 - modelops_docato_version
local:
 <<: *default
 database: local.db
 schema: null
dev:
 <<: *default
 database: edw
 schema: ptap
staging:
 <<: *default
 database: edw
 schema: ptap
prod:
 <<: *default
 database: edw
 schema: pmodel
"""
    mocker.patch("builtins.open", mock_open(read_data=yaml_content))
    
    config = load_config()
    assert "default" in config
    assert config["local"]["database"] == "local.db"
    assert config["local"]["schema"] is None
    assert config["dev"]["database"] == "edw"
    assert config["dev"]["schema"] == "ptap"
    assert config["prod"]["schema"] == "pmodel"
    assert "modelops_docato_fields" in config["local"]["table_names"]

def test_load_config_file_not_found(mocker: Any) -> None:
    """Test error handling when configuration file is not found.
    
    Args:
        mocker: Pytest fixture for mocking.
        
    Verifies that appropriate exception is raised when config file is missing.
    """
    mocker.patch("builtins.open", side_effect=FileNotFoundError)
    with pytest.raises(FileNotFoundError):
        load_config()

@pytest.mark.parametrize(
    "env,expected_db,expected_schema",
    [
        ("local", "local.db", None),
        ("dev", "edw", "ptap"),
        ("staging", "edw", "ptap"),
        ("prod", "edw", "pmodel"),
    ]
)
def test_get_db_config_environments(
    mocker: Any,
    env: str,
    expected_db: str,
    expected_schema: Optional[str]
) -> None:
    """Test database configuration for different environments.
    
    Args:
        mocker: Pytest fixture for mocking.
        env: Environment name to test.
        expected_db: Expected database name for the environment.
        expected_schema: Expected schema name for the environment.
        
    Tests configuration loading and validation for each supported environment.
    Verifies correct database and schema settings, and proper table name handling.
    """
    yaml_content = """
default: &default
 table_names:
 - modelops_docato_fields
 - modelops_docato_output
 - modelops_docato_version
local:
 <<: *default
 database: local.db
 schema: null
dev:
 <<: *default
 database: edw
 schema: ptap
staging:
 <<: *default
 database: edw
 schema: ptap
prod:
 <<: *default
 database: edw
 schema: pmodel
"""
    mocker.patch("builtins.open", mock_open(read_data=yaml_content))
    mocker.patch.dict('os.environ', {'AEP_ENV': env})
    if env == "dev":
        mocker.patch('macato.config.get_user_id', return_value='u1234')
    
    config = get_db_config()
    
    assert config.environment == Environment(env)
    assert config.database == expected_db
    assert config.schema == expected_schema
    
    expected_table_names = {
        "fields": "modelops_docato_fields",
        "output": "modelops_docato_output",
        "version": "modelops_docato_version"
    }
    
    if env == "dev":
        expected_table_names = {
            key: f"u1234_{value}" 
            for key, value in expected_table_names.items()
        }
    
    assert config.table_names == expected_table_names

def test_get_db_config_dev_environment(mocker: Any) -> None:
    """Test specific behavior of dev environment configuration.
    
    Args:
        mocker: Pytest fixture for mocking.
        
    Tests dev environment specific features including user ID prefixing
    for table names and proper schema/database settings.
    """
    yaml_content = """
default: &default
 table_names:
 - modelops_docato_fields
 - modelops_docato_output
 - modelops_docato_version
dev:
 <<: *default
 database: edw
 schema: ptap
"""
    mocker.patch("builtins.open", mock_open(read_data=yaml_content))
    mocker.patch.dict('os.environ', {'AEP_ENV': 'dev'})
    mocker.patch('macato.config.get_user_id', return_value='u1234')
    
    config = get_db_config()
    
    assert config.environment == Environment.DEV
    assert config.database == "edw"
    assert config.schema == "ptap"
    assert all(table.startswith('u1234_') for table in config.table_names.values())
    assert "modelops_docato_fields" in config.table_names["fields"]

def test_get_db_config_missing_user_id_in_dev(mocker: Any) -> None:
    """Test error handling when user ID is missing in dev environment.
    
    Args:
        mocker: Pytest fixture for mocking.
        
    Verifies that appropriate error is raised when user ID cannot be
    determined in dev environment.
    """
    mocker.patch.dict('os.environ', {'AEP_ENV': 'dev'})
    mocker.patch('macato.config.load_config', return_value=TEST_CONFIG)
    mocker.patch('macato.config.get_user_id', return_value=None)
    
    with pytest.raises(ValueError, match="USERID could not be extracted"):
        get_db_config()

def test_get_db_config_invalid_environment(mocker: Any) -> None:
    """Test error handling for invalid environment specification.
    
    Args:
        mocker: Pytest fixture for mocking.
        
    Verifies that appropriate error is raised when invalid environment
    is specified.
    """
    mocker.patch.dict('os.environ', {'AEP_ENV': 'invalid'})
    
    with pytest.raises(ValueError, match="Invalid environment specified in AEP_ENV"):
        get_db_config()

def test_get_db_config_environment_fallback(mocker: Any) -> None:
    """Test environment fallback behavior when no environment is specified.
    
    Args:
        mocker: Pytest fixture for mocking.
        
    Verifies that configuration falls back to local environment when
    no environment is specified.
    """
    yaml_content = """
default: &default
 table_names:
 - modelops_docato_fields
 - modelops_docato_output
 - modelops_docato_version
local:
 <<: *default
 database: local.db
 schema: null
"""
    mocker.patch("builtins.open", mock_open(read_data=yaml_content))
    mocker.patch.dict('os.environ', {}, clear=True)
    
    config = get_db_config()
    assert config.environment == Environment.LOCAL
    assert config.database == "local.db"
    assert config.schema is None

@pytest.mark.parametrize(
    "nb_prefix,expected",
    [
        ("/jupyter/kubeworkspace/u1234-workspace", "u1234"),
        ("/jupyter/kubeworkspace/u5678-workspace", "u5678"),
        (None, None),
        ("/invalid/path", None),
        ("/jupyter/kubeworkspace/invalid-workspace", None),
        ("/jupyter/kubeworkspace/user123-workspace", None),  # Invalid user ID format
    ]
)
def test_get_user_id(mocker: Any, nb_prefix: Optional[str], expected: Optional[str]) -> None:
    """Test user ID extraction from environment variables.
    
    Args:
        mocker: Pytest fixture for mocking.
        nb_prefix: The notebook prefix path to test.
        expected: Expected user ID result.
        
    Tests various scenarios of user ID extraction including valid and invalid
    formats, missing variables, and edge cases.
    """
    mocker.patch.dict('os.environ', {'NB_PREFIX': nb_prefix} if nb_prefix else {})
    assert get_user_id() == expected