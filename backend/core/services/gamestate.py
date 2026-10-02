# -*- coding: utf-8 -*-
"""توابع وضعیت بازیکن — پورت state.py و بخش تجهیزات helpers.py نسخه تلگرام.

در نسخه وب به جای دیکشنری in-memory، از PlayerItem در دیتابیس استفاده می‌شود؛
قوانین شمارش دقیقاً همان است (کلیدها: f"{item_key}_{suffix}").
"""
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from ..models import GameConfig, PlayerItem, WarEvent

from ..gamedata import (
    AIR_DEFENSES, AIRCRAFT_CARRIERS, ARTILLERY, BOMBS, BUILDINGS, DRONES, ECONOMIC_ITEMS,
    FIGHTERS, GROUND_FORCES, HACKERS, HELICOPTERS, MINES, MISSILES, NAVAL_VESSELS,
    PILOTS, SUBMARINES, TANKS, UNION_CAPACITY,
)


def get_item_qty(player, suffix, item_key):
    return PlayerItem.objects.filter(player=player, item_key=f"{item_key}_{suffix}") \
        .values_list("qty", flat=True).first() or 0


def set_item_qty(player, suffix, item_key, qty):
    obj, _ = PlayerItem.objects.update_or_create(
        player=player, item_key=f"{item_key}_{suffix}", defaults={"qty": max(0, int(qty))}
    )
    return obj.qty


def add_item_qty(player, suffix, item_key, delta):
    obj, _ = PlayerItem.objects.get_or_create(player=player, item_key=f"{item_key}_{suffix}",
                                              defaults={"qty": 0})
    obj.qty = max(0, obj.qty + int(delta))
    obj.save(update_fields=["qty"])
    return obj.qty


def get_category_count(player, category):
    """تعداد کل یک دسته سلاح — مطابق get_user_*_count"""
    _, suffix = _CATEGORY_MAP[category]
    total = PlayerItem.objects.filter(player=player, item_key__endswith=f"_{suffix}") \
        .aggregate(s=Sum("qty"))["s"] or 0
    return total


def get_category_counts(player, category):
    """دیکشنری {item_key: qty} برای یک دسته"""
    _, suffix = _CATEGORY_MAP[category]
    items = PlayerItem.objects.filter(player=player, item_key__endswith=f"_{suffix}") \
        .values_list("item_key", "qty")
    return {k.rsplit("_", 1)[0]: q for k, q in items}


def get_weighted_quality(player, category):
    """⚖️ میانگین وزنی کیفیت — مطابق weighted_quality (برمی‌گرداند (q, total))"""
    cat, _ = _CATEGORY_MAP[category]
    counts = get_category_counts(player, category)
    total = 0
    qsum = 0.0
    for key, cnt in counts.items():
        if cnt > 0 and key in cat:
            total += cnt
            qsum += cnt * cat[key].get("q", 1.0)
    if total == 0:
        return 1.0, 0
    return qsum / total, total


def recalc_attack_power(player):
    """بازمحاسبه قدرت تخریب از روی تجهیزات — مطابق reduce_user_weapon"""
    total = 0
    for category in ("tank", "fighter", "helicopter", "drone", "navy", "submarine",
                     "missile", "artillery", "ground", "bomb"):
        cat, suffix = _CATEGORY_MAP.get(category, (None, None))
        if not cat:
            continue
        for key, item in cat.items():
            total += get_item_qty(player, suffix, key) * item.get("power", 0)
    player.attack_power = total
    player.save(update_fields=["attack_power"])
    return total


def recalc_defense(player):
    """دفاع = ۵۰۰۰ پایه + قدرت پدافندها — مطابق بخش air_defense در reduce_user_weapon"""
    total = 0
    for key, item in AIR_DEFENSES.items():
        total += get_item_qty(player, "air_defense_count", key) * item["power"]
    player.defense = settings.GAME["START_DEFENSE"] + total
    player.save(update_fields=["defense"])
    return player.defense


_CATEGORY_MAP = {
    "tank": (TANKS, "tank_count"),
    "fighter": (FIGHTERS, "fighter_count"),
    "helicopter": (HELICOPTERS, "helicopter_count"),
    "drone": (DRONES, "drone_count"),
    "navy": (NAVAL_VESSELS, "naval_count"),
    "submarine": (SUBMARINES, "submarine_count"),
    "missile": (MISSILES, "missile_count"),
    "artillery": (ARTILLERY, "artillery_count"),
    "air_defense": (AIR_DEFENSES, "air_defense_count"),
    "ground": (GROUND_FORCES, "ground_count"),
    "carrier": (AIRCRAFT_CARRIERS, "carrier_count"),
    "hacker": (HACKERS, "hacker_count"),
    "bomb": (BOMBS, "bomb_count"),
    "mine": (MINES, "count"),
    "economic": (ECONOMIC_ITEMS, "count"),
    "building": (BUILDINGS, "count"),
    "pilot": (PILOTS, "pilot_count"),
}

CATEGORY_MAP = _CATEGORY_MAP


def get_config(key, default=None):
    row = GameConfig.objects.filter(key=key).first()
    return row.value if row else default


def set_config(key, value):
    GameConfig.objects.update_or_create(key=key, defaults={"value": str(value)})


def delete_config(key):
    GameConfig.objects.filter(key=key).delete()


def get_game_day():
    """روز بازی از زمان شروع — مطابق get_game_day"""
    start = get_config("game_start_date")
    if not start:
        set_config("game_start_date", str(timezone.now().timestamp()))
        return 1
    try:
        elapsed = timezone.now().timestamp() - float(start)
        return int(elapsed // 86400) + 1
    except (TypeError, ValueError):
        return 1


def is_virus_active():
    day = get_game_day()
    start_day = int(get_config("virus_start_day", settings.GAME["VIRUS_START_DAY"]))
    return day >= start_day


def is_war_allowed():
    """جنگ دستی یا زمان‌بندی‌شده — مطابق is_war_allowed"""
    ev = WarEvent.objects.filter(active=True).order_by("-id").first()
    if not ev:
        return False
    now = timezone.now()
    if ev.start_time is None and ev.end_time is None:
        return True
    if ev.start_time and now < ev.start_time:
        return False
    if ev.end_time and now > ev.end_time:
        return False
    return True


def get_war_event():
    return WarEvent.objects.filter(active=True).order_by("-id").first()


def get_pilot_type_for_fighter(fighter_key):
    for ptype, pinfo in PILOTS.items():
        if pinfo.get("for_type") == "helicopter":
            continue
        if fighter_key in pinfo.get("fighters", []):
            return ptype
    return None


def get_ready_fighters(player):
    """جنگنده آماده = min(جنگنده، خلبان مربوطه) برای هر مدل — مطابق get_user_fighter_count_with_pilot"""
    counts = get_category_counts(player, "fighter")
    total = 0
    for fkey, fcount in counts.items():
        ptype = get_pilot_type_for_fighter(fkey)
        if ptype:
            pcount = get_item_qty(player, "pilot_count", ptype)
            total += min(fcount, pcount)
    return total


def get_ready_helicopters(player):
    heli_total = get_category_count(player, "helicopter")
    pilot_count = get_item_qty(player, "pilot_count", "helicopter")
    return min(heli_total, pilot_count)


def get_union_capacity(level):
    return UNION_CAPACITY.get(level, 2)


def get_sanction(player):
    """تحریم فعال بازیکن — برمی‌گرداند (active, penalty, end_date)"""
    s = getattr(player, "sanction", None)
    if not s:
        return False, 0, None
    now = timezone.now()
    if s.end_date and s.end_date <= now:
        s.delete()
        return False, 0, None
    return True, s.price_penalty, s.end_date
