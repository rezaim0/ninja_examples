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

# 1 Testing Load_config() function

def test_load_config_success(mocker: MockerFixture):
    """
    Test Case: Successful Loading of Configuration
    """
    # Mock open function to return a sample YAML content
    sample_yaml = """
    default:
      table_names:
        - modelops_docato_fields
        - modelops_docato_output
        - modelops_docato_version
    local:
      <<: *default
      database: local.db
      schema: null
    
    staging:
      <<: *default
      database: edw
      schema: ptap


    dev:
      <<: *default
      database: edw
      schema: ptap
    """
    mocker.patch('builtins.open', mocker.mock_open(read_data=sample_yaml))
    mocker.patch('yaml.safe_load', side_effect=yaml.safe_load)

    config = load_config("dummy/path/config.yaml")
    assert config['local']['database'] == 'local.db'
    assert config['dev']['schema'] == 'ptap'
    assert config['default']['table_names'] == [
        'modelops_docato_fields',
        'modelops_docato_output',
        'modelops_docato_version',
    ]

# Edge Case: File Not Found
def test_load_config_file_not_found(mocker: MockerFixture):
    # Mock open to raise FileNotFoundError
    mocker.patch('builtins.open', side_effect=FileNotFoundError)

    with pytest.raises(FileNotFoundError):
        load_config("nonexistent/config.yaml")

# 2. Testing get_user_id() Function

def test_get_user_id_valid(mocker: MockerFixture):
    """
    # Test Case: Valid NB_PREFIX with Correct user_id
    """
    # Set NB_PREFIX environment variable
    mocker.patch.dict(os.environ, {'NB_PREFIX': '/user/notebook/u1234-notebook'})
    user_id = get_user_id()
    assert user_id == 'u1234'


def test_get_user_id_nb_prefix_not_set(mocker: MockerFixture):
    """
    Test Case: NB_PREFIX Not Set
    """
    
    # Ensure NB_PREFIX is not set
    mocker.patch.dict(os.environ, {}, clear=True)
    # Mock logger to capture error messages
    mock_logger = mocker.patch('config.logger')

    user_id = get_user_id()
    assert user_id is None
    mock_logger.error.assert_called_with("NB_PREFIX environment variable is not set.")


def test_get_user_id_insufficient_parts(mocker: MockerFixture):
    """
    Test Case: NB_PREFIX with Insufficient Parts
    """
    mocker.patch.dict(os.environ, {'NB_PREFIX': '/user/notebook'})
    mock_logger = mocker.patch('config.logger')

    user_id = get_user_id()
    assert user_id is None
    mock_logger.error.assert_called_with("NB_PREFIX does not contain enough parts to extract user ID.")

def test_get_user_id_wrong_length(mocker: MockerFixture):
    """
    Test Case: user_id Not 5 Characters
    """
    mocker.patch.dict(os.environ, {'NB_PREFIX': '/user/notebook/u12-notebook'})
    mock_logger = mocker.patch('config.logger')

    user_id = get_user_id()
    assert user_id is None
    mock_logger.error.assert_called_with("The user_id 'u12' is not made of five characters.")


def test_get_user_id_does_not_start_with_u(mocker: MockerFixture):
    """
    Test Case: user_id Does Not Start with 'u'
    """
    mocker.patch.dict(os.environ, {'NB_PREFIX': '/user/notebook/12345-notebook'})
    mock_logger = mocker.patch('config.logger')

    user_id = get_user_id()
    assert user_id is None
    mock_logger.error.assert_called_with("The user_id '12345' does not start with 'u'.")


def test_get_user_id_exception(mocker: MockerFixture):
   """
   Test Case: Exception Occurs
   """
    # Mock os.getenv to raise an exception
    mocker.patch('os.getenv', side_effect=Exception('Unexpected error'))
    mock_logger = mocker.patch('config.logger')

    user_id = get_user_id()
    assert user_id is None
    mock_logger.exception.assert_called_once()



# 3. Testing get_db_config() Function


mock_config = {
    'default': {
        'table_names': [
            'modelops_docato_fields',
            'modelops_docato_output',
            'modelops_docato_version',
        ],
    },
    'local': {
        'database': 'local.db',
        'schema': None,
        'table_names': [
            'modelops_docato_fields',
            'modelops_docato_output',
            'modelops_docato_version',
        ],
    },
    'dev': {
        'database': 'edw',
        'schema': 'ptap',
        'table_names': [
            'modelops_docato_fields',
            'modelops_docato_output',
            'modelops_docato_version',
        ],
    },
    'prod': {
        'database': 'edw',
        'schema': 'pmodel',
        'table_names': [
            'modelops_docato_fields',
            'modelops_docato_output',
            'modelops_docato_version',
        ],
    },
}

#Test Case: Local Environment
def test_get_db_config_local(mocker: MockerFixture):
    mocker.patch('config.load_config', return_value=mock_config)
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

# Test Case: Dev Environment with Valid User ID
def test_get_db_config_dev_valid_userid(mocker: MockerFixture):
    mocker.patch('config.load_config', return_value=mock_config)
    mocker.patch('config.get_user_id', return_value='u1234')
    mocker.patch.dict(os.environ, {'AEP_ENV': 'dev'}, clear=True)

    db_config = get_db_config()
    expected_table_names = [
        'u1234_modelops_docato_fields',
        'u1234_modelops_docato_output',
        'u1234_modelops_docato_version',
    ]
    assert db_config.environment == Environment.DEV
    assert db_config.database == 'edw'
    assert db_config.schema == 'ptap'
    assert db_config.table_names == expected_table_names

# Test Case: Dev Environment with No User ID
def test_get_db_config_dev_no_userid(mocker: MockerFixture):
    mocker.patch('config.load_config', return_value=mock_config)
    mocker.patch('config.get_user_id', return_value=None)
    mocker.patch.dict(os.environ, {'AEP_ENV': 'dev'}, clear=True)

    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    assert "USERID could not be extracted for dev environment." in str(exc_info.value)

#Test Case: Prod Environment


def test_get_db_config_prod(mocker: MockerFixture):
    mocker.patch('config.load_config', return_value=mock_config)
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

#Test Case: Invalid AEP_ENV Value

def test_get_db_config_invalid_env(mocker: MockerFixture):
    mocker.patch.dict(os.environ, {'AEP_ENV': 'invalid_env'}, clear=True)

    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    assert "Invalid environment specified in AEP_ENV: invalid_env" in str(exc_info.value)


#Test Case: Missing Environment in Config

def test_get_db_config_missing_env_in_config(mocker: MockerFixture):
    # Remove 'dev' configuration from mock_config
    incomplete_config = mock_config.copy()
    incomplete_config.pop('dev')
    mocker.patch('config.load_config', return_value=incomplete_config)
    mocker.patch.dict(os.environ, {'AEP_ENV': 'dev'}, clear=True)

    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    assert "No configuration found for environment: dev" in str(exc_info.value)

# Test Case: Missing table_names in Config

def test_get_db_config_missing_table_names(mocker: MockerFixture):
    # Remove 'table_names' from 'dev' configuration
    incomplete_config = mock_config.copy()
    incomplete_config['dev'] = {
        'database': 'edw',
        'schema': 'ptap',
        # 'table_names' key is missing
    }
    mocker.patch('config.load_config', return_value=incomplete_config)
    mocker.patch('config.get_user_id', return_value='u1234')
    mocker.patch.dict(os.environ, {'AEP_ENV': 'dev'}, clear=True)

    db_config = get_db_config()
    # Since table_names default to [], the prefixed list should be empty
    assert db_config.table_names == []
