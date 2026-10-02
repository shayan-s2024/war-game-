# -*- coding: utf-8 -*-
"""کارهای پس‌زمینه Celery — جانشین حلقه زمانی نسخه تلگرام (economy.py)."""
import logging
import random

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from ..gamedata import VIRUSES
from ..models import Notification, Player, WarEvent
from . import economy as eco
from . import gamestate as gs

logger = logging.getLogger(__name__)


def _all_players():
    return Player.objects.filter(player_name__isnull=False).select_related("country")


@shared_task(name="core.services.tick.task_daily_profit")
def task_daily_profit():
    """💰 سود شبانه — هر شب ساعت ۲۲ به وقت تهران (فقط یک بار در روز اجرا شود)"""
    now = timezone.localtime(timezone.now())
    if now.hour != 22:
        return "not 22:00 yet"
    today = now.strftime("%Y%m%d")
    if gs.get_config("last_profit_date") == today:
        return "already done"
    gs.set_config("last_profit_date", today)
    for p in _all_players():
        result = eco.apply_daily_profit(p)
        if result["profit"] > 0:
            Notification.objects.create(
                player=p, kind="reward", title="📈 سود روزانه واریز شد",
                body=f"{result['profit']:,} سکه به خزانه شما اضافه شد.")
    return "done"


@shared_task(name="core.services.tick.task_virus_damage")
def task_virus_damage():
    """🦠 آسیب ویروس — یک بار در هر روز بازی"""
    current_day = gs.get_game_day()
    if gs.get_config("last_virus_damage_day") == str(current_day):
        return "already done today"
    gs.set_config("last_virus_damage_day", current_day)
    if not gs.is_virus_active():
        return "viruses not active yet"
    for p in _all_players():
        if not p.active_viruses:
            continue
        reports = eco.apply_virus_damage(p, current_day)
        for r in reports:
            if r.get("cured"):
                Notification.objects.create(player=p, kind="virus", title="✅ ویروس مهار شد",
                                            body=f"ویروس {VIRUSES[r['virus']]['name']} در کشور شما مهار شد!")
            else:
                Notification.objects.create(player=p, kind="virus", title="🦠 گزارش ویروس",
                                            body=f"{VIRUSES[r['virus']]['name']}: {r.get('pop_loss', 0)} تلفات امروز. روزهای باقیمانده: {p.active_viruses.get(r['virus'], {}).get('remaining_days', 0)}")
    return "done"


@shared_task(name="core.services.tick.task_spread_virus")
def task_spread_virus():
    """🦠 انتشار تصادفی ویروس — ۱۵٪ شانس هر ۶ ساعت"""
    if not gs.is_virus_active():
        return "viruses not active"
    if random.random() >= settings.GAME["VIRUS_SPREAD_CHANCE"]:
        return "no spread this cycle"
    players = list(_all_players())
    if not players:
        return "no players"
    target = random.choice(players)
    vkey = random.choice(list(VIRUSES.keys()))
    target.active_viruses[vkey] = {
        "remaining_days": settings.GAME["VIRUS_DURATION_DAYS"],
        "daily_loss": VIRUSES[vkey]["daily_loss"],
        "damage_base": VIRUSES[vkey]["damage_base"],
        "start_date": timezone.now().timestamp(),
    }
    target.save(update_fields=["active_viruses"])
    Notification.objects.create(
        player=target, kind="virus", title=f"⚠️ {VIRUSES[vkey]['name']} شناسایی شد!",
        body=f"ضرر روزانه: {VIRUSES[vkey]['daily_loss']} نفر | مدت: {settings.GAME['VIRUS_DURATION_DAYS']} روز | برای درمان بیمارستان بسازید!")
    return f"virus {vkey} spread to {target.player_name}"


@shared_task(name="core.services.tick.task_fire_burn")
def task_fire_burn():
    """🔥 آتش‌سوزی شهرهای در آشوب — روزانه"""
    today = timezone.localtime().strftime("%Y%m%d")
    if gs.get_config("last_fire_burn") == today:
        return "already done"
    gs.set_config("last_fire_burn", today)
    for p in _all_players():
        burn = eco.apply_fire_burn(p)
        if burn > 0:
            Notification.objects.create(player=p, kind="bomb", title="🔥 شهر شما هنوز در آتش می‌سوزد!",
                                        body=f"امروز {burn:,} نفر جان باختند.")
    return "done"


@shared_task(name="core.services.tick.task_tick_fleets")
def task_tick_fleets():
    """⚓ رسیدن و برگشت ناوگان‌ها — هر ۳۰ ثانیه"""
    from .naval import tick_fleets
    return tick_fleets()


@shared_task(name="core.services.tick.task_check_war_schedule")
def task_check_war_schedule():
    """⚔️ پایان خودکار جنگ‌های زمان‌بندی‌شده"""
    now = timezone.now()
    expired = WarEvent.objects.filter(active=True, end_time__lt=now)
    count = 0
    for ev in expired:
        ev.active = False
        ev.save()
        count += 1
        for p in _all_players():
            Notification.objects.create(player=p, kind="war", title="🕊️ جنگ جهانی به پایان رسید!",
                                        body="حالت صلح برقرار شد.")
    return f"{count} wars ended"


# ==================== 🌍 World Simulation tick — دیپلماسی/تجارت/هشدار ====================

@shared_task(name="core.services.tick.task_diplomacy_tick")
def task_diplomacy_tick():
    """🤝 اجرای تجارت‌های فعال + انقضای پیشنهادها — هر ۵ دقیقه (fallback: lazy در GET)"""
    from . import diplomacy
    trade = diplomacy.execute_trade_tick()
    expired = diplomacy.expire_proposals()
    return f"{trade}; {expired}"


@shared_task(name="core.services.tick.task_alerts_tick")
def task_alerts_tick():
    """🚨 ارزیابی هشدارهای همه بازیکنان از وضعیت واقعی — هر ۱۵ دقیقه (fallback: lazy)"""
    from . import alerts
    n = 0
    for p in _all_players():
        try:
            found = alerts.evaluate_player(p)
            n += len(found)
        except Exception:
            logger.exception("alerts tick failed for player %s", p.id)
    return f"{n} alerts active"


# ==================== Lazy fallback (بدون Redis/Celery در دمو) ====================

def lazy_world_tick():
    """اجرای سبک tick جهان در request — با throttle از GameConfig (هر ۳ دقیقه یک بار).
    در production Celery/beat جای این را می‌گیرد؛ این fallback است نه جایگزین.
    """
    import time as _time
    from . import gamestate as gs
    now = _time.time()
    last = float(gs.get_config("last_lazy_world_tick", "0") or 0)
    if now - last < 180:
        return False
    gs.set_config("last_lazy_world_tick", str(now))
    try:
        from .naval import tick_fleets
        tick_fleets()
    except Exception:
        logger.exception("lazy tick fleets")
    try:
        from . import diplomacy
        diplomacy.execute_trade_tick()
        diplomacy.expire_proposals()
    except Exception:
        logger.exception("lazy tick diplomacy")
    try:
        from . import alerts
        alerts.evaluate_player  # import check
        from ..models import Player
        for p in Player.objects.filter(player_name__isnull=False).select_related("country")[:50]:
            alerts.evaluate_player(p)
    except Exception:
        logger.exception("lazy tick alerts")
    return True
