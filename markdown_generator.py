#####################################################################################
############################### This is Iteration 2 ###############################################
####################################################################################
import os
import yaml
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from typing import Any, Dict, Generator, Tuple, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarkdownGenerator:
    YAML_EXTENSION = '.yaml'
    MARKDOWN_EXTENSION = '.md'

    def __init__(self, metrics_dir: str, template_path: str):
        """
        Initialize the MarkdownGenerator with the directory containing YAML files and the Jinja2 template path.

        :param metrics_dir: Directory containing YAML files.
        :param template_path: Path to the Jinja2 template file.
        """
        self.metrics_dir = Path(metrics_dir)
        self.template_path = Path(template_path)
        self.env = Environment(loader=FileSystemLoader(self.template_path.parent))
        self.template = self._load_template()

    def _load_template(self) -> Any:
        """
        Load the Jinja2 template.

        :return: Jinja2 template object.
        :raises TemplateNotFound: If the template file is not found.
        """
        try:
            template_name = self.template_path.name
            return self.env.get_template(template_name)
        except TemplateNotFound:
            logging.error(f"Template not found: {self.template_path}")
            raise
        except PermissionError as e:
            logging.error(f"Permission error loading template: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error loading template: {type(e).__name__}: {e}")
            raise

    def process_yaml_file(self, yaml_file_path: Path) -> Dict[str, Any]:
        """
        Process a YAML file and return its content as a dictionary.

        :param yaml_file_path: Path to the YAML file.
        :return: Dictionary containing YAML file content.
        :raises yaml.YAMLError: If there is an error in processing the YAML file.
        """
        try:
            with open(yaml_file_path, 'r') as yaml_file:
                return yaml.safe_load(yaml_file)
        except yaml.YAMLError as e:
            logging.error(f"YAML error processing file {yaml_file_path}: {e}")
            raise
        except Exception as e:
            logging.error(f"Error processing YAML file {yaml_file_path}: {e}")
            raise

    def render_markdown(self, data: Dict[str, Any]) -> str:
        """
        Render Markdown from data using the Jinja2 template.

        :param data: Data to be rendered in the template.
        :return: Rendered Markdown string.
        :raises Exception: If there is an error in rendering the Markdown.
        """
        try:
            return self.template.render(data)
        except Exception as e:
            logging.error(f"Error rendering Markdown: {e}")
            raise

    def write_output(self, output: str, output_file_path: Path) -> None:
        """
        Write rendered Markdown to a file.

        :param output: Rendered Markdown content.
        :param output_file_path: Path to the output file.
        :raises Exception: If there is an error in writing to the file.
        """
        try:
            with open(output_file_path, 'w') as markdown_file:
                markdown_file.write(output)
        except Exception as e:
            logging.error(f"Error writing to file {output_file_path}: {e}")
            raise

    def generate_markdown_files(self) -> Generator[Tuple[Path, Path], None, None]:
        """
        Generate Markdown files from YAML files in the metrics directory.

        :yield: Tuple containing paths to the processed YAML file and the generated Markdown file.
        """
        for subdir, _, files in os.walk(self.metrics_dir):
            yaml_files = [f for f in files if f.endswith(self.YAML_EXTENSION)]
            for file in yaml_files[:1]:  # Process only the first YAML file found in each directory
                yaml_file_path = Path(subdir) / file
                try:
                    data = self.process_yaml_file(yaml_file_path)
                    output = self.render_markdown(data)
                    markdown_file_path = Path(subdir) / f'output{self.MARKDOWN_EXTENSION}'
                    self.write_output(output, markdown_file_path)
                    logging.info(f'Rendered Markdown for {yaml_file_path} to {markdown_file_path}')
                    yield yaml_file_path, markdown_file_path
                except Exception as e:
                    logging.error(f"Failed to process {yaml_file_path}: {e}")

    def check_existing_markdown_files(self) -> Tuple[List[Tuple[Path, Path]], List[Path]]:
        """
        Check for existing Markdown files in the metrics directory.

        :return: A tuple containing two lists:
                 1. List of tuples with subdirectory path and markdown file path for directories containing markdown files.
                 2. List of subdirectory paths for directories that do not contain markdown files.
        """
        subdirs_with_markdown = []
        subdirs_without_markdown = []
        
        for subdir, _, files in os.walk(self.metrics_dir):
            markdown_files = [f for f in files if f.endswith(self.MARKDOWN_EXTENSION)]
            if markdown_files:
                markdown_file_path = Path(subdir) / markdown_files[0]  # Assuming one markdown file per subdir
                subdirs_with_markdown.append((Path(subdir), markdown_file_path))
            else:
                subdirs_without_markdown.append(Path(subdir))
        
        return subdirs_with_markdown, subdirs_without_markdown

