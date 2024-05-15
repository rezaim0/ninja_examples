<!-- Template file: template.md -->
Company Name: {{ company.name }}

{% for department, department_data in company.departments.items() %}
Department: {{ department }}
Employees:
{% for employee in department_data.employees %}
- Name: {{ employee.name }}
  Age: {{ employee.age }}
  Skills:
  {% for skill in employee.skills %}
  - {{ skill }}
  {% endfor %}
{% endfor %}
{% endfor %}
