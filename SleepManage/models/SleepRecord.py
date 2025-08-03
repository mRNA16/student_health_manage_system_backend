from django.db import models
from django.contrib.auth.models import User

class SleepRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sleep_records')
    date = models.DateField()
    sleep_time = models.TimeField()
    wake_time = models.TimeField()
    duration = models.FloatField(help_text="睡眠时长（小时）", blank=True)
    note = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from datetime import datetime, timedelta
        st = datetime.combine(self.date, self.sleep_time)
        wt = datetime.combine(self.date, self.wake_time)
        if wt < st:
            wt += timedelta(days=1)
        self.duration = (wt - st).total_seconds() / 3600
        super().save(*args, **kwargs)