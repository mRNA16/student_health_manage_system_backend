from django.db import models
from .NutritionFood import NutritionFood
from .MealRecord import MealRecord

class MealItem(models.Model):
    meal_record = models.ForeignKey(MealRecord, on_delete=models.CASCADE, related_name='items')
    food = models.ForeignKey(NutritionFood, on_delete=models.SET_NULL, null=True)
    quantity_in_grams = models.FloatField()
    estimated_calories = models.FloatField(help_text="千卡(kcal)",default=0)
    estimated_water = models.FloatField(help_text="克(g)",default=0)

    def save(self, *args, **kwargs):
        if self.food and (not self.estimated_calories or self.estimated_calories == 0):
            self.estimated_calories = self.food.energy_get_kcal* self.quantity_in_grams/100
            self.estimated_water = self.food.water_content* self.quantity_in_grams/100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.food.name} {self.quantity_in_grams}g"
