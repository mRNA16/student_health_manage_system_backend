from django.db import models

class NutritionFood(models.Model):
    name = models.CharField(max_length=100, unique=True)
    edible_portion = models.FloatField(help_text='可食部比例 (0-1)', default=1.0)
    water_content = models.FloatField(help_text='每100g可食部水分含量 (克)', default=0)
    energy_kj = models.FloatField(help_text='每100g可食部能量 (千焦)', default=0)

    def __str__(self):
        return self.name
