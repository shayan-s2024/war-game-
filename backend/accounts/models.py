from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """کاربر — با اتصال تلگرام برای اشتراک حساب بین ربات و وب"""
    telegram_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    telegram_username = models.CharField(max_length=64, blank=True, default="")
    telegram_photo_url = models.URLField(blank=True, default="")
    is_bot_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.username
