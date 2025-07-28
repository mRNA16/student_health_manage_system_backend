from django.db import models

class NutritionFood(models.Model):
    name = models.CharField(max_length=100, unique=True)
    edible_portion = models.FloatField(default=1.0)
    water_content = models.FloatField(help_text='水含量 (克)', default=0)
    energy_kj = models.FloatField(help_text='能量 (千焦)', default=0)
    energy_kcal = models.FloatField(help_text='能量 (千卡)', default=0) 
    energy_get_kj = models.FloatField(help_text='能量 (千焦)', default=0)
    energy_get_kcal = models.FloatField(help_text='能量 (千卡)', default=0)
    water_get = models.FloatField(help_text='水分 (克)', default=0)

    def save(self, *args, **kwargs):
        if not self.energy_kcal and self.energy_kj:
            self.energy_kcal = self.energy_kj * 0.239  # 1 kJ ≈ 0.239 kcal
        self.energy_get_kcal = self.edible_portion * self.energy_kcal
        self.energy_get_kj = self.edible_portion * self.energy_kj
        self.water_get = self.edible_portion * self.water_content
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
