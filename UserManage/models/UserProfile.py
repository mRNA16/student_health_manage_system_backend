from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    height = models.FloatField(verbose_name="身高（cm）")
    weight = models.FloatField(verbose_name="体重（kg）")
    gender = models.CharField(max_length=10, choices=(('male', '男'), ('female', '女')), verbose_name="性别")
    birthday = models.DateField(verbose_name="生日")
    realName = models.CharField(max_length=150, verbose_name="真实姓名", blank=True, null=True)
    roles = models.JSONField(default=list, verbose_name="角色", blank=True, null=True)

    def __str__(self):
        return self.user.username