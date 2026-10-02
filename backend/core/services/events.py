# -*- coding: utf-8 -*-
"""Activity Feed و online tracking — داده زنده داشبورد ادمین (بند ۷/۸ اسپک).

همه eventها اینجا ثبت می‌شوند تا هم Activity Feed عمومی و هم داشبورد ادمین
از یک منبع واحد تغذیه شوند؛ هیچ داده‌ای mock نیست.
"""
import logging

from django.utils import timezone

from ..models import ActivityLog, Player

logger = logging.getLogger(__name__)

# آستانه تراکنش بزرگ — برای feed و suspicious
LARGE_TX_THRESHOLD = 100_000


def serialize_event(row):
    """سریالایز عمومی event برای feed/API/WS"""
    return {"id": row.id, "kind": row.kind, "text": row.text,
            "created_at": row.created_at.isoformat()}


def _event_coords(actor):
    """مختصات کشور بازیکن برای نمایش روی Globe (واقعی؛ None اگر نبود)"""
    try:
        c = actor.country if actor else None
        if c is None:
            return None, None
        return (c.lat if c.lat is not None else c.continent.lat,
                c.lon if c.lon is not None else c.continent.lon)
    except Exception:
        return None, None


def log_event(kind, actor=None, text="", target_id=None, target_kind=""):
    """ثبت یک event در feed + push زنده WS. actor = Player یا None (سیستم)."""
    try:
        row = ActivityLog.objects.create(
            kind=kind, actor=actor,
            actor_name=(actor.player_name or "") if actor else "",
            text=text[:256], target_id=target_id, target_kind=target_kind)
    except Exception:
        logger.exception("log_event failed")
        return
    # 📡 WS زنده — همه رویدادهای جهان بدون refresh روی feed و Globe
    try:
        from ..api.routing import push_world_event
        lat, lon = _event_coords(actor)
        push_world_event({"id": row.id, "kind": kind, "text": text[:256],
                          "created_at": row.created_at.isoformat(),
                          "lat": lat, "lon": lon})
    except Exception:
        pass  # بدون Redis/channel layer، feed از polling تغذیه می‌شود


def log_large_transaction(player, amount, reason):
    """تراکنش‌های بزرگ یا منفی مشکوک → feed + suspicious."""
    if amount >= LARGE_TX_THRESHOLD:
        log_event("large_transaction", player,
                  f"💰 {player.player_name} — تراکنش {amount:,} سکه ({reason})",
                  target_id=player.id, target_kind="player")
    if amount <= -LARGE_TX_THRESHOLD:
        log_event("suspicious", player,
                  f"🚩 خروج غیرعادی {abs(amount):,} سکه از {player.player_name}",
                  target_id=player.id, target_kind="player")


def touch_last_seen(user):
    """به‌روزرسانی last_seen — هر ساعت یک بار (کاهش write) تا پرشمارش شود."""
    if not user or not user.is_authenticated:
        return
    p = Player.objects.filter(user=user).only("id", "last_seen").first()
    if not p:
        return
    now = timezone.now()
    if not p.last_seen or (now - p.last_seen).total_seconds() > 3600:
        Player.objects.filter(id=p.id).update(last_seen=now)


def online_count():
    """Online Users = last_seen در ۱۵ دقیقه اخیر"""
    return Player.objects.filter(
        last_seen__gte=timezone.now() - timezone.timedelta(minutes=15)).count()


def ws_connections_count():
    """تعداد اتصال‌های فعال WS بازیکنان — از channel layer groups (بدون شمارش دستی)."""
    try:
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        # channels_redis نگهداری group memberships را expose نمی‌کند؛
        # fallback: اتصال‌های اخیر از Redis INCR که consumer در connect می‌زند
        from django.core.cache import cache
        return cache.get("ws_player_connections", 0)
    except Exception:
        return 0
