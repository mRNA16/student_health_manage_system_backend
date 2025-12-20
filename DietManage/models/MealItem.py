from django.db import models
from .NutritionFood import NutritionFood
from .MealRecord import MealRecord

class MealItem(models.Model):
    meal_record = models.ForeignKey(MealRecord, on_delete=models.CASCADE, related_name='items')
    food = models.ForeignKey(NutritionFood, on_delete=models.DO_NOTHING, null=True)
    quantity_in_grams = models.FloatField()

    def __str__(self):
        return f"{self.food.name if self.food else '未知食物'} {self.quantity_in_grams}g"
