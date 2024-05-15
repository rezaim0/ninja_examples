import yaml
from jinja2 import Environment, FileSystemLoader

# Load the YAML data
with open('data_3_layer1.yaml', 'r') as file:
    data = yaml.safe_load(file)

# Set up the Jinja environment
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('template_3_layer_1.md')

# Render the template with the data
output = template.render(data)

# Output the result to a file
output_file = 'output_3layer_1.md'
with open(output_file, 'w') as file:
    file.write(output)

print(f"Markdown file generated: {output_file}")
