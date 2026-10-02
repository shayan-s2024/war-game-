# -*- coding: utf-8 -*-
"""احراز هویت — ثبت‌نام/ورود + Telegram Login (اشتراک حساب بین ربات و وب).

Telegram Login Widget با HMAC-SHA256 verify می‌شود (مستندات رسمی تلگرام)؛
اگر کاربر با همان telegram_id در ربات بازی کرده باشد، همان Player و همان
progression را می‌بیند.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.serializers import RegisterSerializer, TelegramAuthSerializer
from core.api.throttling import AuthRateThrottle
from core.models import AdminUser


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def _ensure_main_admin():
    AdminUser.objects.get_or_create(telegram_id=settings.GAME["MAIN_ADMIN_TELEGRAM_ID"])


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def register(request):
    """ثبت‌نام با username/password — سپس فلو انتخاب کشور/کابینه در players API"""
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    username = s.validated_data["username"]
    if User.objects.filter(username=username).exists():
        return Response({"error": "این نام کاربری قبلاً گرفته شده"}, status=400)
    with transaction.atomic():
        user = User.objects.create_user(username=username, password=s.validated_data["password"])
        _ensure_main_admin()
    tokens = _issue_tokens(user)
    return Response({"tokens": tokens, "user": {"id": user.id, "username": user.username}}, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def login(request):
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(username=username, password=password)
    if not user:
        return Response({"error": "نام کاربری یا رمز عبور اشتباه است"}, status=401)
    tokens = _issue_tokens(user)
    return Response({"tokens": tokens, "user": {"id": user.id, "username": user.username}})


def _telegram_webapp_identity(init_data):
    """Verify raw Telegram Mini App initData with the bot token."""
    if not isinstance(init_data, str) or not init_data or len(init_data) > 32768:
        raise ValueError("????? ???? ????? ??????? ???")
    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    if len(pairs) != len({key for key, _ in pairs}):
        raise ValueError("????? ???? ????? ??????? ???")
    fields = dict(pairs)
    received_hash = fields.pop("hash", "")
    bot_token = getattr(settings, "TELEGRAM_LOGIN_BOT_TOKEN", "")
    if not bot_token or not received_hash:
        raise ValueError("???? ?????? ?? ???? ???????? ???? ???")
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("????? ???? ?????? ??????? ???")
    try:
        user_data = json.loads(fields.get("user", "{}"))
        user_id = user_data.get("id")
        auth_date = int(fields.get("auth_date", "0"))
    except (TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("????? ????? ?????? ??????? ???")
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise ValueError("?????? ????? ?????? ??????? ???")
    now = int(time.time())
    if auth_date <= 0 or auth_date > now + 60 or now - auth_date > 86400:
        raise ValueError("???????? ????? ?????? ????? ???????")
    return {
        "id": str(user_id),
        "auth_date": str(auth_date),
        "username": str(user_data.get("username") or ""),
        "first_name": str(user_data.get("first_name") or ""),
        "last_name": str(user_data.get("last_name") or ""),
        "photo_url": str(user_data.get("photo_url") or ""),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
@transaction.atomic
def telegram_login(request):
    """Sign in with Telegram Login Widget or a validated Mini App initData."""
    init_data = request.data.get("init_data")
    if init_data is not None:
        try:
            data = _telegram_webapp_identity(init_data)
        except (ValueError, TypeError):
            return Response({"error": "????? ???? ?????? ??????? ???"}, status=401)
    else:
        s = TelegramAuthSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = {k: str(v) for k, v in s.validated_data.items() if v}
        received_hash = data.pop("hash", "")
        bot_token = getattr(settings, "TELEGRAM_LOGIN_BOT_TOKEN", "")
        if not bot_token:
            return Response({"error": "???? ?????? ?? ???? ???????? ???? ???"}, status=503)
        # Telegram Login Widget check string and HMAC format.
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret = hashlib.sha256(bot_token.encode()).digest()
        computed = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
        if not received_hash or not hmac.compare_digest(computed, received_hash):
            return Response({"error": "????? ???? ?????? ??????? ???"}, status=401)
        try:
            auth_date = int(data.get("auth_date", 0))
        except (TypeError, ValueError):
            return Response({"error": "auth_date ???????"}, status=400)
        now = int(time.time())
        if auth_date <= 0 or auth_date > now + 60 or now - auth_date > 86400:
            return Response({"error": "???????? ????? ????? ???????"}, status=401)

    tg_id = str(data["id"])
    user = User.objects.filter(telegram_id=tg_id).first()
    if not user:
        username = data.get("username") or f"tg_{tg_id}"
        base, i = username, 1
        while User.objects.filter(username=username).exists():
            username = f"{base}_{i}"
            i += 1
        user = User.objects.create_user(username=username)
        user.telegram_id = tg_id
        user.telegram_username = data.get("username", "")
        user.telegram_photo_url = data.get("photo_url", "")
        user.is_bot_admin = AdminUser.objects.filter(telegram_id=tg_id).exists()
        user.save()
    tokens = _issue_tokens(user)
    return Response({"tokens": tokens, "user": {"id": user.id, "username": user.username,
                                                "telegram_id": user.telegram_id}})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def refresh_token(request):
    s = TokenRefreshSerializer(data=request.data)
    try:
        s.is_valid(raise_exception=True)
        return Response(s.validated_data)
    except Exception:
        return Response({"error": "توکن نامعتبر"}, status=401)
