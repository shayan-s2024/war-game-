# -*- coding: utf-8 -*-
"""Rate limiting سمت سرور — ضد اسپم و rate abuse."""
from rest_framework.throttling import SimpleRateThrottle


class GameRateThrottle(SimpleRateThrottle):
    """محدودیت عمومی اکشن‌های بازی per-user"""
    scope = "game"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return self.cache_format % {"scope": self.scope, "ident": request.user.pk}
        return self.get_ident(request)


class AuthRateThrottle(SimpleRateThrottle):
    """محدودیت سخت‌گیرانه برای endpointهای احراز هویت"""
    scope = "auth"

    def get_cache_key(self, request, view):
        return self.get_ident(request)


class AdminRateThrottle(SimpleRateThrottle):
    scope = "admin"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return self.cache_format % {"scope": self.scope, "ident": request.user.pk}
        return self.get_ident(request)
