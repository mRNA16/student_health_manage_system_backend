import json
import os
from django.db import migrations

def parse_value(val, unit):
    if not val or val in ['Tr', '-', '—', '…']:
        return 0.0
    try:
        # Remove unit and any non-numeric characters except decimal point
        clean_val = ''.join(c for c in val if c.isdigit() or c == '.')
        return float(clean_val) if clean_val else 0.0
    except ValueError:
        return 0.0

def parse_portion(val):
    if not val or val in ['Tr', '-', '—', '…']:
        return 1.0
    try:
        clean_val = ''.join(c for c in val if c.isdigit() or c == '.')
        return float(clean_val) / 100.0 if clean_val else 1.0
    except ValueError:
        return 1.0

def import_food_data(apps, schema_editor):
    NutritionFood = apps.get_model('DietManage', 'NutritionFood')
    json_path = os.path.join(os.path.dirname(__file__), '..', 'food_nutrition.json')
    
    if not os.path.exists(json_path):
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    foods_to_create = []
    seen_names = set()
    
    for item in data:
        name = item.get('food_name')
        if not name or name in seen_names:
            continue
            
        # Check if already exists in DB (to avoid migration re-run issues)
        if NutritionFood.objects.filter(name=name).exists():
            seen_names.add(name)
            continue

        edible = parse_portion(item.get('edible_portion'))
        water = parse_value(item.get('water_content'), 'g')
        energy = parse_value(item.get('energy'), 'kJ')
        
        foods_to_create.append(
            NutritionFood(
                name=name,
                edible_portion=edible,
                water_content=water,
                energy_kj=energy
            )
        )
        seen_names.add(name)
        
        # Bulk create in chunks to avoid memory issues
        if len(foods_to_create) >= 500:
            NutritionFood.objects.bulk_create(foods_to_create)
            foods_to_create = []

    if foods_to_create:
        NutritionFood.objects.bulk_create(foods_to_create)

def reverse_import(apps, schema_editor):
    NutritionFood = apps.get_model('DietManage', 'NutritionFood')
    NutritionFood.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('DietManage', '0009_refactor_nutrition_food_to_3nf'),
    ]

    operations = [
        migrations.RunPython(import_food_data, reverse_import),
    ]
