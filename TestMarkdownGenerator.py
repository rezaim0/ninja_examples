
############################################################################
### Second Iteration ############################
import unittest
from unittest.mock import patch, mock_open, MagicMock, call
from pathlib import Path
import tempfile
import os
import shutil
import yaml
from markdown_generator import MarkdownGenerator

class TestMarkdownGenerator(unittest.TestCase):
    """
    Unit tests for the MarkdownGenerator class.

    These tests cover the following functionalities:
    - Initialization of the MarkdownGenerator.
    - Processing YAML files.
    - Loading Jinja2 templates.
    - Rendering Markdown content.
    - Writing output to files.
    - Generating Markdown files from YAML files.
    - Checking for existing Markdown files.
    - Handling errors during YAML file processing.
    - Generating Markdown files with complex data structures.
    """
    def setUp(self):
        """
        Set up the test environment before each test method is run.

        This method creates a temporary directory structure and files needed for testing.
        """
        self.temp_dir = Path(tempfile.mkdtemp())
        self.metrics_dir = self.temp_dir / 'metrics'
        self.metrics_dir.mkdir(exist_ok=True)
        
        self.template_content = "{{ metric_inputs.key }}"
        self.template_path = self.temp_dir / 'template.md'
        self.template_path.write_text(self.template_content)
        
        self.yaml_file_content = {'key': 'value'}

    def tearDown(self):
        """
        Clean up the test environment after each test method has run.

        This method removes the temporary directory and all its contents.
        """
        shutil.rmtree(self.temp_dir)

    def test_markdown_generator_initialization(self):
        """
        Test the initialization of the MarkdownGenerator class.

        This test verifies that the MarkdownGenerator is correctly initialized
        with the provided metrics directory and template path.
        """
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        self.assertEqual(generator.metrics_dir, self.metrics_dir)
        self.assertEqual(generator.template_path, self.template_path)

    @patch("builtins.open", new_callable=mock_open, read_data="key: value")
    @patch("yaml.safe_load", return_value={'key': 'value'})
    def test_process_yaml_file(self, mock_yaml_load, mock_open):
        """
        Test the process_yaml_file method of MarkdownGenerator.

        This test verifies that a YAML file is correctly processed and its content
        is returned as a dictionary.
        """
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        data = generator.process_yaml_file(self.metrics_dir / "test_file.yaml")
        self.assertEqual(data, self.yaml_file_content)

    @patch("builtins.open", new_callable=mock_open, read_data="{{ metric_inputs.key }}")
    @patch("jinja2.Environment.get_template")
    def test_load_template(self, mock_get_template, mock_open):
        """
        Test the _load_template method of MarkdownGenerator.

        This test ensures that the Jinja2 template is correctly loaded during
        the initialization of MarkdownGenerator.
        """
        mock_template = MagicMock()
        mock_get_template.return_value = mock_template
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        self.assertEqual(generator.template, mock_template)

    def test_render_markdown(self):
        """
        Test the render_markdown method of MarkdownGenerator.

        This test verifies that the Markdown content is correctly rendered
        using the loaded Jinja2 template and provided data.
        """
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        generator.template = MagicMock()
        generator.template.render.return_value = "value"
        output = generator.render_markdown(self.yaml_file_content)
        self.assertEqual(output, "value")

    @patch("builtins.open", new_callable=mock_open)
    def test_write_output(self, mock_open):
        """
        Test the write_output method of MarkdownGenerator.

        This test ensures that the rendered Markdown content is correctly
        written to the specified output file.
        """
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        output_path = self.metrics_dir / "output.md"
        generator.write_output("output content", output_path)
        mock_open().write.assert_called_once_with("output content")

    @patch("os.walk")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("jinja2.Environment.get_template")
    def test_generate_markdown_files(self, mock_get_template, mock_yaml_load, mock_open, mock_os_walk):
        """
        Test the generate_markdown_files method of MarkdownGenerator.

        This test verifies the entire process of generating Markdown files from YAML files,
        including walking through directories, processing YAML files, rendering Markdown,
        and writing output files.
        """
        mock_yaml_load.return_value = self.yaml_file_content
        mock_template = MagicMock()
        mock_template.render.return_value = "rendered content"
        mock_get_template.return_value = mock_template
        
        mock_os_walk.return_value = [
            (str(self.metrics_dir), [], ['file1.yaml']),
            (str(self.metrics_dir / 'subdir'), [], ['file2.yaml']),
        ]
        
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        result = list(generator.generate_markdown_files())
        
        expected_output_paths = [
            (self.metrics_dir / 'file1.yaml', self.metrics_dir / 'output.md'),
            (self.metrics_dir / 'subdir' / 'file2.yaml', self.metrics_dir / 'subdir' / 'output.md'),
        ]
        
        self.assertEqual(result, expected_output_paths)
        
        mock_open.assert_has_calls([
            call(self.metrics_dir / 'file1.yaml', 'r'),
            call(self.metrics_dir / 'output.md', 'w'),
            call(self.metrics_dir / 'subdir' / 'file2.yaml', 'r'),
            call(self.metrics_dir / 'subdir' / 'output.md', 'w'),
        ], any_order=True)

    @patch("builtins.open", new_callable=mock_open, read_data="invalid: yaml: content")
    @patch("yaml.safe_load")
    def test_process_invalid_yaml_file(self, mock_yaml_load, mock_open):
        """
        Test the process_yaml_file method with an invalid YAML file.

        This test ensures that a yaml.YAMLError is raised when attempting to process
        an invalid YAML file.
        """
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        with self.assertRaises(yaml.YAMLError):
            generator.process_yaml_file(self.metrics_dir / "invalid_file.yaml")

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("yaml.safe_load", return_value=None)
    def test_process_empty_yaml_file(self, mock_yaml_load, mock_open):
        """
        Test the process_yaml_file method with an empty YAML file.

        This test verifies that processing an empty YAML file returns None.
        """
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        data = generator.process_yaml_file(self.metrics_dir / "empty_file.yaml")
        self.assertIsNone(data)

    @patch("builtins.open", new_callable=mock_open)
    def test_write_output_permission_error(self, mock_open):
        """
        Test the write_output method when a PermissionError occurs.

        This test ensures that a PermissionError is raised when attempting to write
        to a file without proper permissions.
        """
        def side_effect(*args, **kwargs):
            if 'w' in args:
                raise PermissionError("Permision denied")
            else:
                return mock_open.return_value
        
        mock_open.side_effect = side_effect
        
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)

        with self.assertRaises(PermissionError):
            generator.write_output("output content", self.metrics_dir / "output.md")

    @patch("os.walk")
    def test_check_existing_markdown_files(self, mock_os_walk):
        """
        Test checking for existing Markdown files.

        This test verifies if the check_existing_markdown_files method correctly identifies
        directories containing Markdown files and those without.
        """
        # creating subdirectories and markdown files
        mock_os_walk.return_value = [
            (str(self.metrics_dir / 'subdir1'), [], ['file1.yaml', 'file2.md']),
            (str(self.metrics_dir / 'subdir2'), [], ['file3.yaml']),
            (str(self.metrics_dir / 'subdir3'), [], ['file4.md']),
        ]
        
        # Initialise the MarkdownGenerator
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        
        # check for existing Markdown files
        with_markdown, without_markdown = generator.check_existing_markdown_files()
        
        # Expected Results
        expected_with_markdown = [
            (self.metrics_dir / 'subdir1', self.metrics_dir / 'subdir1' / 'file2.md'),
            (self.metrics_dir / 'subdir3', self.metrics_dir / 'subdir3' / 'file4.md')
        ]
        expected_without_markdown = [
            self.metrics_dir / 'subdir2'
        ]
        
        self.assertEqual(with_markdown, expected_with_markdown)
        self.assertEqual(without_markdown, expected_without_markdown)

    @patch("builtins.open", new_callable=mock_open)
    @patch("jinja2.Environment.get_template")
    def test_process_yaml_file_not_found(self, mock_get_template, mock_open):
        """
        Test handling of FileNotFoundError during YAML file processing.

        This test checks if the process_yaml_file method correctly handles the scenario
        when a YAML file is not found.
        """
        mock_get_template.return_value = MagicMock()
        
        # Set up the open mock to raise FileNotFoundError only for the YAML file
        def side_effect(*args, **kwargs):
            if isinstance(args[0], Path):
                path_str = str(args[0])
                if str(self.metrics_dir) in path_str and path_str.endswith('.yaml'):
                    raise FileNotFoundError()
            return mock_open.return_value
        
        mock_open.side_effect = side_effect

        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        
        with self.assertRaises(FileNotFoundError):
            generator.process_yaml_file(self.metrics_dir / "nonexistent.yaml")

    @patch("os.walk")
    def test_generate_markdown_files_empty_directory(self, mock_os_walk):
        """
        Test generating Markdown files when the directory is empty.

        This test verifies if the generate_markdown_files method correctly handles
        the scenario when the metrics directory is empty.
        """
        mock_os_walk.return_value = [(str(self.metrics_dir), [], [])]
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        result = list(generator.generate_markdown_files())
        self.assertEqual(result, [])

    def test_render_markdown_complex_data(self):
        """
        Test rendering Markdown with complex data structures.

        This test checks if the render_markdown method correctly processes and renders
        complex data structures using the Jinja2 template.
        """
        complex_data = {
            "key1": {"nested_key": "value"},
            "key2": [1, 2, 3],
            "key3": None
        }
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        generator.template = MagicMock()
        generator.render_markdown(complex_data)
        generator.template.render.assert_called_once_with(complex_data)

if __name__ == "__main__":
    unittest.main()
