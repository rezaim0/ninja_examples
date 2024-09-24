import re
from datetime import date
from pathlib import Path
from typing import Optional
from croniter import croniter, croniter_range
from loguru import logger
import yaml
from yaml.parser import ParserError
from docato.core.util import replace_back
from docato.shared.util import reformat_yaml_file

class AAPManifestConfig:
    def __init__(self, config_path: Path = Path("./")) -> None:
        # Paths to 'kfp_manifest' and 'aep_manifest'
        kfp_file_path = config_path / "kfp_manifest"
        aep_file_path = config_path / "aep_manifest"

        # Check which files exist
        kfp_exists = kfp_file_path.is_file()
        aep_exists = aep_file_path.is_file()

        # Determine which file to use (kfp_manifest has precedence)
        if kfp_exists:
            file_path = kfp_file_path
            self.exists = True
            self.manifest_type = 'kfp'
        elif aep_exists:
            file_path = aep_file_path
            self.exists = True
            self.manifest_type = 'aep'
        else:
            self.exists = False
            self.manifest_type = None

        # Load the file if it exists
        if self.exists:
            try:
                # YAML does not accept '@' in the content to load.
                # So we read the content first
                with open(file_path, "r") as file:
                    content = file.read()
                # Then replace the '@' with '__AT__'
                content_modified = re.sub(r"@(\w+)", r"__AT__\1", content)
                # Now we can load
                yaml_loaded = yaml.safe_load(content_modified)
                # After loading, we will have a dictionary object
                # We will need to put '@' back wherever replaced by '__AT__' before
                self.input_data = replace_back(yaml_loaded)
            except ParserError:
                self.input_data, _ = reformat_yaml_file(file_path)
            except Exception as e:
                logger.warning(f"Skipping reading {file_path}. Error: {str(e)}")
                self.exists = False
                self.input_data = None
        else:
            self.input_data = None

    def get_defaults(self):
        """Return all default values."""
        if self.exists and self.input_data:
            if self.manifest_type == 'kfp':
                # Extract values specific to kfp_manifest
                default_vals = {
                    "execution_platform": "Kubeflow Pipelines (KFP)",
                    "processing_schedule": self.input_data.get("schedule"),
                    "processing_frequency": self._process_processing_frequency(),
                    "workflow_sequence": self._process_workflow_sequence(),
                    "runtime": (
                        f"python {self.input_data.get('python_version')}"
                        if self.input_data.get("python_version")
                        else None
                    ),
                }
            else:  # aep_manifest
                # Extract values specific to aep_manifest
                default_vals = {
                    "execution_platform": "Analytics Execution Platform (AEP)",
                    "processing_schedule": self.input_data.get("schedule"),
                    "processing_frequency": self._process_processing_frequency(),
                    "workflow_sequence": self._process_workflow_sequence(),
                    "runtime": (
                        "python 3.8" if self.input_data.get("use_python38") else None
                    ),
                }
            # Remove keys where we are unable to determine default values
            default_vals = {k: v for (k, v) in default_vals.items() if v is not None}
        else:
            default_vals = {}
        return default_vals

    def _process_workflow_sequence(self):
        """Convert 'workflow_definition' into 'workflow_sequence'."""
        workflow_definition = self.input_data.get("workflow_definition")
        if workflow_definition:
            # Stages are separated by commas
            stages = [stage.strip() for stage in workflow_definition.split(',')]
            workflow_sequence = []
            for stage in stages:
                # Tasks within stages are separated by '|'
                tasks = [task.strip() for task in stage.split('|')]
                for task in tasks:
                    workflow_sequence.append(f"{task} -> <ADD DESCRIPTION>")
            return workflow_sequence
        else:
            return None

    def _process_processing_frequency(self):
        """Convert 'schedule' into 'processing_frequency'."""
        schedule = self.input_data.get("schedule")
        if schedule and croniter.is_valid(schedule):
            cnt = sum(
                1
                for _ in croniter_range(
                    date(2023, 1, 1), date(2023, 12, 31), schedule
                )
            )
            return cnt
        else:
            return None
