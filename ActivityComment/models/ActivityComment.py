from django.db import models
from django.contrib.auth import get_user_model

class ActivityComment(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20)  # 'sport' | 'sleep' | 'meal'
    activity_id = models.IntegerField()  # 对应 SportRecord / SleepRecord / MealRecord 的 ID
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)