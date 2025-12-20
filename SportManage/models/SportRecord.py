from django.db import models
from django.contrib.auth.models import User

class SportRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='sport_records')
    date = models.DateField()
    sport = models.IntegerField()
    begin_time = models.TimeField()
    end_time = models.TimeField()
    calories = models.FloatField(default=0)
    note = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.sport} - {self.date}"