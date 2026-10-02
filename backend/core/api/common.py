# -*- coding: utf-8 -*-
"""ابزار مشترک viewها — دریافت بازیکن از کاربر JWT."""
from core.models import Player


def get_player(request):
    try:
        return Player.objects.select_related("country", "country__continent", "union").get(user=request.user)
    except Player.DoesNotExist:
        return None


def require_player(request):
    """(player, error_response) — بازیکنِ ثبت‌نام‌کرده یا خطای ۴۰۳."""
    player = get_player(request)
    if not player or not player.player_name:
        return None, Response_needs_registration()
    return player, None


def Response_needs_registration():
    from rest_framework.response import Response
    return Response({"error": "ابتدا باید ثبت‌نام کامل کنید", "needs_registration": True}, status=403)
