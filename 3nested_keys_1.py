# Importing necessary libraries
import yaml
from jinja2 import Environment, FileSystemLoader

# ## YAML Input (supermarket.yaml)
# Here is the YAML structure for our supermarket list.
supermarket_yaml_data = """
food:  
  fruits: 
    citrics: oranges  
    tropical: 
      type1: bananas
      type2: pineapples
"""
# Writing the YAML data to a file for demonstration
with open('supermarket.yaml', 'w') as file:
    file.write(supermarket_yaml_data)

# ## Python Equivalent
# The Python equivalent of the above YAML structure is:
# data = {
#     "food": {
#         "fruits": {
#             "citrics": "oranges",
#             "tropical": {
#                 "type1": "bananas",
#                 "type2": "pineapples"
#             }
#         }
#     }
# }

# ## Jinja Template (template_supermarket.md)
# Here is a Jinja template to render this data into a Markdown format.
supermarket_template = """
<!-- template_supermarket.md -->
# Supermarket List

## Food

### Fruits

#### Citrics
- {{ food.fruits.citrics }}

#### Tropical
- {{ food.fruits.tropical.type1 }}
- {{ food.fruits.tropical.type2 }}
"""
# Writing the Jinja template to a file for demonstration
with open('template_supermarket.md', 'w') as file:
    file.write(supermarket_template)

# ## Python Script to Render the Template
# Now, let's write a Python script to load the YAML data, render the template, and output the result as a Markdown file.
with open('supermarket.yaml', 'r') as file:
    data = yaml.safe_load(file)

# Set up the Jinja environment
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('template_supermarket.md')

# Render the template with the data
output = template.render(data)

# Output the result to a file
output_file = 'output_supermarket.md'
with open(output_file, 'w') as file:
    file.write(output)

print(f"Markdown file generated: {output_file}")

# ## Resulting Markdown (output_supermarket.md)
# The rendered Markdown file should look like this:
output_supermarket_md = """
# Supermarket List

## Food

### Fruits

#### Citrics
- oranges

#### Tropical
- bananas
- pineapples
"""
print(output_supermarket_md)
