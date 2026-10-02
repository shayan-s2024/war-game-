from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name",
                  "telegram_id", "telegram_username", "telegram_photo_url", "is_bot_admin"]


class TelegramAuthSerializer(serializers.Serializer):
    """داده‌های Telegram Login Widget — باید hash آن با bot token verify شود
    (id و auth_date عدد ارسال می‌شوند؛ بعداً رشته می‌شوند)"""
    id = serializers.IntegerField()
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    photo_url = serializers.URLField(required=False, allow_blank=True)
    auth_date = serializers.IntegerField()
    hash = serializers.CharField()


class RegisterSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[a-zA-Z0-9_.]{3,32}$")
    password = serializers.CharField(min_length=6, max_length=128)
    ref = serializers.CharField(required=False, allow_blank=True)
