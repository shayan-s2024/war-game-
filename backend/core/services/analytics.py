# -*- coding: utf-8 -*-
"""Analytics داشبورد ادمین — Server-side aggregation روی داده واقعی بازی.

قانون: هیچ عددی فرانت‌محاسبه یا mock نیست؛ همه از aggregate دیتابیس می‌آید.
بازه‌ها: 1=امروز 7=هفته 30=ماه 90=فصل — فیلتر بازه سمت سرور اعمال می‌شود.
"""
import csv
import io

from django.utils import timezone
from django.db.models import Count, Sum

from ..models import (ActivityLog, AttackRecord, Base, CreditTransaction,
                      GlobalBattleEvent, Player, Sanction, Union)

DAYS = {"1": 1, "7": 7, "30": 30, "90": 90}


def _range(days):
    return timezone.now() - timezone.timedelta(days=days)


def _delta(cur, prev):
    if prev is None or prev == 0:
        return None
    return round((cur - prev) / prev * 100, 1)


def _kpi(label, value, prev=None, icon=""):
    return {"label": label, "value": value, "prev": prev,
            "change_pct": _delta(value, prev) if prev is not None else None,
            "trend": ("up" if (prev is not None and value >= prev) else
                      "down" if prev is not None else "flat"), "icon": icon}


# ==================== KPI اعداد خلاصه ====================
def kpis(days=7):
    since = _range(days)
    prev_since = _range(days * 2)
    now = timezone.now()

    players = Player.objects.filter(player_name__isnull=False)
    total_players = players.count()
    new_regs = players.filter(user__date_joined__gte=since).count()
    prev_regs = players.filter(user__date_joined__gte=prev_since,
                               user__date_joined__lt=since).count()
    dau = players.filter(last_seen__gte=_range(1)).count()
    wau = players.filter(last_seen__gte=_range(7)).count()
    mau = players.filter(last_seen__gte=_range(30)).count()
    online = Player.objects.filter(last_seen__gte=now - timezone.timedelta(minutes=15)).count()

    battles_period = AttackRecord.objects.filter(at__gte=since).count()
    prev_battles = AttackRecord.objects.filter(at__gte=prev_since, at__lt=since).count()

    tx_in = CreditTransaction.objects.filter(amount__gt=0, created_at__gte=since) \
        .aggregate(s=Sum("amount"))["s"] or 0
    tx_out = abs(CreditTransaction.objects.filter(amount__lt=0, created_at__gte=since) \
                 .aggregate(s=Sum("amount"))["s"] or 0)

    return {
        "period_days": days, "updated_at": timezone.now().isoformat(),
        "online_now": online,
        "kpis": [
            _kpi("بازیکنان کل", total_players, icon="👥"),
            _kpi("ثبت‌نام جدید", new_regs, prev_regs, icon="🆕"),
            _kpi("DAU", dau, icon="📅"),
            _kpi("WAU", wau, icon="📆"),
            _kpi("MAU", mau, icon="🗓️"),
            _kpi("آنلاین", online, icon="🟢"),
            _kpi("نبردهای دوره", battles_period, prev_battles, icon="⚔️"),
            _kpi("سکه ورودی", tx_in, icon="💰"),
            _kpi("سکه خروجی", tx_out, icon="💸"),
            _kpi("اتحادها", Union.objects.count(), icon="🤝"),
            _kpi("پایگاه‌ها", Base.objects.count(), icon="🏕️"),
            _kpi("تحریم فعال", Sanction.objects.filter(end_date__gt=now).count(), icon="🌐"),
            _kpi("بن‌شده", Player.objects.filter(banned_at__isnull=False).count(), icon="⛔"),
        ],
    }


def _daily_buckets(days, out_key):
    """ساخت اسکلت روزهای بازه با صفر پیش‌فرض"""
    d = timezone.localdate() - timezone.timedelta(days=days - 1)
    return {(d + timezone.timedelta(days=i)).isoformat(): {out_key: 0} for i in range(days)}


def _bucket_series(days, rows, dt_index, out_key):
    buckets = _daily_buckets(days, out_key)
    for dt in rows:
        key = timezone.localtime(dt).date().isoformat()
        if key in buckets:
            buckets[key][out_key] += 1
    d = timezone.localdate() - timezone.timedelta(days=days - 1)
    return [{"day": (d + timezone.timedelta(days=i)).isoformat(),
             **buckets[(d + timezone.timedelta(days=i)).isoformat()]} for i in range(days)]


# ==================== روند ثبت‌نام ====================
def registration_trend(days=30):
    rows = Player.objects.filter(player_name__isnull=False,
                                 user__date_joined__gte=_range(days)) \
        .values_list("user__date_joined", flat=True)
    return _bucket_series(days, rows, None, "count")


# ==================== روند نبرد ====================
def battle_trend(days=30):
    rows = AttackRecord.objects.filter(at__gte=_range(days)).values_list("at", flat=True)
    return _bucket_series(days, rows, None, "battles")


def battle_by_hour(days=30):
    """فعالیت نبرد بر اساس ساعت شبانه‌روز — server-side aggregate."""
    rows = AttackRecord.objects.filter(at__gte=_range(days)).values_list("at", flat=True)
    hours = [0] * 24
    for dt in rows:
        hours[timezone.localtime(dt).hour] += 1
    return [{"hour": h, "battles": c} for h, c in enumerate(hours)]


def battle_outcomes(days=30):
    """توزیع نتیجه از متن واقعی رویدادهای جهانی — همان کلیدواژه‌های combat.py"""
    ev = GlobalBattleEvent.objects.filter(created_at__gte=_range(days)) \
        .values_list("summary", flat=True)
    counts = {"victory": 0, "narrow_victory": 0, "narrow_defeat": 0, "defeat": 0}
    for s in ev:
        if "پیروزی قاطع" in s:
            counts["victory"] += 1
        elif "پیروزی سخت" in s:
            counts["narrow_victory"] += 1
        elif "شکست سنگین" in s:
            counts["defeat"] += 1
        elif "شکست نزدیک" in s:
            counts["narrow_defeat"] += 1
    return counts


def top_by_battles(days=30, limit=8):
    """برترین کشورها بر اساس تعداد نبرد — aggregate SQL."""
    rows = (AttackRecord.objects.filter(at__gte=_range(days))
            .values("player__country__name", "player__country__emoji")
            .annotate(battles=Count("id"))
            .order_by("-battles")[:limit])
    return [{"country": r["player__country__name"] or "—",
             "emoji": r["player__country__emoji"] or "🏳️",
             "battles": r["battles"]} for r in rows]


# ==================== اقتصاد ====================
def economy_overview(days=30):
    txs = CreditTransaction.objects.filter(created_at__gte=_range(days))
    by_reason = {r["reason"]: r["total"] for r in
                 txs.values("reason").annotate(total=Sum("amount")).order_by("-total")}
    supply = Player.objects.aggregate(s=Sum("credit"))["s"] or 0
    generated = sum(v for v in by_reason.values() if v > 0)
    spent = abs(sum(v for v in by_reason.values() if v < 0))
    return {
        "supply": supply, "generated": generated, "spent": spent,
        "by_reason": [{"reason": k, "total": v} for k, v in by_reason.items()],
    }


def tx_trend(days=30):
    """گردش مالی روزانه (ورودی/خروجی)"""
    txs = CreditTransaction.objects.filter(created_at__gte=_range(days)) \
        .values_list("amount", "created_at")
    buckets = {}
    for amount, dt in txs:
        day = timezone.localtime(dt).date().isoformat()
        b = buckets.setdefault(day, {"in": 0, "out": 0})
        if amount > 0:
            b["in"] += amount
        else:
            b["out"] += abs(amount)
    out = []
    d = timezone.localdate() - timezone.timedelta(days=days - 1)
    for i in range(days):
        key = (d + timezone.timedelta(days=i)).isoformat()
        b = buckets.get(key, {"in": 0, "out": 0})
        out.append({"day": key, "in": b["in"], "out": b["out"]})
    return out


# ==================== Activity ====================
def activity_by_hour(days=7):
    rows = ActivityLog.objects.filter(created_at__gte=_range(days)) \
        .values_list("created_at", flat=True)
    hours = [0] * 24
    for dt in rows:
        hours[timezone.localtime(dt).hour] += 1
    return [{"hour": h, "events": c} for h, c in enumerate(hours)]


def activity_feed(limit=40, kind=None):
    qs = ActivityLog.objects.all().order_by("-id")
    if kind:
        qs = qs.filter(kind=kind)
    return [{
        "id": a.id, "kind": a.kind, "actor": a.actor_name, "text": a.text,
        "target_id": a.target_id, "target_kind": a.target_kind,
        "created_at": a.created_at.isoformat(),
    } for a in qs[:limit]]


# ==================== Export CSV ====================
def players_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "player_name", "country", "credit", "defense", "attack_power",
                "daily_profit", "score", "population", "union", "banned"])
    for p in (Player.objects.select_related("country", "union")
              .filter(player_name__isnull=False).order_by("-score")):
        w.writerow([p.id, p.player_name, p.country.name if p.country else "",
                    p.credit, p.defense, p.attack_power, p.daily_profit, p.score,
                    p.population, p.union.name if p.union else "", bool(p.banned_at)])
    return buf.getvalue()
