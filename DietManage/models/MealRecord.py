from django.db import models
from django.contrib.auth.models import User

class MealRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    meal = models.CharField(
        max_length=10,
        choices=[('breakfast', '早餐'), ('lunch', '午餐'), ('dinner', '晚餐')]
    )
    source = models.CharField(
        max_length=20,
        choices=[('manual', '手动录入'), ('ai', '系统推荐')],
        default='manual'
    )

    def __str__(self):
        return f"{self.user.username} 的 {self.get_meal_display()} ({self.date})"
