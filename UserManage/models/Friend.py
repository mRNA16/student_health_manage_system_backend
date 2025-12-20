from django.db import models
from django.contrib.auth.models import User

class Friend(models.Model):
    STATUS_CHOICES = (
        ('pending', '待接受'),
        ('accepted', '已接受'),
        ('rejected', '已拒绝'),
    )

    from_user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='sent_friend_requests')
    to_user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='received_friend_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('from_user', 'to_user', 'status')

    def __str__(self):
        return f'{self.from_user.username} -> {self.to_user.username}: {self.status}'