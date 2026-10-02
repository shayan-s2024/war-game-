# -*- coding: utf-8 -*-
"""دستاوردها — ویژگی گیمیفیکیشن نسخه وب (بند ۱۷ اسپک).

منطق: بعد از اکشن‌های مهم (خرید، نبرد، هک، اتحاد، دعوت) evaluate_achievements
فراخوانی می‌شود؛ شرط‌های برقرار → قفل‌گشایی یک‌بارمصرف + جایزه سکه با audit + اعلان.
"""
from ..gamedata import ACHIEVEMENTS
from ..models import (
    AssassinationInfo, AttackRecord, Base, Notification, PlayerAchievement,
)
from . import gamestate as gs


def _metric_value(player, ach):
    """مقدار فعلی متریک یک دستاورد — هر شرط حداکثر یک query."""
    cond = ach["condition"]
    if cond == "credit_gte":
        return player.credit
    if cond == "daily_profit_gte":
        return player.daily_profit
    if cond == "defense_gte":
        return player.defense
    if cond == "attack_power_gte":
        return player.attack_power
    if cond == "population_gte":
        return player.population
    if cond == "score_gte":
        return player.score
    if cond == "battles_total_gte":
        return AttackRecord.objects.filter(player=player).count()
    if cond == "codes_stolen_gte":
        return AssassinationInfo.objects.filter(hacker=player).count()
    if cond == "bases_count_gte":
        return Base.objects.filter(owner=player).count()
    if cond == "union_level_gte":
        return player.union.level if player.union_id else 0
    if cond == "invite_count_gte":
        return player.invite_count
    if cond == "item_total_gte":
        return gs.get_category_count(player, _category_for_suffix(ach["suffix"]))
    if cond == "item_key_gte":
        return gs.get_item_qty(player, ach["suffix"], ach["item_key"])
    return 0


def _category_for_suffix(suffix):
    """دسته دسته‌بندی برای یک پسوند شمارنده — برای شرط item_total."""
    for category, (_cat, sfx) in gs.CATEGORY_MAP.items():
        if sfx == suffix:
            return category
    return "tank"


def evaluate_achievements(player):
    """بررسی همه دستاوردها؛ موارد جدید را قفل‌گشایی و جایزه می‌دهد.

    خروجی: لیست دستاوردهای تازه باز‌شده (برای نمایش celebration در فرانت).
    """
    from .combat import change_credit, notify

    unlocked_now = []
    existing = set(PlayerAchievement.objects.filter(player=player)
                   .values_list("achievement_key", flat=True))
    for key, ach in ACHIEVEMENTS.items():
        if key in existing:
            continue
        if _metric_value(player, ach) >= ach["threshold"]:
            PlayerAchievement.objects.create(player=player, achievement_key=key)
            change_credit(player, ach["reward"], "achievement_reward",
                          {"achievement": key})
            notify(player, "reward", f"🏆 دستاورد باز شد: {ach['name']}",
                   f"{ach['icon']} {ach['description']}\nجایزه: {ach['reward']:,} سکه")
            unlocked_now.append(key)
    return unlocked_now


def achievement_overview(player):
    """وضعیت کامل دستاوردها برای API — باز‌شده‌ها + پیشرفت بقیه."""
    from django.utils import timezone as tz

    existing = {pa.achievement_key: pa.unlocked_at
                for pa in PlayerAchievement.objects.filter(player=player)}
    items = []
    unlocked_count = 0
    for key, ach in ACHIEVEMENTS.items():
        done = key in existing
        if done:
            unlocked_count += 1
        else:
            # پیشرفت فعلی نسبت به آستانه (سقف ۱۰۰٪)
            val = _metric_value(player, ach)
            progress = min(100, int(val * 100 / max(1, ach["threshold"])))
        items.append({
            "key": key, "name": ach["name"], "icon": ach["icon"],
            "tier": ach["tier"], "description": ach["description"],
            "reward": ach["reward"], "threshold": ach["threshold"],
            "unlocked": done,
            "unlocked_at": existing[key].isoformat() if done else None,
            "progress": 100 if done else (progress if not done else 0),
        })
    return {
        "achievements": items,
        "unlocked_count": unlocked_count,
        "total_count": len(ACHIEVEMENTS),
    }
