# -*- coding: utf-8 -*-
"""🚨 موتور هشدار — همه alertها از وضعیت واقعی Game Core تولید می‌شوند.

- dedup با akey (TYPE:key:scope) — هر مشکل فقط یک Alert فعال (update می‌شود، تکرار نمی‌شود)
- lifecycle: active → acknowledged → resolved (alert پایدار می‌ماند تا رفع مشکل)
- اولویت از فرمول configurable در settings.GAME["ALERT_WEIGHTS"]
- push زنده WS به گروه بازیکن (fallback: polling)
"""
import logging

from django.conf import settings
from django.utils import timezone

from ..models import Alert
from . import gamestate as gs

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {"severity": {"critical": 60, "warning": 30, "info": 10},
                   "economic": 20, "military": 20, "population": 15, "time": 15}


def _weights() -> dict:
    try:
        w = settings.GAME.get("ALERT_WEIGHTS", {})
        out = {k: dict(v) if isinstance(v, dict) else v for k, v in DEFAULT_WEIGHTS.items()}
        for k, v in w.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k].update(v)
            else:
                out[k] = v
        return out
    except Exception:
        return DEFAULT_WEIGHTS


def compute_priority(severity: str, kind: str) -> int:
    """فرمول اولویت — configurable بدون تغییر کد."""
    w = _weights()
    p = w["severity"].get(severity, 10)
    if kind in ("resource_shortage", "treasury_low", "production_failure", "trade_disruption"):
        p += w["economic"]
    if kind in ("supply_disruption", "military_readiness", "equipment_shortage"):
        p += w["military"]
    if kind == "resource_shortage":
        p += w["population"]
    if severity == "critical":
        p += w["time"]
    return min(100, p)


def raise_alert(player, kind: str, akey: str, title: str, description: str = "",
                cause: str = "", severity: str = "warning",
                recommended_action: str = "", meta: dict | None = None, country=None) -> Alert:
    """ساخت/به‌روزرسانی هشدار با dedup — اگر فعال بود، محتوا/اولویت refresh می‌شود."""
    try:
        existing = Alert.objects.filter(akey=akey, status__in=["active", "acknowledged"]).first()
        priority = compute_priority(severity, kind)
        if existing:
            changed = []
            if existing.description != description:
                existing.description = description[:2000]; changed.append("description")
            if existing.priority != priority:
                existing.priority = priority; changed.append("priority")
            if existing.severity != severity:
                existing.severity = severity; changed.append("severity")
            # اگر قبلاً ack شده ولی بدتر شد (critical) → دوباره فعال
            if existing.status == "acknowledged" and severity == "critical":
                existing.status = "active"; existing.acked_at = None; changed.append("status")
            if changed:
                existing.save(update_fields=list(set(changed + ["updated_at"])))
            return existing
        alert = Alert.objects.create(
            akey=akey[:120], country=country, player=player, type=kind,
            severity=severity, priority=priority, title=title[:128],
            description=description[:2000], cause=cause[:256],
            recommended_action=recommended_action[:256], meta=meta or {})
        _notify(player, alert)
        return alert
    except Exception:
        logger.exception("raise_alert failed for %s", akey)
        raise


def resolve_alert(akey: str) -> bool:
    """رفع مشکل → resolved (تاریخچه حفظ می‌شود)."""
    updated = Alert.objects.filter(akey=akey, status__in=["active", "acknowledged"]) \
        .update(status="resolved", resolved_at=timezone.now())
    return bool(updated)


def ack_alert(player, alert_id: int) -> Alert | None:
    a = Alert.objects.filter(id=alert_id, player=player, status="active").first()
    if a:
        a.status = "acknowledged"
        a.acked_at = timezone.now()
        a.save(update_fields=["status", "acked_at"])
    return a


def _notify(player, alert: Alert):
    """push زنده به گروه بازیکن — بدون Redis، بی‌صدا skip."""
    try:
        from ..api.routing import notify_player_sync
        notify_player_sync(player.id, {"kind": "alert", "id": alert.id, "type": alert.type,
                                       "severity": alert.severity, "title": alert.title,
                                       "priority": alert.priority, "akey": alert.akey})
    except Exception:
        pass


# ==================== ارزیابی وضعیت واقعی بازیکن ====================

TREASURY_LOW_ABS = 2_000          # خزانه مطلق زیر این = هشدار
TREASURY_LOW_RATIO = 0.05         # یا زیر ۵٪ درآمد روزانه


def evaluate_player(player) -> list[Alert]:
    """🩺 ارزیابی کامل وضعیت واقعی بازیکن — هر هشدار از داده Game Core.
    خروجی: لیست alertهای فعال پس از ارزیابی (برای resolve خودکار موارد رفع‌شده).
    """
    from ..gamedata import AIR_DEFENSES, NAVAL_VESSELS, TANKS, FIGHTERS
    now = timezone.now()
    raised: list[Alert] = []

    def _active(akey):
        return Alert.objects.filter(akey=akey, status__in=["active", "acknowledged"]).exists()

    # ۱) خزانه — ترکیبی از credit واقعی و درآمد/هزینه ثبت‌شده
    income = player.daily_profit or 0
    low = player.credit < TREASURY_LOW_ABS or (income > 0 and player.credit < income * TREASURY_LOW_RATIO)
    akey = "treasury_low:credit:player"
    if low:
        raised.append(raise_alert(
            player, "treasury_low", akey, "💰 خزانه کشور رو به تخلیه است",
            f"موجودی {player.credit:,} سکه — با درآمد روزانه {income:,} پوشش کافی نیست.",
            cause="درآمد روزانه کمتر از هزینه‌ها یا از دست رفتن سرمایه",
            severity="warning" if player.credit > 0 else "critical",
            recommended_action="معادن/شرکت‌های جدید بسازید یا هزینه نظامی را موقتاً کم کنید",
            meta={"credit": player.credit, "income": income}, country=player.country))
    elif _active(akey):
        resolve_alert(akey)

    # ۲) آمادگی نظامی — ارتش بدون پدافند/خلبان
    atk = player.attack_power or 0
    if atk > 0:
        fighters = gs.get_category_count(player, "fighter")
        pilots = sum(gs.get_item_qty(player, "pilot_count", k) for k in ("normal", "strong", "professional"))
        ready = gs.get_ready_fighters(player)
        akey2 = "military_readiness:pilots:player"
        if fighters > 0 and ready < fighters // 2:
            raised.append(raise_alert(
                player, "military_readiness", akey2, "✈️ بیش از نیمی از جنگنده‌ها خلبان ندارند",
                f"{ready} جنگنده آماده از {fighters} جنگنده ({pilots} خلبان).",
                cause="کمبود خلبان — جنگنده بدون خلبان در نبرد شرکت نمی‌کند",
                severity="warning",
                recommended_action="از فروشگاه بخش خلبان‌ها، خلبان خریداری کنید",
                meta={"ready": ready, "fighters": fighters, "pilots": pilots}, country=player.country))
        elif _active(akey2):
            resolve_alert(akey2)
        # پدافند صفر با ارتش بزرگ
        ad = sum(gs.get_item_qty(player, "air_defense_count", k) for k in AIR_DEFENSES)
        akey3 = "military_readiness:air_defense:player"
        if ad == 0 and atk >= 5000:
            raised.append(raise_alert(
                player, "military_readiness", akey3, "🛡 کشور بدون پدافند هوایی است",
                f"قدرت حمله {atk:,} اما هیچ پدافندی موجود نیست — حملات هوایی تقریباً بدون مانع وارد می‌شوند.",
                cause="نبود پدافند هوایی",
                severity="critical", recommended_action="خرید پدافند از فروشگاه (عادی تا گنبد آهنین)",
                meta={"attack": atk}, country=player.country))
        elif _active(akey3):
            resolve_alert(akey3)

    # ۳) تجهیزات — ارتش سرگردان بدون هیچ نیروی زمینی آماده
    ground = gs.get_category_count(player, "ground")
    akey4 = "equipment_shortage:ground:player"
    if atk > 0 and ground == 0:
        raised.append(raise_alert(
            player, "equipment_shortage", akey4, "🥷 نیروی زمینی صفر است",
            "بدون نیروی زمینی، دفاع سرزمینی و اشغال ممکن نیست.",
            cause="نبود سرباز", severity="warning",
            recommended_action="خرید سرباز عادی از فروشگاه (پادگان به‌مرور تولید می‌کند)",
            meta={"attack": atk}, country=player.country))
    elif _active(akey4):
        resolve_alert(akey4)

    # ۴) اختلال تأمین دریایی — ناو بدون اسکله (بندر)
    naval = sum(gs.get_item_qty(player, "naval_count", k) for k in NAVAL_VESSELS)
    docks = gs.get_item_qty(player, "count", "dock")
    akey5 = "supply_disruption:dock:player"
    if naval > 0 and docks == 0:
        raised.append(raise_alert(
            player, "supply_disruption", akey5, "⚓ ناوهای شما بدون اسکله هستند",
            f"{naval} شناور نظامی دارید اما اسکله‌ای برای پشتیبانی و ترانزیت تجهیزات ندارید — اعزام دریایی ممکن نیست.",
            cause="نبود اسکله (dock) برای عملیات دریایی",
            severity="critical", recommended_action="ساخت اسکله از فروشگاه بخش ساختمان‌ها",
            meta={"naval": naval}, country=player.country))
    elif _active(akey5):
        resolve_alert(akey5)

    # ۵) تولید — ویروس فعال با نبود بیمارستان
    if player.active_viruses:
        need_pro = any(v in ("rabies", "marburg") for v in player.active_viruses)
        pro_h = gs.get_item_qty(player, "count", "professional_hospital")
        normal_h = gs.get_item_qty(player, "count", "normal_hospital")
        akey6 = "production_failure:hospital:player"
        if need_pro and pro_h == 0:
            raised.append(raise_alert(
                player, "production_failure", akey6, "🏥 ویروس خونریزی‌دهنده بدون بیمارستان حرفه‌ای",
                f"ویروس‌های {', '.join(player.active_viruses)} فعال‌اند و بیمارستان حرفه‌ای ندارید — درمان خودکار ممکن نیست.",
                cause="نبود بیمارستان حرفه‌ای", severity="critical",
                recommended_action="ساخت بیمارستان حرفه‌ای (۷۰٪ شانس درمان روزانه)",
                meta={"viruses": list(player.active_viruses.keys())}, country=player.country))
        elif not need_pro and normal_h == 0:
            raised.append(raise_alert(
                player, "production_failure", akey6, "🏥 ویروس فعال بدون بیمارستان",
                "برای مهار ویروس، بیمارستان لازم است.",
                cause="نبود بیمارستان", severity="warning",
                recommended_action="ساخت بیمارستان عادی",
                meta={"viruses": list(player.active_viruses.keys())}, country=player.country))
        elif _active(akey6):
            resolve_alert(akey6)
    else:
        resolve_alert("production_failure:hospital:player")

    # ۶) دیپلماتیک — تنش بالا با همسایه
    from ..models import DiplomaticRelation
    if player.country_id:
        hot = (DiplomaticRelation.objects
               .filter(source_id=player.country_id, tension__gte=70)
               .select_related("target").first())
        akey7 = f"diplomatic_change:tension:{player.country_id}"
        if hot:
            raised.append(raise_alert(
                player, "diplomatic_change", akey7, f"⚡ تنش با {hot.target.name} در اوج",
                f"تنش {hot.tension}٪ — خطر درگیری نظامی واقعی است.",
                cause="ت tens بالا در روابط دیپلماتیک", severity="warning",
                recommended_action="ارسال پیمان عدم تجاوز یا کاهش تنش از طریق توافق",
                meta={"target": hot.target.name, "tension": hot.tension}, country=player.country))
        elif _active(akey7):
            resolve_alert(akey7)

    return raised


def serialize_alert(a: Alert) -> dict:
    return {"id": a.id, "type": a.type, "severity": a.severity, "priority": a.priority,
            "title": a.title, "description": a.description, "cause": a.cause,
            "recommended_action": a.recommended_action, "meta": a.meta,
            "status": a.status, "akey": a.akey,
            "created_at": a.created_at.isoformat(), "updated_at": a.updated_at.isoformat()}
