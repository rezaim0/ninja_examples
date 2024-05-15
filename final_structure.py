
# # Importing necessary libraries
# import yaml
# from jinja2 import Environment, FileSystemLoader

# # ## YAML Input
# # the YAML structure for Star Wars conversation.
# supermarket_yaml_data = """
# title: Star Wars: A Humorous Conversation
# author: George Lucas (Parody)
# date: 2024-05-15
# sections:
#   - title: Introduction
#     content: Luke: I've got a bad feeling about this...
#     subsections:
#       - title: Background
#         content: Obi-Wan: Trust the Force, Luke.
#       - title: Scope
#         content: Darth Vader: I find your lack of faith disturbing.
#   - title: Main Content
#     content: Luke: What’s the main content, Master?
#     subsections:
#       - title: Details
#         points:
#           - point: Use the Force, Luke!
#           - point: That’s no moon, it’s a space station.
#       - title: Analysis
#         points:
#           - point: The Force is strong with this one.
#           - point: You underestimate the power of the Dark Side.
#   - title: Conclusion
#     content: Obi-Wan: The Force will be with you, always.
#     acknowledgements:
#       - name: Dave
#         contribution: Being the chosen one.
#       - name: Eve
#         contribution: Keeping balance to the Force.
# """
# # Writing the YAML data to a file for demonstration
# with open('supermarket.yaml', 'w') as file:
#     file.write(supermarket_yaml_data)

# # ## Python Equivalent
# # The Python equivalent of the above YAML structure is:
# # data = {
# #     "title": "Star Wars: A Humorous Conversation",
# #     "author": "George Lucas (Parody)",
# #     "date": "2024-05-15",
# #     "sections": [
# #         {
# #             "title": "Introduction",
# #             "content": "Luke: I've got a bad feeling about this...",
# #             "subsections": [
# #                 {"title": "Background", "content": "Obi-Wan: Trust the Force, Luke."},
# #                 {"title": "Scope", "content": "Darth Vader: I find your lack of faith disturbing."}
# #             ]
# #         },
# #         {
# #             "title": "Main Content",
# #             "content": "Luke: What’s the main content, Master?",
# #             "subsections": [
# #                 {"title": "Details", "points": [
# #                     {"point": "Use the Force, Luke!"},
# #                     {"point": "That’s no moon, it’s a space station."}
# #                 ]},
# #                 {"title": "Analysis", "points": [
# #                     {"point": "The Force is strong with this one."},
# #                     {"point": "You underestimate the power of the Dark Side."}
# #                 ]}
# #             ]
# #         },
# #         {
# #             "title": "Conclusion",
# #             "content": "Obi-Wan: The Force will be with you, always.",
# #             "acknowledgements": [
# #                 {"name": "Dave", "contribution": "Being the chosen one."},
# #                 {"name": "Eve", "contribution": "Keeping balance to the Force."}
# #             ]
# #         }
# #     ]
# # }

# # ## Jinja Template (template_starwars.md)
# # Here is a Jinja template to render this data into a Markdown format.
# supermarket_template = """
# <!-- template_starwars.md -->
# # {{ title }}

# **Author**: {{ author }}

# **Date**: {{ date }}

# {% for section in sections %}
# ## {{ section.title }}

# {{ section.content }}

# {% if section.subsections %}
#   {% for subsection in section.subsections %}
# ### {{ subsection.title }}

# {{ subsection.content }}

#   {% if subsection.points %}
#     {% for point in subsection.points %}
# - {{ point.point }}
#     {% endfor %}
#   {% endif %}
#   {% endfor %}
# {% endif %}

# {% if section.acknowledgements %}
# **Acknowledgements**:
#   {% for ack in section.acknowledgements %}
# - {{ ack.name }}: {{ ack.contribution }}
#   {% endfor %}
# {% endif %}
# {% endfor %}
# """
# # Writing the Jinja template to a file for demonstration
# with open('template_starwars.md', 'w') as file:
#     file.write(supermarket_template)

# # ## Python Script to Render the Template
# # Now, let's write a Python script to load the YAML data, render the template, and output the result as a Markdown file.
# with open('supermarket.yaml', 'r') as file:
#     data = yaml.safe_load(file)

# # Set up the Jinja environment
# env = Environment(loader=FileSystemLoader('.'))
# template = env.get_template('template_starwars.md')

# # Render the template with the data
# output = template.render(data)

# # Output the result to a file
# output_file = 'output_starwars.md'
# with open(output_file, 'w') as file:
#     file.write(output)

# print(f"Markdown file generated: {output_file}")

##===========================================================================

# Importing necessary libraries
import yaml
from jinja2 import Environment, FileSystemLoader

# ## YAML Input
# the YAML structure for Star Wars conversation.
supermarket_yaml_data = """
title: Star Wars: A Humorous Conversation
author: George Lucas (Parody)
date: 2024-05-15
sections:
  - title: Introduction
    content: Luke: I've got a bad feeling about this...
    subsections:
      - title: Background
        content: Obi-Wan: Trust the Force, Luke.
      - title: Scope
        content: Darth Vader: I find your lack of faith disturbing.
  - title: Main Content
    content: Luke: What’s the main content, Master?
    subsections:
      - title: Details
        points:
          - point: Use the Force, Luke!
          - point: That’s no moon, it’s a space station.
      - title: Analysis
        points:
          - point: The Force is strong with this one.
          - point: You underestimate the power of the Dark Side.
  - title: Conclusion
    content: Obi-Wan: The Force will be with you, always.
    acknowledgements:
      - name: Dave
        contribution: Being the chosen one.
      - name: Eve
        contribution: Keeping balance to the Force.
"""

# Writing the YAML data to a file for demonstration
yaml_filename = 'supermarket.yaml'
try:
    with open(yaml_filename, 'w') as file:
        file.write(supermarket_yaml_data)
except IOError as e:
    print(f"Error writing YAML file: {e}")

# ## Jinja Template (template_starwars.md)
# Here is a Jinja template to render this data into a Markdown format.
supermarket_template = """
<!-- template_starwars.md -->
# {{ title }}

**Author**: {{ author }}

**Date**: {{ date }}

{% for section in sections %}
## {{ section.title }}

{{ section.content }}

{% if section.subsections %}
  {% for subsection in section.subsections %}
### {{ subsection.title }}

{{ subsection.content }}

  {% if subsection.points %}
    {% for point in subsection.points %}
- {{ point.point }}
    {% endfor %}
  {% endif %}
  {% endfor %}
{% endif %}

{% if section.acknowledgements %}
**Acknowledgements**:
  {% for ack in section.acknowledgements %}
- {{ ack.name }}: {{ ack.contribution }}
  {% endfor %}
{% endif %}
{% endfor %}
"""

# Writing the Jinja template to a file for demonstration
template_filename = 'template_starwars.md'
try:
    with open(template_filename, 'w') as file:
        file.write(supermarket_template)
except IOError as e:
    print(f"Error writing template file: {e}")

# ## Python Script to Render the Template
# Now, let's write a Python script to load the YAML data, render the template, and output the result as a Markdown file.
try:
    with open(yaml_filename, 'r') as file:
        data = yaml.safe_load(file)
except IOError as e:
    print(f"Error reading YAML file: {e}")
    data = None

if data:
    # Set up the Jinja environment
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_filename)

    # Render the template with the data
    output = template.render(data)

    # Output the result to a file
    output_file = 'output_starwars.md'
    try:
        with open(output_file, 'w') as file:
            file.write(output)
        print(f"Markdown file generated: {output_file}")
    except IOError as e:
        print(f"Error writing output file: {e}")
