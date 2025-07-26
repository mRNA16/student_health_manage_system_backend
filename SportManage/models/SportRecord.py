from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import json
import os

class SportRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sport_records')
    date = models.DateField()
    sport = models.IntegerField()
    begin_time = models.TimeField()
    end_time = models.TimeField()
    duration = models.PositiveIntegerField()
    calories = models.FloatField(default=0)
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.sport} - {self.date}"
    
    def save(self, *args, **kwargs):
        bt = datetime.combine(self.date, self.begin_time)
        et = datetime.combine(self.date, self.end_time)
        if et < bt:
            et += timedelta(days=1)
        self.duration = (et - bt).total_seconds() / 3600

        met_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'met.json')
        with open(met_path, 'r', encoding='utf-8') as f:
            mets = json.load(f)
        try:
            met_value = mets[self.sport]['met']
        except (IndexError, KeyError):
            met_value = 1
        profile = self.user.profile
        weight = profile.weight
        gender = profile.gender
        factor = 3.5 if gender == 'male' else 3.1
        self.calories = (met_value * weight * factor / 200) * self.duration * 60

        super().save(*args, **kwargs)