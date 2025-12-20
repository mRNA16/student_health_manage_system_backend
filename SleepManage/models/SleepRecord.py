from django.db import models
from django.contrib.auth.models import User

class SleepRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='sleep_records')
    date = models.DateField()
    sleep_time = models.TimeField()
    wake_time = models.TimeField()
    created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}"