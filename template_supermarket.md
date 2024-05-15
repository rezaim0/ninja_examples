
<!-- template_supermarket.md -->
# Supermarket List

## Food

{% for item in food %}
  {% if item.vegetables %}
## Vegetables
- {{ item.vegetables }}
  {% endif %}
  {% if item.fruits %}
## Fruits
### Citrics
- {{ item.fruits.citrics }}
### Tropical
- {{ item.fruits.tropical }}
### Nuts
- {{ item.fruits.nuts }}
### Sweets
- {{ item.fruits.sweets }}
  {% endif %}
{% endfor %}
