from jinja2 import Template
import yaml

# Read YAML data
with open('company_data.yaml') as file:
    data = yaml.load(file, Loader=yaml.FullLoader)

# Read template
with open('template_company.md') as file:
    template_str = file.read()

# Jinja template
template = Template(template_str)

# Render template
output = template.render(company=data['company'])

# Write output to file
with open('output.md', 'w') as file:
    file.write(output)

print("Template rendered successfully. Output saved in 'output.md'")
