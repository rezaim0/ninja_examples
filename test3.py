import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date
import textwrap
from your_module import AAPManifestConfig  # Replace 'your_module' with the actual module name

@pytest.fixture
def temp_dir():
    """Create a temporary directory for the test."""
    dirpath = tempfile.mkdtemp()
    yield Path(dirpath)
    shutil.rmtree(dirpath)

def test_only_kfp_manifest(temp_dir):
    """Test when only kfp_manifest exists."""
    kfp_manifest_content = textwrap.dedent("""
    schedule: 0 2 * * *
    python_version: 3.9
    workflow_definition: task1, task2|task3, task4
    """)

    # Create kfp_manifest file
    kfp_manifest_path = temp_dir / 'kfp_manifest'
    kfp_manifest_path.write_text(kfp_manifest_content)

    # Instantiate the class
    config = AAPManifestConfig(config_path=temp_dir)
    assert config.exists is True
    assert config.manifest_type == 'kfp'

    # Get defaults
    defaults = config.get_defaults()

    # Expected defaults
    expected_defaults = {
        'execution_platform': 'kubeflow pipelines (KFP)',  # Updated line
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
