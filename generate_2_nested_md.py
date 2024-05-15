import yaml
from jinja2 import Environment, FileSystemLoader

# Load the YAML data
with open('data_2_nested.yaml', 'r') as file:
    data = yaml.safe_load(file)

# Set up the Jinja environment
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('2_nested_template.md')

# Render the template with the data
output = template.render(data)

# Output the result to a file
output_file = 'output_2_nested.md'
with open(output_file, 'w') as file:
    file.write(output)

print(f"Markdown file generated: {output_file}")
