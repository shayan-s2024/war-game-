# -*- coding: utf-8 -*-
"""WebSocket routing + اعلان‌های realtime.

احراز هویت WS: فرانت JWT دارد (نه session)؛ توکن access از query string
خوانده و با SimpleJWT verify می‌شود:
    ws://host/ws/game/?token=<access_token>
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.urls import path


@database_sync_to_async
def _user_from_token(token_str):
    """بازگردانی کاربر از توکن JWT — با SimpleJWT (با درنظر گرفتن blacklist)."""
    from django.contrib.auth import get_user_model

    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import AccessToken

    try:
        access = AccessToken(token_str)
    except TokenError:
        return None
    try:
        user = get_user_model().objects.get(id=access["user_id"])
        return user if user.is_active else None
    except get_user_model().DoesNotExist:
        return None


class PlayerConsumer(AsyncJsonWebsocketConsumer):
    """کانال اعلان‌های realtime بازیکن — battle/bomb/hack/virus/war و ..."""

    async def connect(self):
        # توکن از query string: /ws/game/?token=<access>
        token = ""
        for part in self.scope.get("query_string", b"").decode().split("&"):
            name, _, value = part.partition("=")
            if name == "token" and value:
                token = value
                break
        user = await _user_from_token(token) if token else None
        if user is None:
            await self.close(code=4401)
            return
        player_id = await self._get_player_id(user)
        if player_id is None:
            await self.close(code=4404)
            return
        self.group_name = f"player_{player_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected", "player_id": player_id})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify(self, event):
        await self.send_json({"type": "notification", "payload": event["payload"]})

    @database_sync_to_async
    def _get_player_id(self, user):
        from core.models import Player
        p = Player.objects.filter(user=user).only("id").first()
        return p.id if p else None


async def push_notification(player_id, payload):
    """ارسال اعلان به گروه بازیکن — async؛ از سرویس‌های sync با async_to_sync."""
    from channels.layers import get_channel_layer
    layer = get_channel_layer()
    await layer.group_send(f"player_{player_id}", {"type": "notify", "payload": payload})


def notify_player_sync(player_id, payload):
    """نقطه ورود sync برای سرویس‌های Django — امن حتی اگر Redis/channel layer خطا دهد."""
    try:
        from asgiref.sync import async_to_sync
        async_to_sync(push_notification)(player_id, payload)
    except Exception:
        pass  # بدون Redis، اعلان در دیتابیس می‌ماند و فرانت polling می‌کند


def push_admin_dashboard(payload):
    """ارسال event زنده به همه داشبوردهای ادمین — از سرویس‌ها (sync)"""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        async def _push():
            layer = get_channel_layer()
            await layer.group_send("admin_dashboard", {"type": "dash.event", "payload": payload})
        async_to_sync(_push)()
    except Exception:
        pass  # بدون Redis، feed همچنان از دیتابیس poll می‌شود


class WorldConsumer(AsyncJsonWebsocketConsumer):
    """🌍 کانال عمومی جهان — رویدادهای feed (نبرد/اتحاد/ناوگان/...) بدون refresh.
    عمومی و read-only؛ پس از اتصال به گروه world_join، تعداد بیننده زنده بالا می‌ماند.
    """

    async def connect(self):
        self.group_name = "world_feed"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add("world_join", self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected"})
        viewers = await self._viewers_count()
        await self._broadcast_viewers(viewers)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("world_feed", self.channel_name)
        await self.channel_layer.group_discard("world_join", self.channel_name)
        viewers = await self._viewers_count()
        await self._broadcast_viewers(viewers)

    async def world_event(self, event):
        await self.send_json({"type": "event", "payload": event["payload"]})

    async def viewers(self, event):
        await self.send_json({"type": "viewers", "count": event["count"]})

    @database_sync_to_async
    def _viewers_count(self):
        from django.core.cache import cache
        return cache.get("ws_player_connections", 0)

    async def _broadcast_viewers(self, count):
        try:
            from channels.layers import get_channel_layer
            await get_channel_layer().group_send("world_feed", {"type": "viewers", "count": count})
        except Exception:
            pass


async def push_world_event(payload):
    """ارسال event جهان به همه بیننده‌های Globe — از سرویس‌ها با async_to_sync."""
    from channels.layers import get_channel_layer
    layer = get_channel_layer()
    await layer.group_send("world_feed", {"type": "world_event", "payload": payload})


class AdminConsumer(AsyncJsonWebsocketConsumer):
    """کانال زنده داشبورد ادمین — فقط ادمین واقعی (server-side check)"""

    async def connect(self):
        token = ""
        for part in self.scope.get("query_string", b"").decode().split("&"):
            name, _, value = part.partition("=")
            if name == "token" and value:
                token = value
                break
        user = await _user_from_token(token) if token else None
        if user is None or not await _is_admin(user):
            await self.close(code=4403)
            return
        self.group_name = "admin_dashboard"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected"})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def dash_event(self, event):
        await self.send_json({"type": "dash", "payload": event["payload"]})


@database_sync_to_async
def _is_admin(user):
    from core.models import AdminUser
    return bool(user.is_staff or user.is_superuser
                or (user.telegram_id and AdminUser.objects.filter(telegram_id=user.telegram_id).exists()))


websocket_urlpatterns = [
    path("ws/world/", WorldConsumer.as_asgi()),
    path("ws/game/", PlayerConsumer.as_asgi()),
    path("ws/admin/", AdminConsumer.as_asgi()),
]
