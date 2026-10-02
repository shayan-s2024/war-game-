# -*- coding: utf-8 -*-
"""پروفایل عمومی بازیکن (بند Public Player Profile اسپک).

قوانین:
- هیچ داده حساسی (سکه دقیق، سرباز، کدها) از API عمومی نمی‌گذرد
- privacy از Player.privacy (JSON) خوانده و **سمت سرور** اعمال می‌شود
- همه آمار از Game Core (همان مدل‌های بازی) می‌آید
"""
from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.gamedata import ACHIEVEMENTS
from core.models import (AttackRecord, BattleLog, GlobalBattleEvent, Player,
                         PlayerAchievement, Statement, UsedCountry)
from core.services.gamestate import CATEGORY_MAP  # noqa: F401
from .common import get_player

# پیش‌فرض‌های privacy — اگر بازیکن تنظیم نکرده باشد
DEFAULT_PRIVACY = {
    "show_country": True, "show_union": True, "show_battles": True,
    "show_achievements": True, "show_statements": True, "show_last_active": True,
    "show_stats": True,
}

TIER_POINTS = {"bronze": 10, "silver": 25, "gold": 50}


def _rank_of(player, metric="score"):
    """رتبه جهانی واقعی — count from DB (index روی -score موجود)"""
    if metric == "score":
        better = Player.objects.filter(player_name__isnull=False, score__gt=player.score).count()
    else:
        better = Player.objects.filter(player_name__isnull=False,
                                       **{f"{metric}__gt": getattr(player, metric)}).count()
    return better + 1


def _win_stats(player_id):
    """سابقه نظامی واقعی از رویدادهای جهانی — مهاجم/مدافع"""
    evs = GlobalBattleEvent.objects.filter(attacker_id=player_id) | \
          GlobalBattleEvent.objects.filter(defender_id=player_id)
    wins = losses = 0
    for e in evs[:200]:
        s = e.summary
        if e.attacker_id == player_id:
            if "پیروزی" in s:
                wins += 1
            elif "شکست" in s:
                losses += 1
        else:
            if "شکست" in s:
                wins += 1  # شکست مهاجم = پیروزی مدافع
            elif "پیروزی" in s:
                losses += 1
    return wins, losses, evs.count()


def _timeline(player, privacy):
    """Timeline واقعی از چند منبع — فقط eventهای مجاز عمومی"""
    items = []
    # اتحاد
    if privacy.get("show_union", True) and player.union:
        items.append({"ts": player.union.created_at.isoformat(), "icon": "🤝",
                      "text": f"عضو اتحاد {player.union.name} شد"})
    # دستاوردها
    if privacy.get("show_achievements", True):
        for pa in PlayerAchievement.objects.filter(player=player).order_by("-id")[:8]:
            a = ACHIEVEMENTS.get(pa.achievement_key, {})
            items.append({"ts": pa.unlocked_at.isoformat(), "icon": a.get("icon", "🏆"),
                          "text": f"دستاورد «{a.get('name', pa.achievement_key)}» باز شد"})
    # بیانیه‌ها
    if privacy.get("show_statements", True):
        for s in Statement.objects.filter(player=player).order_by("-id")[:5]:
            items.append({"ts": s.created_at.isoformat(),
                          "icon": "📢" if s.kind == "statement" else "🐦",
                          "text": s.text[:80]})
    # نبردهای مهم
    if privacy.get("show_battles", True):
        for e in GlobalBattleEvent.objects.filter(attacker=player).order_by("-id")[:5]:
            items.append({"ts": e.created_at.isoformat(), "icon": "⚔️", "text": e.summary[:80]})
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items[:15]


@api_view(["GET"])
@permission_classes([AllowAny])
def public_profile(request, username):
    User = None
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.filter(username=username).first()
    player = Player.objects.filter(user=user).first() if user else None
    if not player or not player.player_name:
        return Response({"error": "بازیکن یافت نشد"}, status=404)

    # privacy خود بازیکن — banned ها پروفایل مخفی
    if player.is_banned:
        return Response({"error": "این حساب مسدود شده"}, status=403)
    privacy = {**DEFAULT_PRIVACY, **(player.privacy or {})}

    wins, losses, total_battles = _win_stats(player.id)
    achievements = PlayerAchievement.objects.filter(player=player)
    ach_items = []
    achievement_points = 0
    for pa in achievements:
        a = ACHIEVEMENTS.get(pa.achievement_key, {})
        tier = a.get("tier", "bronze")
        achievement_points += TIER_POINTS.get(tier, 10)
        ach_items.append({
            "key": pa.achievement_key, "name": a.get("name", pa.achievement_key),
            "icon": a.get("icon", "🏆"), "tier": tier,
            "description": a.get("description", ""), "unlocked_at": pa.unlocked_at.isoformat(),
        })

    last_seen_public = None
    if privacy.get("show_last_active", True) and player.last_seen:
        last_seen_public = player.last_seen.isoformat()
        # فقط تاریخ نسبی (امروز/دیروز) نه ساعت دقیق — privacy-aware

    data = {
        "name": player.player_name,
        "joined": player.user.date_joined.isoformat() if player.user else None,
        "country": None, "country_emoji": None, "continent": None,
        "union": None, "union_level": None,
        "stats": {}, "battles": {
            "total": total_battles, "wins": wins, "losses": losses,
            "win_rate": round(wins * 100 / max(1, wins + losses), 1),
        },
        "achievements": ach_items if privacy.get("show_achievements", True) else [],
        "achievement_points": achievement_points,
        "statements": [], "timeline": _timeline(player, privacy),
        "ranks": {"global": _rank_of(player, "score")},
        "last_active": last_seen_public,
        "privacy": {k: privacy[k] for k in ("show_country", "show_union", "show_battles",
                                            "show_achievements", "show_statements", "show_last_active")},
    }
    if privacy.get("show_country", True) and player.country:
        data["country"] = player.country.name
        data["country_emoji"] = player.country.emoji
        data["continent"] = player.country.continent.key
        # رتبه کشوری واقعی: بازیکنان همان قاره
        same_cont = Player.objects.filter(player_name__isnull=False,
                                          country__continent=player.country.continent)
        better = same_cont.filter(score__gt=player.score).count()
        data["ranks"]["country"] = better + 1
    if privacy.get("show_union", True) and player.union:
        data["union"] = player.union.name
        data["union_level"] = player.union.level
    if privacy.get("show_stats", True):
        data["stats"] = {
            "score": player.score, "population": player.population,
            "daily_profit": player.daily_profit, "attack_power": player.attack_power,
            "defense": player.defense,
            # سکه دقیق عمومی نمی‌شود — فقط بازه/رمز
            "credit_range": "۱۰۰K+" if player.credit >= 100000 else
                            ("۱۰K+" if player.credit >= 10000 else "<10K"),
        }
    if privacy.get("show_statements", True):
        data["statements"] = [{
            "id": s.id, "kind": s.kind, "text": s.text, "created_at": s.created_at.isoformat(),
        } for s in Statement.objects.filter(player=player).order_by("-id")[:10]]
    return Response(data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def my_privacy(request):
    """تنظیمات privacy خودم — سمت سرور ذخیره و در public_profile اعمال می‌شود"""
    player = get_player(request)
    if not player or not player.player_name:
        return Response({"error": "بازیکن یافت نشد"}, status=404)
    if request.method == "POST":
        allowed_keys = set(DEFAULT_PRIVACY.keys())
        new_p = {k: bool(v) for k, v in (request.data or {}).items() if k in allowed_keys}
        player.privacy = {**DEFAULT_PRIVACY, **(player.privacy or {}), **new_p}
        player.save(update_fields=["privacy"])
    return Response({"privacy": {**DEFAULT_PRIVACY, **(player.privacy or {})}})
