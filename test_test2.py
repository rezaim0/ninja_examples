import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date
from your_module import AAPManifestConfig  # Replace 'your_module' with the actual module name

@pytest.fixture
def temp_dir():
    """Create a temporary directory for the test."""
    dirpath = tempfile.mkdtemp()
    yield Path(dirpath)
    shutil.rmtree(dirpath)

def test_only_kfp_manifest(temp_dir):
    """Test when only kfp_manifest exists."""
    kfp_manifest_content = """
    schedule: 0 2 * * *
    python_version: 3.9
    workflow_definition: task1, task2|task3, task4
    """

    # Create kfp_manifest file
    kfp_manifest_path = temp_dir / 'kfp_manifest'
    kfp_manifest_path.write_text(kfp_manifest_content)

    # Instantiate the class
    config = AAPManifestConfig(config_path=temp_dir)

    # Get defaults
    defaults = config.get_defaults()

    # Expected defaults
    expected_defaults = {
        'execution_platform': 'Analytics Automation Platform (AAP)',
        'processing_schedule': '0 2 * * *',
        'processing_frequency': 365,  # Assuming daily execution
        'workflow_sequence': [
            'task1 -> <ADD DESCRIPTION>',
            'task2 -> <ADD DESCRIPTION>',
            'task3 -> <ADD DESCRIPTION>',
            'task4 -> <ADD DESCRIPTION>',
        ],
        'runtime': 'python 3.9'
    }

    assert defaults == expected_defaults

def test_only_aep_manifest(temp_dir):
    """Test when only aep_manifest exists."""
    aep_manifest_content = """
    schedule: 0 7 * * 1
    use_python38: true
    workflow_definition: edw-get|edh-get, data-transform, model-1|model-2|model-3, join-outputs, upload
    """

    # Create aep_manifest file
    aep_manifest_path = temp_dir / 'aep_manifest'
    aep_manifest_path.write_text(aep_manifest_content)

    # Instantiate the class
    config = AAPManifestConfig(config_path=temp_dir)

    # Get defaults
    defaults = config.get_defaults()

    # Expected defaults
    expected_defaults = {
        'execution_platform': 'Analytics Execution Platform (AEP)',
        'processing_schedule': '0 7 * * 1',
        'processing_frequency': 52,  # Assuming weekly execution
        'workflow_sequence': [
            'edw-get -> <ADD DESCRIPTION>',
            'edh-get -> <ADD DESCRIPTION>',
            'data-transform -> <ADD DESCRIPTION>',
            'model-1 -> <ADD DESCRIPTION>',
            'model-2 -> <ADD DESCRIPTION>',
            'model-3 -> <ADD DESCRIPTION>',
            'join-outputs -> <ADD DESCRIPTION>',
            'upload -> <ADD DESCRIPTION>',
        ],
        'runtime': 'python 3.8'
    }

    assert defaults == expected_defaults

def test_both_manifests_exist(temp_dir):
    """Test when both kfp_manifest and aep_manifest exist."""
    kfp_manifest_content = """
    schedule: 0 2 * * *
    python_version: 3.9
    workflow_definition: task1, task2|task3, task4
    """
    aep_manifest_content = """
    schedule: 0 7 * * 1
    use_python38: true
    workflow_definition: edw-get|edh-get, data-transform, model-1|model-2|model-3, join-outputs, upload
    """

    # Create both manifest files
    kfp_manifest_path = temp_dir / 'kfp_manifest'
    kfp_manifest_path.write_text(kfp_manifest_content)
    aep_manifest_path = temp_dir / 'aep_manifest'
    aep_manifest_path.write_text(aep_manifest_content)

    # Instantiate the class
    config = AAPManifestConfig(config_path=temp_dir)

    # Get defaults
    defaults = config.get_defaults()

    # Since kfp_manifest has precedence, we expect defaults from kfp_manifest
    expected_defaults = {
        'execution_platform': 'Analytics Automation Platform (AAP)',
        'processing_schedule': '0 2 * * *',
        'processing_frequency': 365,
        'workflow_sequence': [
            'task1 -> <ADD DESCRIPTION>',
            'task2 -> <ADD DESCRIPTION>',
            'task3 -> <ADD DESCRIPTION>',
            'task4 -> <ADD DESCRIPTION>',
        ],
        'runtime': 'python 3.9'
    }

    assert defaults == expected_defaults

def test_no_manifest_exists(temp_dir):
    """Test when neither kfp_manifest nor aep_manifest exists."""
    # Instantiate the class
    config = AAPManifestConfig(config_path=temp_dir)

    # Get defaults
    defaults = config.get_defaults()

    # Expected defaults should be empty
    expected_defaults = {}

    assert defaults == expected_defaults

def test_invalid_yaml(temp_dir, mocker):
    """Test when the manifest file contains invalid YAML."""
    kfp_manifest_content = """
    schedule: 0 2 * * *
    invalid_yaml: [unclosed_list
    """

    # Create kfp_manifest file with invalid YAML
    kfp_manifest_path = temp_dir / 'kfp_manifest'
    kfp_manifest_path.write_text(kfp_manifest_content)

    # Mock the reformat_yaml_file function
    mock_reformat = mocker.patch('your_module.reformat_yaml_file')
    mock_reformat.return_value = ({'schedule': '0 2 * * *'}, None)

    # Instantiate the class
    config = AAPManifestConfig(config_path=temp_dir)

    # Get defaults
    defaults = config.get_defaults()

    # Expected defaults after reformatting
    expected_defaults = {
        'execution_platform': 'Analytics Automation Platform (AAP)',
        'processing_schedule': '0 2 * * *',
        'processing_frequency': 365,
        'workflow_sequence': None,
        'runtime': None
    }

    assert defaults == expected_defaults
    mock_reformat.assert_called_once_with(kfp_manifest_path)

def test_process_processing_frequency(temp_dir):
    """Test the _process_processing_frequency method with various schedules."""
    # Create a manifest with a daily schedule
    kfp_manifest_content = """
    schedule: 0 0 * * *
    python_version: 3.9
    """

    kfp_manifest_path = temp_dir / 'kfp_manifest'
    kfp_manifest_path.write_text(kfp_manifest_content)

    config = AAPManifestConfig(config_path=temp_dir)
    frequency = config._process_processing_frequency()

    assert frequency == 365  # Daily execution

    # Update the manifest with a weekly schedule
    kfp_manifest_content = """
    schedule: 0 0 * * 0
    python_version: 3.9
    """

    kfp_manifest_path.write_text(kfp_manifest_content)

    config = AAPManifestConfig(config_path=temp_dir)
    frequency = config._process_processing_frequency()

    assert frequency == 52  # Weekly execution

def test_process_workflow_sequence(temp_dir):
    """Test the _process_workflow_sequence method with various workflow definitions."""
    kfp_manifest_content = """
    schedule: 0 2 * * *
    workflow_definition: task1|task2, task3|task4|task5, task6
    """

    kfp_manifest_path = temp_dir / 'kfp_manifest'
    kfp_manifest_path.write_text(kfp_manifest_content)

    config = AAPManifestConfig(config_path=temp_dir)
    workflow_sequence = config._process_workflow_sequence()

    expected_sequence = [
        'task1 -> <ADD DESCRIPTION>',
        'task2 -> <ADD DESCRIPTION>',
        'task3 -> <ADD DESCRIPTION>',
        'task4 -> <ADD DESCRIPTION>',
        'task5 -> <ADD DESCRIPTION>',
        'task6 -> <ADD DESCRIPTION>',
    ]

    assert workflow_sequence == expected_sequence

def test_replace_back():
    """Test the replace_back function."""
    from docato.core.util import replace_back

    data_with_at = {
        'key1': '__AT__value1',
        'key2': ['__AT__value2', '__AT__value3'],
        'key3': {
            'subkey1': '__AT__value4',
            'subkey2': '__AT__value5'
        }
    }

    expected_data = {
        'key1': '@value1',
        'key2': ['@value2', '@value3'],
        'key3': {
            'subkey1': '@value4',
            'subkey2': '@value5'
        }
    }

    result = replace_back(data_with_at)
    assert result == expected_data

def test_reformat_yaml_file(temp_dir, mocker):
    """Test the reformat_yaml_file function with invalid YAML."""
    from docato.shared.util import reformat_yaml_file

    invalid_yaml_content = """
    schedule: 0 2 * * *
    invalid_yaml: [unclosed_list
    """

    manifest_path = temp_dir / 'manifest'
    manifest_path.write_text(invalid_yaml_content)

    # Mock the reformat_yaml_file function
    mock_reformat = mocker.patch('docato.shared.util.reformat_yaml_file')
    mock_reformat.return_value = (None, None)

    input_data, _ = reformat_yaml_file(manifest_path)

    # Since the YAML is invalid and reformat_yaml_file returns None
    assert input_data is None
    mock_reformat.assert_called_once_with(manifest_path)
