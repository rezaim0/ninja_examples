
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

    def setUp(self):
        # Create temporary directory and file
        self.temp_dir = tempfile.mkdtemp()
        self.metrics_dir = Path(self.temp_dir) / 'metrics'
        self.metrics_dir.mkdir(exist_ok=True)
        
        # Create a temporary template file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as temp_file:
            temp_file.write("{{ metric_inputs.key }}")
            self.template_path = Path(temp_file.name)
        
        self.yaml_file_content = {'key': 'value'}

    def tearDown(self):
        # Clean up temporary files and directories
        shutil.rmtree(self.temp_dir)
        if self.template_path.exists():
            os.unlink(self.template_path)

    @patch("builtins.open", new_callable=mock_open, read_data="key: value")
    @patch("yaml.safe_load", return_value={'key': 'value'})
    def test_process_yaml_file(self, mock_yaml_load, mock_open):
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        data = generator.process_yaml_file(self.metrics_dir / "test_file.yaml")
        self.assertEqual(data, self.yaml_file_content)
    
    @patch("builtins.open", new_callable=mock_open, read_data="{{ metric_inputs.key }}")
    @patch("jinja2.Environment.get_template")
    def test_load_template(self, mock_get_template, mock_open):
        mock_template = MagicMock()
        mock_get_template.return_value = mock_template
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        self.assertEqual(generator.template, mock_template)
    
    def test_render_markdown(self):
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        generator.template = MagicMock()
        generator.template.render.return_value = "value"
        output = generator.render_markdown(self.yaml_file_content)
        self.assertEqual(output, "value")
    
    @patch("builtins.open", new_callable=mock_open)
    def test_write_output(self, mock_open):
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        output_path = self.metrics_dir / "output.md"
        generator.write_output("output content", output_path)
        mock_open().write.assert_called_once_with("output content")
    
    @patch("os.walk")
    @patch("builtins.open", new_callable=mock_open, read_data="key: value")
    @patch("yaml.safe_load")
    @patch("jinja2.Environment.get_template")
    @patch("markdown_generator.MarkdownGenerator.write_output")
    def test_generate_markdown_files(self, mock_write_output, mock_get_template, mock_yaml_load, mock_open, mock_os_walk):
        mock_yaml_load.return_value = {'key': 'value'}
        mock_template = MagicMock()
        mock_template.render.return_value = "rendered content"
        mock_get_template.return_value = mock_template
        
        # Mocking os.walk to simulate directory structure
        mock_os_walk.return_value = [
            (str(self.metrics_dir / 'subdir1'), [], ['file1.yaml', 'file2.txt']),
            (str(self.metrics_dir / 'subdir2'), [], ['file3.yaml', 'file4.md', 'file4.yaml']),
        ]
        
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        result = list(generator.generate_markdown_files())
        
        # Expected output paths for the YAML files
        expected_output_paths = [
            (self.metrics_dir / 'subdir1' / 'file1.yaml', self.metrics_dir / 'subdir1' / 'output.md'),
            (self.metrics_dir / 'subdir2' / 'file3.yaml', self.metrics_dir / 'subdir2' / 'output.md'),
        ]
        
        # Ensure the correct tuples are yielded
        self.assertEqual(result, expected_output_paths)
        
        # Ensure write_output is called with the correct arguments
        calls = [call("rendered content", path) for _, path in expected_output_paths]
        mock_write_output.assert_has_calls(calls, any_order=True)
        
        # Ensure the correct files are processed
        mock_yaml_load.assert_called_with(mock_open())

    @patch("builtins.open", new_callable=mock_open, read_data="key: value")
    @patch("yaml.safe_load", return_value={'key': 'value'})
    def test_process_invalid_yaml_file(self, mock_yaml_load, mock_open):
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        with self.assertRaises(yaml.YAMLError):
            generator.process_yaml_file(self.metrics_dir / "invalid_file.yaml")

    @patch("builtins.open", new_callable=mock_open, read_data="key: value")
    @patch("yaml.safe_load", return_value=None)
    def test_process_empty_yaml_file(self, mock_yaml_load, mock_open):
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        data = generator.process_yaml_file(self.metrics_dir / "empty_file.yaml")
        self.assertIsNone(data)
   
    @patch("builtins.open", new_callable=mock_open)
    def test_write_output_permission_error(self, mock_open):
        # Prepare to raise PermissionError only on the specific open call for writing output
        def side_effect(*args, **kwargs):
            if 'w' in args:
                raise PermissionError("Permission denied")
            else:
                return mock_open.return_value
        
        mock_open.side_effect = side_effect
        
        generator = MarkdownGenerator(str(self.metrics_dir), str(self.template_path))
        
        with self.assertRaises(PermissionError):
            generator.write_output("output content", self.metrics_dir / "output.md")
    
    @patch("os.walk")
    def test_check_existing_markdown_files(self, mock_os_walk):
        # Mocking os.walk to simulate directory structure
        mock_os_walk.return_value = [
            (str(self.metrics_dir / 'subdir1'), [], ['file1.yaml', 'file2.md']),
            (str(self.metrics_dir / 'subdir2'), [], ['file3.yaml']),
            (str(self.metrics_dir / 'subdir3'), [], ['file4.md']),
        ]
        
        generator = MarkdownGenerator(self.metrics_dir, self.template_path)
        with_markdown, without_markdown = generator.check_existing_markdown_files()
        
        # Expected results
        expected_with_markdown = [
            (self.metrics_dir / 'subdir1', self.metrics_dir / 'subdir1' / 'file2.md'),
            (self.metrics_dir / 'subdir3', self.metrics_dir / 'subdir3' / 'file4.md')
        ]
        expected_without_markdown = [
            self.metrics_dir / 'subdir2'
        ]
        
        # Assertions
        self.assertEqual(with_markdown, expected_with_markdown)
        self.assertEqual(without_markdown, expected_without_markdown)

if __name__ == "__main__":
    unittest.main()

