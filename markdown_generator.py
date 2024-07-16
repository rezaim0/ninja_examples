import os
import yaml
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from typing import Any, Dict, Generator, Tuple, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarkdownGenerator:
    """
    A class for generating Markdown files from YAML data using Jinja2 templates.

    This class processes YAML files in a specified directory, renders them using
    a Jinja2 template, and outputs the result as Markdown files.
    """

    YAML_EXTENSION = '.yaml'
    MARKDOWN_EXTENSION = '.md'

    def __init__(self, metrics_dir: str, template_path: str):
        """
        Initialize the MarkdownGenerator with the directory containing YAML files and the Jinja2 template path.

        Args:
            metrics_dir (str): Directory containing YAML files.
            template_path (str): Path to the Jinja2 template file.
        """
        self.metrics_dir = Path(metrics_dir)
        self.template_path = Path(template_path)
        self.env = Environment(loader=FileSystemLoader(self.template_path.parent))
        self.template = self._load_template()

    def _load_template(self) -> Any:
        """
        Load the Jinja2 template.

        Returns:
            Any: Jinja2 template object.

        Raises:
            TemplateNotFound: If the template file is not found.
            PermissionError: If there's a permission error while loading the template.
            Exception: For any other unexpected errors during template loading.
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
            logging.error(f"Unexpected error loading template: {e}")
            raise

    def process_yaml_file(self, yaml_file_path: Path) -> Dict[str, Any]:
        """
        Process a single YAML file and load its content.

        Args:
            yaml_file_path (Path): Path to the YAML file.

        Returns:
            Dict[str, Any]: Parsed content of the YAML file.

        Raises:
            FileNotFoundError: If the YAML file is not found.
            yaml.YAMLError: If there's an error parsing the YAML file.
            Exception: For any other unexpected errors during YAML file processing.
        """
        try:
            with open(yaml_file_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logging.error(f"YAML file not found: {yaml_file_path}")
            raise
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML file: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error processing YAML file: {e}")
            raise

    def render_markdown(self, data: Dict[str, Any]) -> str:
        """
        Render Markdown content from the provided data using the Jinja2 template.

        Args:
            data (Dict[str, Any]): Data to be rendered in the template.

        Returns:
            str: Rendered Markdown content.
        """
        try:
            return self.template.render(data)
        except Exception as e:
            logging.error(f"Error rendering markdown: {e}")
            raise

    def write_output(self, output: str, output_path: Path):
        """
        Write the rendered output to a file.

        Args:
            output (str): Rendered Markdown content.
            output_path (Path): Path to the output file.

        Raises:
            IOError: If there's an error writing to the output file.
        """
        try:
            with open(output_path, 'w') as file:
                file.write(output)
        except IOError as e:
            logging.error(f"Error writing output to file: {e}")
            raise

    def generate_markdown_files(self) -> Generator[Tuple[Path, Path], None, None]:
        """
        Generate Markdown files from YAML files in the metrics directory.

        Yields:
            Generator[Tuple[Path, Path], None, None]: A generator yielding tuples of
            the processed YAML file path and the generated Markdown file path.
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

        Returns:
            Tuple[List[Tuple[Path, Path]], List[Path]]: A tuple containing two lists:
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
