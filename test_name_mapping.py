# test_utils.py

import pytest
from unittest.mock import MagicMock
from utils import get_physical_table_name
from config import DBConfig, Environment

# Assuming loguru logger is configured appropriately
# from loguru import logger

def test_get_physical_table_name_success_dev(mocker):
    # Mock db_config for dev environment
    mock_db_config = DBConfig(
        environment=Environment.DEV,
        database='edw',
        schema='ptap',
        table_names=[
            'u1234_modelops_docato_fields',
            'u1234_modelops_docato_output',
            'u1234_modelops_docato_version'
        ]
    )
    # Mock get_db_config to return the mocked db_config
    mocker.patch('utils.get_db_config', return_value=mock_db_config)

    # Test for each base table name
    base_names = [
        "modelops_docato_fields",
        "modelops_docato_output",
        "modelops_docato_version"
    ]
    expected_physical_names = mock_db_config.table_names

    for base_name, expected_physical_name in zip(base_names, expected_physical_names):
        physical_name = get_physical_table_name(base_name)
        assert physical_name == expected_physical_name

def test_get_physical_table_name_success_prod(mocker):
    # Mock db_config for prod environment
    mock_db_config = DBConfig(
        environment=Environment.PROD,
        database='edw',
        schema='pmodel',
        table_names=[
            'modelops_docato_fields',
            'modelops_docato_output',
            'modelops_docato_version'
        ]
    )
    mocker.patch('utils.get_db_config', return_value=mock_db_config)

    base_names = [
        "modelops_docato_fields",
        "modelops_docato_output",
        "modelops_docato_version"
    ]
    expected_physical_names = mock_db_config.table_names

    for base_name, expected_physical_name in zip(base_names, expected_physical_names):
        physical_name = get_physical_table_name(base_name)
        assert physical_name == expected_physical_name

def test_get_physical_table_name_mismatch_lengths(mocker):
    # Mock db_config with mismatched lengths
    mock_db_config = DBConfig(
        environment=Environment.PROD,
        database='edw',
        schema='pmodel',
        table_names=[
            'modelops_docato_fields',
            'modelops_docato_output'
            # Missing 'modelops_docato_version'
        ]
    )
    mocker.patch('utils.get_db_config', return_value=mock_db_config)

    with pytest.raises(ValueError) as exc_info:
        get_physical_table_name("modelops_docato_fields")
    assert "Mismatch between the number of base and physical table names" in str(exc_info.value)

def test_get_physical_table_name_order_mismatch(mocker):
    # Mock db_config with order mismatch
    mock_db_config = DBConfig(
        environment=Environment.DEV,
        database='edw',
        schema='ptap',
        table_names=[
            'u1234_modelops_docato_output',       # Swapped order
            'u1234_modelops_docato_fields',
            'u1234_modelops_docato_version'
        ]
    )
    mocker.patch('utils.get_db_config', return_value=mock_db_config)

    with pytest.raises(ValueError) as exc_info:
        get_physical_table_name("modelops_docato_fields")
    assert "Order of base and physical table names does not match" in str(exc_info.value)

def test_get_physical_table_name_base_name_not_found(mocker):
    # Mock db_config with correct table names
    mock_db_config = DBConfig(
        environment=Environment.PROD,
        database='edw',
        schema='pmodel',
        table_names=[
            'modelops_docato_fields',
            'modelops_docato_output',
            'modelops_docato_version'
        ]
    )
    mocker.patch('utils.get_db_config', return_value=mock_db_config)

    with pytest.raises(ValueError) as exc_info:
        get_physical_table_name("nonexistent_table")
    assert "Base table name 'nonexistent_table' not found in mapping" in str(exc_info.value)

def test_get_physical_table_name_table_names_not_list(mocker):
    # Mock db_config with table_names not being a list
    mock_db_config = DBConfig(
        environment=Environment.PROD,
        database='edw',
        schema='pmodel',
        table_names="not_a_list"
    )
    mocker.patch('utils.get_db_config', return_value=mock_db_config)

    with pytest.raises(TypeError) as exc_info:
        get_physical_table_name("modelops_docato_fields")
    assert "db_config.table_names must be a list" in str(exc_info.value)
