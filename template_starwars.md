
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
