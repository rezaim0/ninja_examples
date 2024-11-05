"""Tests for the database configuration module.

This module contains comprehensive test cases for the database configuration functionality,
including environment handling, config loading, and user ID extraction. The tests are
specifically designed for the YAML configuration that uses anchors and inheritance
for different environments.

Note:
    These tests cover both success and failure scenarios for all major functions
    in the database configuration module.
"""

import os
from pathlib import Path
from typing import Dict, Any

import pytest
import yaml
from pytest_mock import MockerFixture

from config import (
    DBConfig,
    Environment,
    load_config,
    get_user_id,
    get_db_config
)

@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """
    Provides a sample configuration dictionary matching the actual config structure.

    Returns:
        Dict[str, Any]: A dictionary containing test configuration data with YAML anchors.
    """
    return {
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

@pytest.fixture
def mock_config_file(tmp_path: Path) -> Path:
    """
    Creates a temporary config file with the actual YAML structure.

    Args:
        tmp_path (Path): Pytest fixture providing temporary directory path.

    Returns:
        Path: Path to the temporary config file.
    """
    config_content = """
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
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return config_file

def test_load_config(mock_config_file: Path) -> None:
    """
    Tests the load_config function with the actual configuration structure.

    Args:
        mock_config_file (Path): Path to the test configuration file.
    """
    config = load_config(str(mock_config_file))
    assert isinstance(config, dict)
    
    # Check inheritance from default
    environments = ["local", "dev", "staging", "prod"]
    for env in environments:
        assert env in config
        assert "table_names" in config[env]
        assert len(config[env]["table_names"]) == 3
        assert "modelops_docato_fields" in config[env]["table_names"]
        assert "modelops_docato_output" in config[env]["table_names"]
        assert "modelops_docato_version" in config[env]["table_names"]

    # Check environment-specific values
    assert config["local"]["database"] == "local.db"
    assert config["local"]["schema"] is None
    
    assert config["dev"]["database"] == "edw"
    assert config["dev"]["schema"] == "ptap"
    
    assert config["prod"]["database"] == "edw"
    assert config["prod"]["schema"] == "pmodel"

@pytest.mark.parametrize("environment,expected_db,expected_schema", [
    ("local", "local.db", None),
    ("dev", "edw", "ptap"),
    ("staging", "edw", "ptap"),
    ("prod", "edw", "pmodel"),
])
def test_get_db_config_environments(
    mocker: MockerFixture,
    mock_config_file: Path,
    environment: str,
    expected_db: str,
    expected_schema: str
) -> None:
    """
    Tests get_db_config function for all environments.

    Args:
        mocker (MockerFixture): Pytest mocker fixture.
        mock_config_file (Path): Path to test config file.
        environment (str): Test environment value.
        expected_db (str): Expected database name.
        expected_schema (str): Expected schema name.
    """
    mocker.patch.dict(os.environ, {"AEP_ENV": environment})
    if environment == "dev":
        mocker.patch.dict(os.environ, {"NB_PREFIX": "/hub/user/u1234-workspace"})
    
    mocker.patch("config.load_config", return_value=yaml.safe_load(mock_config_file.read_text()))
    
    config = get_db_config()
    assert isinstance(config, DBConfig)
    assert config.environment == Environment(environment)
    assert config.database == expected_db
    assert config.schema == expected_schema
    
    # Verify table names
    expected_tables = {
        "fields": "modelops_docato_fields",
        "output": "modelops_docato_output",
        "version": "modelops_docato_version"
    }
    
    if environment == "dev":
        expected_tables = {
            key: f"u1234_{value}" 
            for key, value in expected_tables.items()
        }
    
    assert config.table_names == expected_tables

def test_get_db_config_dev_table_prefixing(mocker: MockerFixture, mock_config_file: Path) -> None:
    """
    Tests table name prefixing in dev environment.

    Args:
        mocker (MockerFixture): Pytest mocker fixture.
        mock_config_file (Path): Path to test config file.
    """
    mocker.patch.dict(os.environ, {
        "AEP_ENV": "dev",
        "NB_PREFIX": "/hub/user/u1234-workspace"
    })
    mocker.patch("config.load_config", return_value=yaml.safe_load(mock_config_file.read_text()))
    
    config = get_db_config()
    for table_name in config.table_names.values():
        assert table_name.startswith("u1234_")
        assert "modelops_docato" in table_name

def test_table_mapping_consistency(mocker: MockerFixture, mock_config_file: Path) -> None:
    """
    Tests that table names are consistently mapped to their correct keys.

    Args:
        mocker (MockerFixture): Pytest mocker fixture.
        mock_config_file (Path): Path to test config file.
    """
    mocker.patch.dict(os.environ, {"AEP_ENV": "local"})
    mocker.patch("config.load_config", return_value=yaml.safe_load(mock_config_file.read_text()))
    
    config = get_db_config()
    assert "fields" in config.table_names
    assert config.table_names["fields"] == "modelops_docato_fields"
    assert "output" in config.table_names
    assert config.table_names["output"] == "modelops_docato_output"
    assert "version" in config.table_names
    assert config.table_names["version"] == "modelops_docato_version"

@pytest.mark.parametrize("invalid_table_names", [
    ["modelops_docato_fields", "modelops_docato_output"],  # Missing version
    ["modelops_docato_fields"],  # Missing multiple
    ["invalid_table_1", "invalid_table_2", "invalid_table_3"],  # All invalid
])
def test_get_db_config_invalid_table_names(
    mocker: MockerFixture,
    sample_config: Dict[str, Any],
    invalid_table_names: list
) -> None:
    """
    Tests get_db_config with invalid or missing table names.

    Args:
        mocker (MockerFixture): Pytest mocker fixture.
        sample_config (Dict[str, Any]): Sample configuration data.
        invalid_table_names (list): List of invalid table names to test.
    """
    sample_config["local"]["table_names"] = invalid_table_names
    
    mocker.patch.dict(os.environ, {"AEP_ENV": "local"})
    mocker.patch("config.load_config", return_value=sample_config)
    
    with pytest.raises(ValueError, match="Missing table names for keys"):
        get_db_config()