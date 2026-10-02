# -*- coding: utf-8 -*-
"""اقتصاد — پورت کامل shop.py: خرید همه دسته‌ها با سقف تجهیزات، جریمه تحریم و audit تراکنش."""
from ..gamedata import (
    AIR_DEFENSES, AIRCRAFT_CARRIERS, ARTILLERY, BOMBS, BUILDINGS, DRONES, ECONOMIC_ITEMS,
    FIGHTERS, GROUND_FORCES, HACKERS, HELICOPTERS, MINES, MISSILES, NAVAL_VESSELS,
    PILOTS, SHOP_PRICE_MULTIPLIER, SUBMARINES, TANKS,
)
from . import gamestate as gs
from .combat import change_credit

# دسته → (دیکشنری، پسوند شمارنده)
BUY_CATEGORIES = {
    "mine": (MINES, "count"),
    "economic": (ECONOMIC_ITEMS, "count"),
    "defense": (AIR_DEFENSES, "air_defense_count"),
    "tank": (TANKS, "tank_count"),
    "fighter": (FIGHTERS, "fighter_count"),
    "helicopter": (HELICOPTERS, "helicopter_count"),
    "missile": (MISSILES, "missile_count"),
    "drone": (DRONES, "drone_count"),
    "naval": (NAVAL_VESSELS, "naval_count"),
    "submarine": (SUBMARINES, "submarine_count"),
    "carrier": (AIRCRAFT_CARRIERS, "carrier_count"),
    "ground": (GROUND_FORCES, "ground_count"),
    "artillery": (ARTILLERY, "artillery_count"),
    "hacker": (HACKERS, "hacker_count"),
    "bomb": (BOMBS, "bomb_count"),
    "pilot": (PILOTS, "pilot_count"),
    "building": (BUILDINGS, "count"),
}

# دسته‌هایی که هر واحد خرید = item.count عدد (بسته‌ای، مطابق تلگرام)
BUNDLE_CATEGORIES = {"defense", "tank", "fighter", "helicopter", "missile", "drone",
                     "naval", "submarine", "carrier", "ground", "artillery", "hacker",
                     "bomb", "pilot"}


def get_sanction_penalty(player):
    from .gamestate import get_sanction
    active, penalty, _ = get_sanction(player)
    return penalty if active else 0.0


def effective_price(player, base_price):
    penalty = get_sanction_penalty(player)
    return int(base_price * SHOP_PRICE_MULTIPLIER * (1 + penalty)), penalty


def purchase(player, category, item_key, count):
    """🛒 خرید از فروشگاه — منطق کامل process_buy_item با سقف cap/max، تحریم و audit"""
    if category not in BUY_CATEGORIES:
        return {"ok": False, "error": "دسته نامعتبر"}
    catalog, suffix = BUY_CATEGORIES[category]
    item = catalog.get(item_key)
    if not item:
        return {"ok": False, "error": "آیتم نامعتبر"}
    if count < 1 or count > 1000:
        return {"ok": False, "error": "تعداد نامعتبر"}

    price_per_unit, penalty = effective_price(player, item["price"])
    bundle = item.get("count", 1) if category in BUNDLE_CATEGORIES else 1
    total_price = price_per_unit * count
    total_units = bundle * count

    # 🚫 سقف تجهیزات (cap/max) — مطابق _CAT_MAP تلگرام
    cap = item.get("cap", item.get("max"))
    current = gs.get_item_qty(player, suffix, item_key)
    if cap is not None and current + total_units > cap:
        return {"ok": False,
                "error": f"سقف تجهیزات! حداکثر {cap:,} عدد از {item['name']} می‌توانید داشته باشید (فعلاً {current:,})"}

    if player.credit < total_price:
        shortage = total_price - player.credit
        return {"ok": False, "error": f"موجودی کافی نیست! کمبود: {shortage:,} سکه"}

    # کسر پول + audit — (برخی کالاها مثل پهپاد cap ندارند مطابق نسخه تلگرام)
    change_credit(player, -total_price, "purchase",
                  {"category": category, "item": item_key, "count": count,
                   "sanction_penalty": penalty})

    gs.add_item_qty(player, suffix, item_key, total_units)

    # اعمال اثرات — مطابق process_buy_item
    effects = {}
    if category == "mine":
        profit = item["daily_profit"] * count
        player.daily_profit += profit
        effects["daily_profit"] = profit
    elif category == "economic":
        profit = item["profit"] * count
        player.daily_profit += profit
        effects["daily_profit"] = profit
    elif category == "defense":
        power = item["power"] * total_units
        player.defense += power
        effects["defense"] = power
    elif category in ("tank", "fighter", "helicopter", "missile", "drone", "naval",
                      "submarine", "artillery", "ground", "bomb"):
        power = item["power"] * total_units
        player.attack_power += power
        effects["attack_power"] = power
    player.save(update_fields=["daily_profit", "defense", "attack_power"])

    result = {
        "ok": True, "item_name": item["name"], "units": total_units,
        "total_price": total_price, "sanction_penalty": int(penalty * 100),
        "credit_left": player.credit, "effects": effects,
    }
    if item.get("description"):
        result["description"] = item["description"]
    return result


# ==================== اقتصاد شبانه ====================
def apply_daily_profit(player):
    """سود شبانه + درمان شانسی ویروس با بیمارستان + تربیت سرباز پادگان
    — پورت کامل check_and_add_daily_profit
    """
    import random
    from ..gamedata import VIRUSES

    profit = player.daily_profit
    if profit > 0:
        change_credit(player, profit, "daily_profit", {})
    healed_viruses = []
    normal_h = gs.get_item_qty(player, "count", "normal_hospital")
    pro_h = gs.get_item_qty(player, "count", "professional_hospital")
    if normal_h > 0 or pro_h > 0:
        for vkey in list(player.active_viruses.keys()):
            needed = VIRUSES[vkey].get("hospital_needed", "normal")
            if needed == "normal" and normal_h > 0 and random.random() < 0.5:
                del player.active_viruses[vkey]
                healed_viruses.append(VIRUSES[vkey]["name"])
            elif needed == "professional" and pro_h > 0 and random.random() < 0.7:
                del player.active_viruses[vkey]
                healed_viruses.append(VIRUSES[vkey]["name"])
    # 🛕 پادگان: هر شب ۵ سرباز به ازای هر پادگان (سقف ۱۰۰۰ از count نسخه تلگرام)
    barracks = gs.get_item_qty(player, "count", "barracks")
    produced_soldiers = 0
    if barracks > 0:
        cap = GROUND_FORCES["normal_soldier"]["count"]
        cur = gs.get_item_qty(player, "ground_count", "normal_soldier")
        produced_soldiers = min(5 * barracks, max(0, cap - cur))
        if produced_soldiers > 0:
            gs.add_item_qty(player, "ground_count", "normal_soldier", produced_soldiers)
    if healed_viruses or produced_soldiers:
        player.save(update_fields=["active_viruses"])
    return {"profit": profit, "healed_viruses": healed_viruses,
            "soldiers_trained": produced_soldiers}


def apply_fire_burn(player):
    """🔥 آتش‌سوزی بمب آتش‌زا: تا ۳ روز، ۳٪ تلفات جمعی (مترو محافظ)"""
    from django.utils import timezone

    from .combat import metro_shelter_factor
    if not player.on_fire_until or player.on_fire_until <= timezone.now():
        return 0
    burn = int(player.population * 0.03 * metro_shelter_factor(player))
    if burn > 0:
        player.population = max(0, player.population - burn)
        player.save(update_fields=["population"])
    return burn


def apply_virus_damage(player, current_day):
    """🦠 آسیب روزانه ویروس — پورت apply_virus_damage (مترو تلفات را کم می‌کند)"""
    from .combat import metro_shelter_factor
    changed = False
    reports = []
    for vkey, vdata in list(player.active_viruses.items()):
        vdata["remaining_days"] -= 1
        if vdata["remaining_days"] <= 0:
            del player.active_viruses[vkey]
            reports.append({"virus": vkey, "cured": True})
        else:
            if vdata.get("damage_base", False):
                player.defense = max(0, player.defense - 50)
            pop_loss = int(vdata.get("daily_loss", 0) * metro_shelter_factor(player))
            if pop_loss > 0:
                player.population = max(0, player.population - pop_loss)
            reports.append({"virus": vkey, "cured": False, "pop_loss": pop_loss})
        changed = True
    if changed:
        player.save(update_fields=["active_viruses", "defense", "population"])
    return reports
