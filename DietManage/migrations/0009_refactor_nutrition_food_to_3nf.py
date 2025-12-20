from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('DietManage', '0008_delete_comment'),
    ]

    operations = [
        # 1. Remove derived fields from the table
        migrations.RemoveField(
            model_name='nutritionfood',
            name='energy_kcal',
        ),
        migrations.RemoveField(
            model_name='nutritionfood',
            name='energy_get_kj',
        ),
        migrations.RemoveField(
            model_name='nutritionfood',
            name='energy_get_kcal',
        ),
        migrations.RemoveField(
            model_name='nutritionfood',
            name='water_get',
        ),
        # 2. Update help_text and defaults for remaining fields
        migrations.AlterField(
            model_name='nutritionfood',
            name='edible_portion',
            field=models.FloatField(default=1.0, help_text='可食部比例 (0-1)'),
        ),
        migrations.AlterField(
            model_name='nutritionfood',
            name='water_content',
            field=models.FloatField(default=0, help_text='每100g可食部水分含量 (克)'),
        ),
        migrations.AlterField(
            model_name='nutritionfood',
            name='energy_kj',
            field=models.FloatField(default=0, help_text='每100g可食部能量 (千焦)'),
        ),
        # 3. Create the View
        migrations.RunSQL(
            sql="""
            CREATE VIEW view_nutrition_food_full AS
            SELECT 
                id, 
                name, 
                edible_portion, 
                water_content, 
                energy_kj,
                CAST(energy_kj * 0.239 AS DOUBLE) AS energy_kcal,
                CAST(edible_portion * energy_kj AS DOUBLE) AS energy_get_kj,
                CAST(edible_portion * energy_kj * 0.239 AS DOUBLE) AS energy_get_kcal,
                CAST(edible_portion * water_content AS DOUBLE) AS water_get
            FROM dietmanage_nutritionfood;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_nutrition_food_full;",
        ),
    ]
