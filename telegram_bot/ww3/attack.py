import requests
import json
import os
import time
import random
import math
import sqlite3
import re
from datetime import datetime, timedelta

from . import state
from .config import ATTACK_LIMIT
from .helpers import WEAPON_CATEGORIES, add_attack_record, calculate_battle_power, can_attack, get_country_continent_key, get_pilot_type_for_fighter, get_user_air_defense_count, get_user_drone_count, get_user_fighter_count, get_user_fighter_count_with_pilot, get_user_helicopter_count, get_user_helicopter_count_with_pilot, get_user_missile_count, get_user_navy_count, get_user_submarine_count, get_user_tank_count, hospital_heal, is_defense_disabled, is_missile_disabled, is_war_allowed, log_battle, metro_shelter_factor, send_message, send_to_group, show_screen, weighted_quality
from .state import bases_data, db, players_data, waiting_for_attack_count, waiting_for_attack_search, waiting_for_attack_target
from .static_data import AIR_DEFENSES, ARTILLERY, BOMBS, BUILDINGS, CONTINENT_NAMES, DRONES, FIGHTERS, HELICOPTERS, MISSILES, NAVAL_VESSELS, SUBMARINES, TANKS, WEAPONS_SYSTEM

# ==================== ماژول attack ====================


# ==================== 💣💥 تسلیحات ویژه: بمب‌افکن استراتژیک و توپخانه ====================
def get_user_artillery_total(user_id):
    return sum(players_data.get(user_id, {}).get(f"{k}_artillery_count", 0) for k in ARTILLERY)


def get_user_artillery_type_count(user_id, art_key):
    return players_data.get(user_id, {}).get(f"{art_key}_artillery_count", 0)


def reduce_artillery(user_id, amount):
    """کاهش توپخانه (از بزرگ‌ترین دسته اول)"""
    p = players_data.get(user_id)
    if not p or amount <= 0:
        return
    remaining = amount
    for k in sorted(ARTILLERY, key=lambda k: -p.get(f"{k}_artillery_count", 0)):
        if remaining <= 0:
            break
        cur = p.get(f"{k}_artillery_count", 0)
        take = min(cur, remaining)
        p[f"{k}_artillery_count"] = cur - take
        remaining -= take


def _dock_loot_bonus(user, weapon, base_loot):
    """⛴️ اسکله: غنیمت حملات دریایی تا ۲ برابر (هر اسکله ۱۵٪)"""
    if weapon not in ("navy", "submarine"):
        return base_loot
    docks = user.get("dock_count", 0)
    if docks <= 0:
        return base_loot
    return int(base_loot * (1 + min(1.0, 0.15 * docks)))


def attack_bombs_menu(chat_id, user_id):
    if not is_war_allowed():
        show_screen(chat_id, "⛔ **جنگ جهانی فعال نیست!**\n\nفعلاً نمی‌توانید حمله کنید.")
        return
    user = players_data.get(user_id, {})
    descs = {"fire": "🔥 ۳ روز شهر حریف در آتش", "space": "🛰 پدافند بی‌اثر + نابودی هواپیماها",
             "continental": "☢️ برد جهانی + نابودی ساختمان‌ها"}
    rows = []
    any_bomb = False
    for key, b in BOMBS.items():
        owned = user.get(f"{key}_bomb_count", 0)
        if owned > 0:
            any_bomb = True
        rows.append([{"text": f"{b['icon']} {b['name']} | موجودی: {owned} | {descs[key]}",
                      "callback_data": f"bomb_type_{key}"}])
    if not any_bomb:
        show_screen(chat_id, "❌ **هیچ بمبی ندارید!**\n💣 بمب‌ها را از فروشگاه بخش بمب بخرید.")
        return
    rows.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    show_screen(chat_id,
        "💣 **بمب‌افکن استراتژیک**\n━━━━━━━━━━━━━━━━━━\n"
        "⚠️ هر بمب یک‌بارمصرف است و ویرانی عظیم به بار می‌آورد!\n"
        "📌 هر حمله بمب‌افکن جزو سهمیه حملات روزانه شماست.\n━━━━━━━━━━━━━━━━━━\nنوع بمب را انتخاب کنید:",
        {"inline_keyboard": rows})


def bomb_targets_menu(chat_id, user_id, bomb_key):
    b = BOMBS.get(bomb_key)
    user = players_data.get(user_id, {})
    if not b or user.get(f"{bomb_key}_bomb_count", 0) <= 0:
        show_screen(chat_id, "❌ از این بمب موجودی ندارید!")
        return
    if bomb_key == "continental":
        targets = [t for t, d in players_data.items() if t != user_id and d.get("player_name")]
    else:
        targets = get_available_targets(user_id, "missile")
    if not targets:
        show_screen(chat_id, "❌ **هیچ هدفی در برد این بمب نیست!**")
        return
    keyboard = [[{"text": f"🎯 {players_data[t].get('player_name', 'نامشخص')}",
                  "callback_data": f"bomb_target_{t}_{bomb_key}"}] for t in targets[:10]]
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_bombs"}])
    rng = "🌍 همه قاره‌ها" if bomb_key == "continental" else "📍 قاره شما + قاره پایگاه‌هایتان"
    show_screen(chat_id,
        f"💣 **حمله با {b['name']}**\n━━━━━━━━━━━━━━━━━━\n"
        f"📊 موجودی: {user.get(f'{bomb_key}_bomb_count', 0)}\n🎯 برد: {rng}\n━━━━━━━━━━━━━━━━━━\nهدف را انتخاب کنید:",
        {"inline_keyboard": keyboard})


def ask_bomb_count(chat_id, user_id, target_id, bomb_key):
    b = BOMBS.get(bomb_key)
    owned = players_data.get(user_id, {}).get(f"{bomb_key}_bomb_count", 0)
    if not b or owned <= 0:
        show_screen(chat_id, "❌ از این بمب موجودی ندارید!")
        return
    waiting_for_attack_count[user_id] = {"target_id": target_id, "weapon": f"bomb_{bomb_key}", "max_count": owned}
    keyboard = {"inline_keyboard": [
        [{"text": "1", "callback_data": "attack_count_1"}, {"text": "2", "callback_data": "attack_count_2"},
         {"text": "3", "callback_data": "attack_count_3"}, {"text": "5", "callback_data": "attack_count_5"}],
        [{"text": f"همه ({owned})", "callback_data": f"attack_count_{owned}"}],
        [{"text": "🔙 انصراف", "callback_data": "attack_bombs"}]
    ]}
    show_screen(chat_id,
        f"💣 **ریختن {b['name']} روی {players_data.get(target_id, {}).get('player_name', 'نامشخص')}**\n"
        f"━━━━━━━━━━━━━━━━━━\n📊 بمب موجود: {owned}\n🔢 چند بمب بیندازیم؟",
        keyboard)


def process_bomb_strike(chat_id, user_id, target_id, bomb_key, count):
    """💣 حمله بمب‌افکن — ویرانی استراتژیک؛ هر بمب یک‌بارمصرف"""
    bomb = BOMBS.get(bomb_key)
    if not bomb:
        send_message(chat_id, "❌ بمب نامعتبر!")
        return
    if not is_war_allowed():
        send_message(chat_id, "⛔ **جنگ جهانی فعال نیست!**")
        return
    can_flag, remaining, wait_time = can_attack(user_id)
    if not can_flag:
        hours, minutes = wait_time
        send_message(chat_id, f"❌ **سهمیه حملات شما تمام شده!**\n⏳ {hours} ساعت {minutes} دقیقه دیگر")
        return
    if target_id == user_id:
        return
    target = players_data.get(target_id, {})
    if not target.get("player_name"):
        send_message(chat_id, "❌ هدف نامعتبر است!")
        return
    user = players_data.get(user_id, {})
    owned = user.get(f"{bomb_key}_bomb_count", 0)
    if owned <= 0:
        send_message(chat_id, "❌ از این بمب موجودی ندارید!")
        return
    count = max(1, min(count, owned))

    old_def = target.get("defense", 5000)
    base_damage = bomb["power"] * count
    extra_lines = []
    if bomb_key == "fire":
        _ad_q, _ad_n = weighted_quality(target_id, AIR_DEFENSES, "air_defense_count")
        intercept_pct = min(55, int(_ad_n * _ad_q * 2))
        intercepted = int(base_damage * intercept_pct / 100)
        damage = base_damage - intercepted
        if intercepted > 0:
            extra_lines.append(f"🛡 پدافند حریف {intercept_pct}٪ از بمب‌ها را رهگیری کرد ({intercepted:,} آسیب کمتر)")
        else:
            extra_lines.append("🛡 پدافند حریف هیچ بمبی را رهگیری نکرد!")
        players_data[target_id]["on_fire_until"] = time.time() + 3 * 86400
        extra_lines.append("🔥 **شهر هدف در آتش گرفت!** ۳ روز آتش‌سوزی و تلفات جمعی")
    elif bomb_key == "space":
        _high_def = (target.get("iron_dome_air_defense_count", 0) * 1.7 * 6
                     + target.get("s400_air_defense_count", 0) * 1.2 * 4)
        _pct = min(60, int(_high_def))
        if _pct > 0:
            _saved = int(base_damage * _pct / 100)
            damage = base_damage - _saved
            extra_lines.append(f"🛡 پدافند پیشرفته حریف {_pct}٪ بمب فضایی را دفع کرد ({_saved:,} آسیب کمتر)")
        else:
            damage = base_damage
        destroyed = 0
        for cat, suffix in ((FIGHTERS, "_fighter_count"), (HELICOPTERS, "_helicopter_count"), (DRONES, "_drone_count")):
            for k in cat:
                cur = target.get(f"{k}{suffix}", 0)
                if cur > 0:
                    kill = min(cur, max(1, int(cur * 0.15 * count)))
                    players_data[target_id][f"{k}{suffix}"] = cur - kill
                    destroyed += kill
        if destroyed > 0:
            extra_lines.append(f"💥 {destroyed} هواپیمای حریف روی زمین نابود شد!")
        extra_lines.append("🛰 ضربه از فضا — پدافند هوایی حریف کاملاً بی‌اثر بود")
    else:
        _high_def = (target.get("iron_dome_air_defense_count", 0) * 1.7 * 5
                     + target.get("s400_air_defense_count", 0) * 1.2 * 3)
        _pct = min(50, int(_high_def * 0.8))
        if _pct > 0:
            damage = int(base_damage * 1.2 * (100 - _pct) / 100)
            extra_lines.append(f"🛡 پدافند پیشرفته حریف {_pct}٪ بمب قاره‌ای را خنثی کرد")
        else:
            damage = int(base_damage * 1.2)
        destroyed_b = []
        for bkey in ("metro", "airport", "dock", "normal_hospital", "professional_hospital", "barracks"):
            bcount = target.get(f"{bkey}_count", 0)
            if bcount > 0 and random.random() < min(0.9, 0.5 * count):
                players_data[target_id][f"{bkey}_count"] = bcount - 1
                destroyed_b.append(BUILDINGS[bkey]["name"])
        pop_loss = int(target.get("population", 10000) * 0.05 * count)
        if target.get("metro_count", 0) > 0:
            pop_loss = int(pop_loss * metro_shelter_factor(target_id))
            extra_lines.append("🚉 متروهای حریف جان بخشی از مردم را نجات داد")
        players_data[target_id]["population"] = max(0, target.get("population", 10000) - pop_loss)
        if pop_loss > 0:
            extra_lines.append(f"👥 {pop_loss:,} نفر تلفات غیرنظامی")
        if destroyed_b:
            extra_lines.append("🏚 ساختمان‌های نابودشده: " + "، ".join(destroyed_b))
        extra_lines.append("☢️ بمب قاره‌ای: برد جهانی — پدافند بی‌اثر")

    new_def = max(0, old_def - damage)
    players_data[target_id]["defense"] = new_def
    players_data[user_id][f"{bomb_key}_bomb_count"] = owned - count

    score_change = min(30, 5 + damage // 3000)
    players_data[user_id]["score"] = user.get("score", 0) + score_change
    players_data[target_id]["score"] = max(0, target.get("score", 0) - score_change)
    loot = random.randint(15000, 40000)
    players_data[user_id]["credit"] = user.get("credit", 0) + loot
    players_data[target_id]["credit"] = max(0, target.get("credit", 0) - loot // 2)
    db.save_player(user_id, players_data[user_id])
    db.save_player(target_id, players_data[target_id])
    add_attack_record(user_id)
    log_battle(user_id, target_id,
               f"💣 {bomb['name']}×{count} روی {target.get('player_name', 'نامشخص')} — آسیب {damage:,}")

    result_text = (
        f"{bomb['icon']} **حمله بمب‌افکن موفق بود!**\n━━━━━━━━━━━━━━━━━━\n"
        f"💣 {bomb['name']} × {count}\n"
        f"💥 آسیب به دفاع حریف: {damage:,}\n"
        f"🛡 دفاع حریف: {old_def:,} ← {new_def:,}\n"
        f"💰 غنیمت: {loot:,} سکه\n🏆 امتیاز: +{score_change}\n"
        f"💣 بمب باقیمانده: {owned - count}\n━━━━━━━━━━━━━━━━━━\n" + "\n".join(extra_lines))
    send_message(chat_id, result_text)
    send_message(int(target_id),
        f"🚨 **{bomb['name']} روی شهر شما فرود آمد!**\n"
        f"👤 مهاجم: {user.get('player_name', 'نامشخص')}\n"
        f"💥 {damage:,} آسیب به دفاع\n🛡 دفاع: {old_def:,} ← {new_def:,}\n" + "\n".join(extra_lines))
    _, remaining_attacks, _ = can_attack(user_id)
    send_message(chat_id, f"📊 حملات باقیمانده: {remaining_attacks}/{ATTACK_LIMIT}")
    # 🔄 lazy import برای جلوگیری از حلقه
    from .dashboard import send_dashboard
    send_dashboard(chat_id, user_id)


def attack_artillery_menu(chat_id, user_id):
    if not is_war_allowed():
        show_screen(chat_id, "⛔ **جنگ جهانی فعال نیست!**")
        return
    total = get_user_artillery_total(user_id)
    if total <= 0:
        show_screen(chat_id, "❌ **توپخانه ندارید!** از فروشگاه ⚔️ تهاجمی بخرید.")
        return
    rows = []
    for key, a in ARTILLERY.items():
        owned = get_user_artillery_type_count(user_id, key)
        rows.append([{"text": f"{a['icon']} {a['name']} | موجودی: {owned} | قدرت: {a['power']}",
                      "callback_data": f"artillery_type_{key}"}])
    rows.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    show_screen(chat_id,
        "💥 **حمله توپخانه‌ای**\n━━━━━━━━━━━━━━━━━━\n"
        "🎯 برد: فقط قاره خودتان\n"
        "🪖 تخصص: کوبیدن تانک‌های حریف\n"
        "🛡 توپخانه پدافنددارِ حریف ضربه شما را کم می‌کند\n━━━━━━━━━━━━━━━━━━\nنوع توپخانه را انتخاب کنید:",
        {"inline_keyboard": rows})


def artillery_targets_menu(chat_id, user_id, art_key):
    a = ARTILLERY.get(art_key)
    owned = get_user_artillery_type_count(user_id, art_key)
    if not a or owned <= 0:
        show_screen(chat_id, "❌ از این توپخانه موجودی ندارید!")
        return
    attacker_continent = get_country_continent_key(players_data.get(user_id, {}).get("country"))
    targets = []
    for tid, d in players_data.items():
        if tid == user_id or not d.get("player_name"):
            continue
        if get_country_continent_key(d.get("country")) == attacker_continent:
            targets.append(tid)
    if not targets:
        show_screen(chat_id, "❌ **هدفی در قاره شما نیست!** (توپخانه برد کوتاه دارد)")
        return
    keyboard = [[{"text": f"🎯 {players_data[t].get('player_name', 'نامشخص')}",
                  "callback_data": f"artillery_target_{t}_{art_key}"}] for t in targets[:10]]
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_artillery"}])
    show_screen(chat_id,
        f"💥 **{a['name']}**\n📊 موجودی: {owned}\n🎯 هدف را انتخاب کنید:",
        {"inline_keyboard": keyboard})


def ask_artillery_count(chat_id, user_id, target_id, art_key):
    a = ARTILLERY.get(art_key)
    owned = get_user_artillery_type_count(user_id, art_key)
    if not a or owned <= 0:
        show_screen(chat_id, "❌ از این توپخانه موجودی ندارید!")
        return
    waiting_for_attack_count[user_id] = {"target_id": target_id, "weapon": f"artillery_{art_key}", "max_count": owned}
    keyboard = {"inline_keyboard": [
        [{"text": "5", "callback_data": "attack_count_5"}, {"text": "10", "callback_data": "attack_count_10"},
         {"text": "25", "callback_data": "attack_count_25"}],
        [{"text": "50", "callback_data": "attack_count_50"}, {"text": "100", "callback_data": "attack_count_100"}],
        [{"text": f"همه ({owned})", "callback_data": f"attack_count_{owned}"}],
        [{"text": "🔙 انصراف", "callback_data": "attack_artillery"}]
    ]}
    show_screen(chat_id,
        f"💥 **شلیک {a['name']} به سمت {players_data.get(target_id, {}).get('player_name', 'نامشخص')}**\n"
        f"━━━━━━━━━━━━━━━━━━\n📊 آتشبار موجود: {owned}\n🔢 تعداد را انتخاب کن:",
        keyboard)


def process_artillery_attack(chat_id, user_id, target_id, art_key, count):
    """💥 حمله توپخانه‌ای — کوبنده تانک‌های حریف؛ توپخانه پدافنددارِ حریف ضربه را کم می‌کند"""
    a = ARTILLERY.get(art_key)
    if not a:
        send_message(chat_id, "❌ توپخانه نامعتبر!")
        return
    if not is_war_allowed():
        send_message(chat_id, "⛔ **جنگ جهانی فعال نیست!**")
        return
    can_flag, remaining, wait_time = can_attack(user_id)
    if not can_flag:
        hours, minutes = wait_time
        send_message(chat_id, f"❌ **سهمیه حملات شما تمام شده!**\n⏳ {hours} ساعت {minutes} دقیقه دیگر")
        return
    attacker = players_data.get(user_id, {})
    target = players_data.get(target_id, {})
    if not target.get("player_name") or target_id == user_id:
        send_message(chat_id, "❌ هدف نامعتبر است!")
        return
    attacker_continent = get_country_continent_key(attacker.get("country"))
    if get_country_continent_key(target.get("country")) != attacker_continent:
        send_message(chat_id, "❌ **توپخانه برد کوتاه دارد!** فقط اهداف قاره خودتان.")
        return
    owned = get_user_artillery_type_count(user_id, art_key)
    if owned <= 0:
        send_message(chat_id, "❌ از این توپخانه موجودی ندارید!")
        return
    count = max(1, min(count, owned))
    # 🛕 توپخانه پدافنددارِ مهاجم: توپ‌های محافظت‌شده → ۱۰٪ قدرت بیشتر
    effective_count = int(count * 1.1) if art_key == "defense" else count
    defender_tanks = max(1, get_user_tank_count(target_id))
    _art_q = a.get("q", 1.0)
    _tank_q, _ = weighted_quality(target_id, TANKS, "tank_count")
    result, attacker_loss, defender_loss, ratio = calculate_battle_power(
        "artillery", "tank", effective_count, defender_tanks, target_id,
        attacker_quality=_art_q, defender_quality=_tank_q)
    # 🛡 توپخانه پدافنددارِ مدافع: تا ۶۰٪ تلفاتش را جبران می‌کند
    def_art = target.get("defense_artillery_count", 0)
    shield_pct = min(60, def_art * 8)
    saved = int(defender_loss * shield_pct / 100)
    defender_loss -= saved
    attacker_loss = min(attacker_loss, count)
    defender_loss = min(defender_loss, defender_tanks)
    reduce_artillery(user_id, attacker_loss)
    reduce_user_weapon(target_id, "tank", defender_loss)
    # 🏥 بیمارستان‌ها: درمان زخمی‌های نبرد توپخانه‌ای
    if attacker_loss > 0:
        _h = hospital_heal(user_id, attacker_loss)
        if _h > 0:
            send_message(chat_id, f"✚ 🏥 بیمارستان‌های شما {_h} سرباز زخمی را درمان کردند و به صف بازگشتند")
    if defender_loss > 0:
        _h = hospital_heal(target_id, defender_loss)
        if _h > 0:
            send_message(int(target_id), f"✚ 🏥 بیمارستان‌های شما {_h} سرباز زخمی را درمان کردند و به صف بازگشتند")

    base_score = max(1, min(30, int(10 * ratio)))
    if result in ("victory", "narrow_victory"):
        attacker_score_change = base_score
        defender_score_change = -base_score
        loot = _dock_loot_bonus(attacker, "artillery", random.randint(8000, 40000))
        players_data[user_id]["credit"] = attacker.get("credit", 0) + loot
        players_data[target_id]["credit"] = max(0, target.get("credit", 0) - loot // 2)
        outcome = "🔥 **رگبار توپخانه موفق بود!**" if result == "victory" else "⚡ **توپخانه با پیروزی سختی به هدف رسید**"
    else:
        attacker_score_change = -base_score
        defender_score_change = base_score
        loot = random.randint(5000, 20000)
        players_data[user_id]["credit"] = max(0, attacker.get("credit", 0) - loot)
        players_data[target_id]["credit"] = target.get("credit", 0) + loot // 3
        outcome = "💔 **توپخانه‌های شما زیر آتش تانک‌های حریف از پا درآمدند**"
    players_data[user_id]["score"] = max(0, attacker.get("score", 0) + attacker_score_change)
    players_data[target_id]["score"] = max(0, target.get("score", 0) + defender_score_change)
    db.save_player(user_id, players_data[user_id])
    db.save_player(target_id, players_data[target_id])
    add_attack_record(user_id)
    log_battle(user_id, target_id,
               f"💥 {a['name']}×{count} علیه {target.get('player_name', 'نامشخص')} — {'موفق' if result in ('victory', 'narrow_victory') else 'ناموفق'}")
    result_text = (
        f"{outcome}\n━━━━━━━━━━━━━━━━━━\n"
        f"💥 {a['name']} × {count}\n"
        f"📊 نسبت قدرت: {ratio:.2f}\n"
        f"💀 تلفات توپخانه شما: {attacker_loss}\n"
        f"💀 تانک‌های نابودشده حریف: {defender_loss}"
        + (f"\n🛡 توپخانه پدافنددار حریف {shield_pct}٪ ضربه را گرفت ({saved} تانک نجات یافت)" if shield_pct else "")
        + (f"\n🛕 توپخانه پدافنددار شما توپ‌ها را محافظت کرد (+۱۰٪ قدرت)" if art_key == "defense" else "")
        + f"\n💰 {'غنیمت' if result in ('victory', 'narrow_victory') else 'خسارت'}: {loot:,} سکه"
        + f"\n🏆 امتیاز شما: {attacker_score_change:+d}")
    send_message(chat_id, result_text)
    send_message(int(target_id),
        f"🚨 **شهر شما زیر رگبار توپخانه است!**\n"
        f"👤 {attacker.get('player_name', 'نامشخص')} با {a['name']} × {count}\n"
        f"💀 تانک‌های از دست رفته: {defender_loss}")
    send_to_group(
        f"⚔️ **نبرد توپخانه‌ای** ⚔️\n"
        f"💥 {attacker.get('player_name', 'نامشخص')} [{attacker.get('country', 'نامشخص')}] با {a['name']} × {count} "
        f"به {target.get('player_name', 'نامشخص')} [{target.get('country', 'نامشخص')}] حمله کرد!\n"
        f"💀 تانک‌های نابودشده: {defender_loss} | تلفات توپخانه: {attacker_loss}")
    _, remaining_attacks, _ = can_attack(user_id)
    send_message(chat_id, f"📊 حملات باقیمانده: {remaining_attacks}/{ATTACK_LIMIT}")
    # 🔄 lazy import برای جلوگیری از حلقه
    from .dashboard import send_dashboard
    send_dashboard(chat_id, user_id)


def get_available_targets(attacker_id, weapon_type):
    attacker = players_data.get(attacker_id, {})
    attacker_country = attacker.get("country")
    attacker_continent = get_country_continent_key(attacker_country)
    attacker_bases = []
    for base_id, base in bases_data.items():
        if base.get("owner") == attacker_id and base.get("ready_at", 0) <= time.time():
            attacker_bases.append(base)
    attacker_base_continents = set()
    for base in attacker_bases:
        base_continent = base.get("continent")
        if base_continent:
            attacker_base_continents.add(base_continent)
    targets = []
    for target_id, target_data in players_data.items():
        if target_id == attacker_id:
            continue
        if not target_data.get("player_name"):
            continue
        target_country = target_data.get("country")
        if not target_country:
            continue
        target_continent = get_country_continent_key(target_country)
        if weapon_type == "missile":
            if attacker_continent == target_continent or target_continent in attacker_base_continents:
                targets.append(target_id)
        elif weapon_type in ["navy", "submarine"]:
            targets.append(target_id)
        else:
            # 🛬 فرودگاه: با داشتن فرودگاه، حمله هوایی به همه قاره‌ها باز می‌شود
            if attacker_continent == target_continent or target_continent in attacker_base_continents:
                targets.append(target_id)
            elif (weapon_type in ("fighter", "helicopter", "drone")
                    and players_data.get(attacker_id, {}).get("airport_count", 0) > 0):
                targets.append(target_id)
    return targets


def send_attack_menu(chat_id, user_id):
    if not is_war_allowed():
        show_screen(chat_id, "⛔ **جنگ جهانی فعال نیست!**\n\nفعلاً نمی‌توانید حمله کنید.")
        return
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔍 جستجوی هدف", "callback_data": "attack_search"}],
            [{"text": "💻 حمله هکری", "callback_data": "attack_hacker"}],
            [{"text": "🗡️ ترور", "callback_data": "attack_assassination"}],
            [{"text": "🪖 حمله زمینی (تانک)", "callback_data": "attack_ground"}],
            [{"text": "✈️ حمله هوایی (جنگنده)", "callback_data": "attack_air"}],
            [{"text": "🚁 حمله هوایی (بالگرد)", "callback_data": "attack_helicopter"}],
            [{"text": "🛸 حمله پهپادی", "callback_data": "attack_drone"}],
            [{"text": "🚢 حمله دریایی (ناو)", "callback_data": "attack_navy"}],
            [{"text": "🐋 حمله دریایی (زیردریایی)", "callback_data": "attack_submarine"}],
            [{"text": "🚀 حمله موشکی", "callback_data": "attack_missile"}],
            [{"text": "💣 بمب‌افکن استراتژیک", "callback_data": "attack_bombs"}],
            [{"text": "💥 توپخانه", "callback_data": "attack_artillery"}],
            [{"text": "❓ قوانین جنگ", "callback_data": "battle_rules"}],
            [{"text": "🔙 بازگشت", "callback_data": "dashboard"}]
        ]
    }
    show_screen(chat_id, "⚔️ **پنل جنگ**\n\n🔥 جنگ جهانی فعال است!\nلطفا ابتدا هدف مورد نظر را جست و جو کرده و سپس نوع حمله کنید", keyboard)


def show_battle_rules(chat_id):
    text = """⚔️ **قوانین جنگ** ⚔️

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🪖 نیروهای زمینی:**
• تانک → می‌تواند: تانک، توپخانه، پدافند

**✈️ نیروهای هوایی:**
• جنگنده → می‌تواند: تانک، جنگنده، بالگرد، ناو، پدافند
• بالگرد → می‌تواند: تانک، توپخانه، پدافند، بالگرد
• ضعیف در برابر → پدافند هوایی

**🛡️ پدافند هوایی:**
• فقط می‌تواند: جنگنده، بالگرد

**🚢 نیروهای دریایی:**
• ناو → می‌تواند: جنگنده، بالگرد، ناو، زیردریایی
• زیردریایی → می‌تواند: ناو، زیردریایی
• ضعیف در برابر → موشک

**🚀 موشک‌ها:**
• برد: تا انتهای قاره
• می‌تواند: ناو

**⚖️ کیفیت تجهیزات:**
• هر تجهیز «کیفیت» دارد؛ کیفیت هم‌ارز تعداد است و باکیفیت‌ها کمتر تلف می‌دهند
• با سلاح‌های ساده نمی‌توانی تجهیزات درجه‌یک حریف را شکست دهی!
• هر تجهیز «سقف» نگهداری دارد — انبار بی‌نهایت وجود ندارد

**💣 بمب‌افکن استراتژیک (یک‌بارمصرف):**
• بمب آتش‌زا → ۳ روز شهر حریف در آتش می‌سوزد (هر پدافندی می‌تواند رهگیری کند)
• بمب فضاپیل → ضربه از فضا؛ فقط پدافندهای پیشرفته (S-400 و گنبد آهنین) دفعش می‌کنند
• بمب قاره‌ای → برد جهانی + نابودی ساختمان‌ها؛ با مترو و پدافند پیشرفته مهار می‌شود

**💥 توپخانه:**
• برد: فقط قاره خودتان | تخصص: نابودی تانک‌های حریف
• توپخانه پدافنددارِ حریف تا ۶۰٪ ضربه را می‌گیرد؛ پدافنددارِ شما +۱۰٪ قدرت می‌دهد

**🏗️ ساختمان‌های کاربردی:**
• 🏥 بیمارستان → درمان سربازان زخمی پس از نبرد (سقف روزانه)
• 🚉 مترو → پناهگاه: کاهش تلفات جمعیت از بمب و ویروس
• 🛬 فرودگاه → حمله هوایی به همه قاره‌ها
• ⛴️ اسکله → غنیمت حملات دریایی تا ۲ برابر
• 🛕 پادگان → هر شب سرباز تربیت می‌کند

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 فرمول: قدرت = آسیب × √(تعداد × کیفیت) × اثربخشی × شانس"""
    show_screen(chat_id, text)


def attack_ground(chat_id, user_id):
    count = get_user_tank_count(user_id)
    if count <= 0:
        send_message(chat_id, "❌ **تانک ندارید!** از فروشگاه بخرید.")
        return
    targets = get_available_targets(user_id, "tank")
    if not targets:
        send_message(chat_id, "❌ **هیچ هدفی یافت نشد!**")
        return
    keyboard = [[{"text": f"🎯 {players_data[t].get('player_name', 'نامشخص')}", "callback_data": f"attack_target_{t}_tank"}] for t in targets[:10]]
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    send_message(chat_id, f"🪖 **حمله زمینی**\nشما {count} تانک دارید.\nهدف را انتخاب کنید:", {"inline_keyboard": keyboard})


def attack_air(chat_id, user_id):
    user = players_data.get(user_id, {})
    ready_fighters = 0
    for fighter_key in FIGHTERS.keys():
        fighter_count = user.get(f"{fighter_key}_fighter_count", 0)
        pilot_type = get_pilot_type_for_fighter(fighter_key)
        if pilot_type:
            pilot_count = user.get(f"{pilot_type}_pilot_count", 0)
            ready_fighters += min(fighter_count, pilot_count)
    if ready_fighters <= 0:
        text = "❌ **شما جنگنده آماده برای حمله ندارید!**\n━━━━━━━━━━━━━━━━━━\n⚠️ هر جنگنده نیاز به خلبان مخصوص خود دارد:\n🟠 خلبان عادی → اف4، اف18، جی10، جی16، اف16، سوخو27\n🔴 خلبان قوی → یوروفایتر، جی17، گلدن ایگل، جی20، سوخو35\n⭐ خلبان حرفه‌ای → سوخو57، اف35، سوخو75، اف22\n━━━━━━━━━━━━━━━━━━\n💰 از فروشگاه خلبان بخرید!"
        send_message(chat_id, text)
        return
    targets = get_available_targets(user_id, "fighter")
    if not targets:
        send_message(chat_id, "❌ **هیچ هدفی یافت نشد!**")
        return
    keyboard = [[{"text": f"🎯 {players_data[t].get('player_name', 'نامشخص')}", "callback_data": f"attack_target_{t}_fighter"}] for t in targets[:10]]
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    normal_pilot = user.get("normal_pilot_count", 0)
    strong_pilot = user.get("strong_pilot_count", 0)
    professional_pilot = user.get("professional_pilot_count", 0)
    pilot_status = f"🟠 عادی: {normal_pilot} | 🔴 قوی: {strong_pilot} | ⭐ حرفه‌ای: {professional_pilot}"
    send_message(chat_id, f"✈️ **حمله هوایی**\n━━━━━━━━━━━━━━━━━━\n🎯 جنگنده‌های آماده: {ready_fighters}\n👨‍✈️ {pilot_status}\n━━━━━━━━━━━━━━━━━━\nهدف را انتخاب کنید:", {"inline_keyboard": keyboard})


def attack_helicopter(chat_id, user_id):
    user = players_data.get(user_id, {})
    heli_count = 0
    for heli_key in HELICOPTERS.keys():
        heli_count += user.get(f"{heli_key}_helicopter_count", 0)
    pilot_count = user.get("helicopter_pilot_count", 0)
    ready_helicopters = min(heli_count, pilot_count)
    if ready_helicopters <= 0:
        send_message(chat_id, "❌ **شما هلیکوپتر آماده برای حمله ندارید!**\n🚁 هر هلیکوپتر نیاز به خلبان هلیکوپتر دارد.\n💰 از فروشگاه خلبان هلیکوپتر بخرید.")
        return
    targets = get_available_targets(user_id, "helicopter")
    if not targets:
        send_message(chat_id, "❌ **هیچ هدفی یافت نشد!**")
        return
    keyboard = [[{"text": f"🎯 {players_data[t].get('player_name', 'نامشخص')}", "callback_data": f"attack_target_{t}_helicopter"}] for t in targets[:10]]
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    send_message(chat_id, f"🚁 **حمله با هلیکوپتر**\n━━━━━━━━━━━━━━━━━━\n🚁 هلیکوپترهای آماده: {ready_helicopters}\n👨‍✈️ خلبان هلیکوپتر: {pilot_count}\n━━━━━━━━━━━━━━━━━━\nهدف را انتخاب کنید:", {"inline_keyboard": keyboard})


def attack_drone(chat_id, user_id):
    count = get_user_drone_count(user_id)
    if count <= 0:
        send_message(chat_id, "❌ **پهپاد ندارید!** از فروشگاه بخرید.")
        return
    targets = get_available_targets(user_id, "drone")
    if not targets:
        send_message(chat_id, "❌ **هیچ هدفی یافت نشد!**")
        return
    keyboard = [[{"text": f"🎯 {players_data[t].get('player_name', 'نامشخص')}", "callback_data": f"attack_target_{t}_drone"}] for t in targets[:10]]
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    send_message(chat_id, f"🛸 **حمله پهپادی**\nشما {count} پهپاد دارید.\nهدف را انتخاب کنید:", {"inline_keyboard": keyboard})


def attack_navy(chat_id, user_id):
    count = get_user_navy_count(user_id)
    if count <= 0:
        send_message(chat_id, "❌ **ناو ندارید!** از فروشگاه بخرید.")
        return
    targets = []
    for target_id, target_data in players_data.items():
        if target_id == user_id:
            continue
        if not target_data.get("player_name"):
            continue
        targets.append(target_id)
    if not targets:
        send_message(chat_id, "❌ **هیچ هدفی یافت نشد!**")
        return
    waiting_for_attack_target[user_id] = {"weapon": "navy", "targets": targets}
    keyboard = []
    for tid in targets[:10]:
        target_name = players_data[tid].get('player_name', 'نامشخص')
        keyboard.append([{"text": f"🎯 {target_name}", "callback_data": f"attack_target_{tid}_navy"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    send_message(chat_id, f"🚢 **حمله دریایی**\nشما {count} ناو دارید.\nهدف را انتخاب کنید:", {"inline_keyboard": keyboard})


def attack_submarine(chat_id, user_id):
    count = get_user_submarine_count(user_id)
    if count <= 0:
        send_message(chat_id, "❌ **زیردریایی ندارید!** از فروشگاه بخرید.")
        return
    targets = get_available_targets(user_id, "submarine")
    if not targets:
        send_message(chat_id, "❌ **هیچ هدفی یافت نشد!**")
        return
    keyboard = [[{"text": f"🎯 {players_data[t].get('player_name', 'نامشخص')}", "callback_data": f"attack_target_{t}_submarine"}] for t in targets[:10]]
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    send_message(chat_id, f"🐋 **حمله با زیردریایی**\nشما {count} زیردریایی دارید.\nهدف را انتخاب کنید:", {"inline_keyboard": keyboard})


def attack_missile(chat_id, user_id):
    if is_missile_disabled(user_id):
        send_message(chat_id, "❌ **سیستم موشکی شما توسط هکرها از کار افتاده است!**\n⏳ تا 30 دقیقه نمی‌توانید موشک شلیک کنید.")
        return
    count = get_user_missile_count(user_id)
    if count <= 0:
        send_message(chat_id, "❌ **موشک ندارید!** از فروشگاه بخرید.")
        return
    attacker_bases = []
    for base_id, base in bases_data.items():
        if base.get("owner") == user_id and base.get("ready_at", 0) <= time.time():
            attacker_bases.append(base)
    attacker_base_continents = set()
    for base in attacker_bases:
        base_continent = base.get("continent")
        if base_continent:
            attacker_base_continents.add(base_continent)
    attacker_country = players_data.get(user_id, {}).get("country", "")
    attacker_continent = get_country_continent_key(attacker_country)
    targets = []
    for target_id, target_data in players_data.items():
        if target_id == user_id:
            continue
        if not target_data.get("player_name"):
            continue
        target_country = target_data.get("country", "")
        target_continent = get_country_continent_key(target_country)
        if attacker_continent == target_continent or target_continent in attacker_base_continents:
            targets.append(target_id)
    if not targets:
        send_message(chat_id, "❌ **هیچ هدفی یافت نشد!**\nموشک می‌تواند به قاره خودتان یا قاره‌هایی که در آنها پایگاه دارید حمله کند.")
        return
    waiting_for_attack_target[user_id] = {"weapon": "missile", "targets": targets}
    keyboard = []
    for tid in targets[:10]:
        target_name = players_data[tid].get('player_name', 'نامشخص')
        keyboard.append([{"text": f"🎯 {target_name}", "callback_data": f"missile_target_{tid}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    base_text = ""
    if attacker_base_continents:
        continent_names = [CONTINENT_NAMES.get(c, c) for c in attacker_base_continents]
        base_text = f"\n📍 پایگاه‌های شما در: {', '.join(continent_names)}"
    send_message(chat_id, f"🚀 **حمله موشکی**\nشما {count} موشک دارید.\n📌 قاره خود: {CONTINENT_NAMES.get(attacker_continent, attacker_continent)}{base_text}\n\nهدف را انتخاب کنید:", {"inline_keyboard": keyboard})


# ==================== جستجوی هدف برای حمله ====================
def attack_search_target(chat_id, user_id):
    """جستجوی هدف برای حمله"""
    if not is_war_allowed():
        send_message(chat_id, "⛔ **جنگ جهانی فعال نیست!**\n\nفعلاً نمی‌توانید حمله کنید.")
        return
    
    send_message(chat_id, "🔍 **نام کشور یا نام بازیکن مورد نظر را وارد کنید:**\n\n(مثال: ایران، آمریکا، رضا)")
    waiting_for_attack_search[user_id] = True


def process_attack_search(chat_id, user_id, search_text):
    """پردازش جستجوی هدف و نمایش نتایج (فقط اسم)"""
    if not is_war_allowed():
        send_message(chat_id, "⛔ **جنگ جهانی فعال نیست!**")
        return
    
    found_players = []
    search_lower = search_text.lower()
    
    for uid, data in players_data.items():
        if uid == user_id:
            continue
        if not data.get("player_name"):
            continue
        
        player_name = data.get("player_name", "").lower()
        country_name = data.get("country", "").lower()
        
        if search_lower in player_name or search_lower in country_name:
            found_players.append({
                "user_id": uid,
                "name": data.get("player_name"),
                "country": data.get("country")
            })
    
    if not found_players:
        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت به منوی حمله", "callback_data": "attack_menu"}]]}
        send_message(chat_id, f"❌ **هیچ بازیکنی با مشخصات '{search_text}' یافت نشد!**\n\nلطفاً نام دقیق‌تری وارد کنید.", keyboard)
        return
    
    text = f"🔍 **نتایج جستجوی '{search_text}'**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 {len(found_players)} بازیکن یافت شد:\n━━━━━━━━━━━━━━━━━━\n\n"
    
    keyboard = []
    for player in found_players[:20]:
        text += f"👤 **{player['name']}**\n"
        text += f"   🌍 {player['country']}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        
        keyboard.append([{"text": f"⚔️ حمله به {player['name']}", "callback_data": f"attack_search_select_{player['user_id']}"}])
    
    if len(found_players) > 20:
        text += f"\n... و {len(found_players) - 20} بازیکن دیگر"
    
    keyboard.append([{"text": "🔍 جستجوی مجدد", "callback_data": "attack_search"}])
    keyboard.append([{"text": "🔙 بازگشت به منوی حمله", "callback_data": "attack_menu"}])
    
    send_message(chat_id, text, {"inline_keyboard": keyboard})


def attack_select_from_search(chat_id, user_id, target_id):
    """انتخاب هدف از نتایج جستجو و رفتن به منوی انتخاب سلاح"""
    if not is_war_allowed():
        send_message(chat_id, "⛔ **جنگ جهانی فعال نیست!**")
        return
    
    if target_id not in players_data:
        send_message(chat_id, "❌ هدف یافت نشد!")
        return
    
    target_name = players_data[target_id].get("player_name", "نامشخص")
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🪖 حمله زمینی (تانک)", "callback_data": f"attack_weapon_tank_{target_id}"}],
            [{"text": "✈️ حمله هوایی (جنگنده)", "callback_data": f"attack_weapon_fighter_{target_id}"}],
            [{"text": "🚁 حمله هوایی (بالگرد)", "callback_data": f"attack_weapon_helicopter_{target_id}"}],
            [{"text": "🛸 حمله پهپادی", "callback_data": f"attack_weapon_drone_{target_id}"}],
            [{"text": "🚢 حمله دریایی (ناو)", "callback_data": f"attack_weapon_navy_{target_id}"}],
            [{"text": "🐋 حمله دریایی (زیردریایی)", "callback_data": f"attack_weapon_submarine_{target_id}"}],
            [{"text": "🚀 حمله موشکی", "callback_data": f"attack_weapon_missile_{target_id}"}],
            [{"text": "💻 حمله هکری", "callback_data": f"attack_hacker_target_{target_id}"}],
            [{"text": "🗡️ ترور", "callback_data": f"assassinate_target_{target_id}"}],
            [{"text": "🔙 بازگشت به نتایج جستجو", "callback_data": "attack_search"}],
            [{"text": "🔙 بازگشت به منوی حمله", "callback_data": "attack_menu"}]
        ]
    }
    
    send_message(chat_id, 
        f"⚔️ **انتخاب روش حمله به {target_name}**\n━━━━━━━━━━━━━━━━━━\n"
        f"نوع حمله را انتخاب کنید:", 
        keyboard)


def attack_weapon_select(chat_id, user_id, weapon, target_id):
    """پردازش انتخاب سلاح و رفتن به مرحله تعداد"""
    weapon_names = {
        "tank": "تانک",
        "fighter": "جنگنده",
        "helicopter": "بالگرد",
        "drone": "پهپاد",
        "navy": "ناو جنگی",
        "submarine": "زیردریایی",
        "missile": "موشک"
    }
    
    if weapon == "tank":
        count = get_user_tank_count(user_id)
    elif weapon == "fighter":
        count = get_user_fighter_count_with_pilot(user_id)
    elif weapon == "helicopter":
        count = get_user_helicopter_count_with_pilot(user_id)
    elif weapon == "drone":
        count = get_user_drone_count(user_id)
    elif weapon == "navy":
        count = get_user_navy_count(user_id)
    elif weapon == "submarine":
        count = get_user_submarine_count(user_id)
    elif weapon == "missile":
        count = get_user_missile_count(user_id)
    else:
        send_message(chat_id, "❌ سلاح نامعتبر!")
        return
    
    if count <= 0:
        weapon_name = weapon_names.get(weapon, weapon)
        if weapon == "fighter":
            send_message(chat_id, f"❌ شما جنگنده آماده (با خلبان) ندارید!")
        elif weapon == "helicopter":
            send_message(chat_id, f"❌ شما هلیکوپتر آماده (با خلبان) ندارید!")
        else:
            send_message(chat_id, f"❌ شما {weapon_name} ندارید! از فروشگاه بخرید.")
        return
    
    waiting_for_attack_count[user_id] = {
        "target_id": target_id,
        "weapon": weapon,
        "max_count": count
    }
    
    weapon_name = weapon_names.get(weapon, weapon)
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "1", "callback_data": f"attack_count_1"}, {"text": "5", "callback_data": f"attack_count_5"}, {"text": "10", "callback_data": f"attack_count_10"}],
            [{"text": "25", "callback_data": f"attack_count_25"}, {"text": "50", "callback_data": f"attack_count_50"}, {"text": "100", "callback_data": f"attack_count_100"}],
            [{"text": f"حداکثر ({count})", "callback_data": f"attack_count_{count}"}],
            [{"text": "🔙 انصراف", "callback_data": "attack_menu"}]
        ]
    }
    
    send_message(chat_id, 
        f"⚔️ **حمله با {weapon_name}**\n━━━━━━━━━━━━━━━━━━\n"
        f"🎯 هدف: {players_data[target_id].get('player_name')}\n"
        f"📊 تعداد موجود: {count}\n"
        f"🔢 **تعداد {weapon_name} برای حمله را انتخاب کن:**", 
        keyboard)


def ask_attack_count(chat_id, user_id, target_id, weapon):
    weapon_names = {
        "tank": "تانک",
        "fighter": "جنگنده",
        "helicopter": "بالگرد",
        "drone": "پهپاد",
        "navy": "ناو جنگی",
        "submarine": "زیردریایی",
        "missile": "موشک"
    }
    if weapon == "tank":
        max_count = get_user_tank_count(user_id)
    elif weapon == "fighter":
        max_count = get_user_fighter_count_with_pilot(user_id)
    elif weapon == "helicopter":
        max_count = get_user_helicopter_count_with_pilot(user_id)
    elif weapon == "drone":
        max_count = get_user_drone_count(user_id)
    elif weapon == "navy":
        max_count = get_user_navy_count(user_id)
    elif weapon == "submarine":
        max_count = get_user_submarine_count(user_id)
    elif weapon == "missile":
        max_count = get_user_missile_count(user_id)
    else:
        show_screen(chat_id, f"❌ سلاح {weapon} شناسایی نشد!")
        return
    if max_count <= 0:
        weapon_name = weapon_names.get(weapon, weapon)
        if weapon == "fighter":
            show_screen(chat_id, f"❌ شما جنگنده آماده (با خلبان) ندارید!")
        elif weapon == "helicopter":
            show_screen(chat_id, f"❌ شما هلیکوپتر آماده (با خلبان) ندارید!")
        else:
            show_screen(chat_id, f"❌ شما {weapon_name} ندارید! از فروشگاه بخرید.")
        return
    waiting_for_attack_count[user_id] = {
        "target_id": target_id, 
        "weapon": weapon, 
        "max_count": max_count
    }
    weapon_name = weapon_names.get(weapon, weapon)
    text = f"⚔️ **حمله با {weapon_name}**\n━━━━━━━━━━━━━━━━━━\n📊 تعداد موجود: {max_count}\n🔢 **تعداد {weapon_name} برای حمله را وارد کن (حداکثر {max_count}):**"
    keyboard = {
        "inline_keyboard": [
            [{"text": "1", "callback_data": f"attack_count_1"}, {"text": "5", "callback_data": f"attack_count_5"}, {"text": "10", "callback_data": f"attack_count_10"}],
            [{"text": "25", "callback_data": f"attack_count_25"}, {"text": "50", "callback_data": f"attack_count_50"}, {"text": "100", "callback_data": f"attack_count_100"}],
            [{"text": f"حداکثر ({max_count})", "callback_data": f"attack_count_{max_count}"}],
            [{"text": "🔙 انصراف", "callback_data": "attack_menu"}]
        ]
    }
    show_screen(chat_id, text, keyboard)


def process_attack_count_callback(chat_id, user_id, count):
    """پردازش تعداد انتخاب شده برای حمله"""
    try:
        count = int(count)
        if count < 1:
            send_message(chat_id, "❌ تعداد باید حداقل 1 باشد!")
            return
        
        if user_id not in waiting_for_attack_count:
            send_message(chat_id, "❌ درخواست نامعتبر! دوباره از منوی حمله اقدام کنید.")
            return
        
        attack_data = waiting_for_attack_count.pop(user_id)
        target_id = attack_data["target_id"]
        weapon = attack_data["weapon"]
        max_count = attack_data["max_count"]
        
        if count > max_count:
            weapon_name = "تجهیزات"
            if weapon == "tank":
                weapon_name = "تانک"
            elif weapon == "fighter":
                weapon_name = "جنگنده"
            elif weapon == "helicopter":
                weapon_name = "بالگرد"
            elif weapon == "drone":
                weapon_name = "پهپاد"
            elif weapon == "navy":
                weapon_name = "ناو جنگی"
            elif weapon == "submarine":
                weapon_name = "زیردریایی"
            elif weapon == "missile":
                weapon_name = "موشک"
            
            send_message(chat_id, f"❌ شما فقط {max_count} عدد {weapon_name} دارید!")
            return
        
        process_attack(chat_id, user_id, target_id, weapon, count)
        
    except ValueError:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")


def process_attack(chat_id, user_id, target_id, weapon, count):
    """پردازش حمله با محدودیت 3 حمله در 24 ساعت"""
    # 💣💥 مسیریابی تسلیحات ویژه
    if weapon.startswith("bomb_"):
        process_bomb_strike(chat_id, user_id, target_id, weapon[5:], count)
        return
    if weapon.startswith("artillery_"):
        process_artillery_attack(chat_id, user_id, target_id, weapon[10:], count)
        return
    
    # ========== 1. بررسی محدودیت حمله ==========
    can_attack_flag, remaining, wait_time = can_attack(user_id)
    
    if not can_attack_flag:
        hours, minutes = wait_time
        send_message(chat_id, 
            f"❌ **شما به محدودیت حمله رسیده‌اید!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 حداکثر {ATTACK_LIMIT} حمله در 24 ساعت\n"
            f"⏳ زمان تا آزاد شدن: {hours} ساعت {minutes} دقیقه\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 صبر کنید تا محدودیت شما آزاد شود.")
        return
    
    # ========== 2. بررسی فعال بودن جنگ ==========
    if not is_war_allowed():
        send_message(chat_id, "⛔ **جنگ جهانی فعال نیست!**\n\nفعلاً نمی‌توانید حمله کنید.")
        return
    
    # ========== 3. نام سلاح‌ها ==========
    weapon_names = {
        "tank": "تانک",
        "fighter": "جنگنده",
        "helicopter": "بالگرد",
        "drone": "پهپاد",
        "navy": "ناو جنگی",
        "submarine": "زیردریایی",
        "missile": "موشک"
    }
    
    # ========== 4. اخطار به بازیکن هدف ==========
    attacker = players_data.get(user_id, {})
    target = players_data.get(target_id, {})
    
    attacker_name = attacker.get('player_name', 'نامشخص')
    attacker_country = attacker.get('country', 'نامشخص')
    weapon_name_persian = weapon_names.get(weapon, weapon)
    
    warning_text = f"""⚠️ **هشدار نظامی!** ⚠️
━━━━━━━━━━━━━━━━━━
🎯 **شما مورد حمله قرار گرفتید!**

👤 مهاجم: {attacker_name}
🌍 کشور مهاجم: {attacker_country}
⚔️ نوع حمله: {weapon_name_persian}
🔢 تعداد تجهیزات مهاجم: {count} عدد

🛡 لطفاً آماده دفاع باشید!
━━━━━━━━━━━━━━━━━━
🕐 {time.strftime('%H:%M:%S')}"""
    
    send_message(int(target_id), warning_text)
    
    # ========== 5. بررسی غیرفعال بودن پدافند ==========
    if weapon in ["fighter", "helicopter", "drone"] and is_defense_disabled(target_id):
        send_message(chat_id, "⚠️ **پدافندهای حریف توسط هکرها از کار افتاده است!**\nحمله شما مؤثرتر خواهد بود.")
    
    # ========== 6. دریافت اطلاعات کاربر و هدف ==========
    user = players_data.get(user_id, {})
    target = players_data.get(target_id, {})
    
    # ========== 7. بررسی موجودی سلاح ==========
    if weapon == "tank":
        weapon_count = get_user_tank_count(user_id)
        weapon_key = "tank"
    elif weapon == "fighter":
        weapon_count = get_user_fighter_count(user_id)
        weapon_key = "fighter"
    elif weapon == "helicopter":
        weapon_count = get_user_helicopter_count(user_id)
        weapon_key = "helicopter"
    elif weapon == "drone":
        weapon_count = get_user_drone_count(user_id)
        weapon_key = "drone"
    elif weapon == "navy":
        weapon_count = get_user_navy_count(user_id)
        weapon_key = "naval"
    elif weapon == "submarine":
        weapon_count = get_user_submarine_count(user_id)
        weapon_key = "submarine"
    elif weapon == "missile":
        weapon_count = get_user_missile_count(user_id)
        weapon_key = "missile"
    else:
        weapon_count = 0
        weapon_key = "tank"
    
    if count > weapon_count:
        weapon_name = weapon_names.get(weapon, weapon)
        send_message(chat_id, f"❌ شما فقط {weapon_count} عدد {weapon_name} دارید!")
        return
    
    # ========== 8. تعیین سلاح دفاعی هدف ==========
    defender_weapons = {
        "tank": "tank", 
        "fighter": "air_defense", 
        "helicopter": "air_defense",
        "drone": "air_defense", 
        "navy": "navy", 
        "submarine": "submarine", 
        "missile": "navy"
    }
    defender_weapon = defender_weapons.get(weapon, "tank")
    
    if defender_weapon == "tank":
        defender_count = get_user_tank_count(target_id)
    elif defender_weapon == "air_defense":
        defender_count = get_user_air_defense_count(target_id)
    elif defender_weapon == "navy":
        defender_count = get_user_navy_count(target_id)
    elif defender_weapon == "submarine":
        defender_count = get_user_submarine_count(target_id)
    else:
        defender_count = 1
    
    defender_count = max(1, defender_count)
    
    # ========== 9. محاسبه نتیجه نبرد ==========
    _cat_a = WEAPON_CATEGORIES.get(weapon, (TANKS, "tank_count"))
    _cat_d = WEAPON_CATEGORIES.get(defender_weapon, (TANKS, "tank_count"))
    _aq, _ = weighted_quality(user_id, _cat_a[0], _cat_a[1])
    _dq, _ = weighted_quality(target_id, _cat_d[0], _cat_d[1])
    result, attacker_loss, defender_loss, ratio = calculate_battle_power(
        weapon, defender_weapon, count, defender_count, target_id,
        attacker_quality=_aq, defender_quality=_dq)
    
    # ========== 10. کاهش تجهیزات مهاجم ==========
    if weapon == "tank":
        reduce_user_weapon(user_id, "tank", attacker_loss)
    elif weapon == "fighter":
        reduce_user_weapon(user_id, "fighter", attacker_loss)
    elif weapon == "helicopter":
        reduce_user_weapon(user_id, "helicopter", attacker_loss)
    elif weapon == "drone":
        reduce_user_weapon(user_id, "drone", attacker_loss)
    elif weapon == "navy":
        reduce_user_weapon(user_id, "naval", attacker_loss)
    elif weapon == "submarine":
        reduce_user_weapon(user_id, "submarine", attacker_loss)
    elif weapon == "missile":
        reduce_user_weapon(user_id, "missile", attacker_loss)
    
    # ========== 11. کاهش تجهیزات هدف ==========
    if defender_weapon == "tank":
        reduce_user_weapon(target_id, "tank", defender_loss)
    elif defender_weapon == "air_defense":
        reduce_user_weapon(target_id, "air_defense", defender_loss)
    elif defender_weapon == "navy":
        reduce_user_weapon(target_id, "naval", defender_loss)
    elif defender_weapon == "submarine":
        reduce_user_weapon(target_id, "submarine", defender_loss)
    
    # ========== 11.5 🏥 بیمارستان‌ها: درمان زخمی‌های زمینی ==========
    heal_notes = []
    if weapon == "tank" and attacker_loss > 0:
        _healed = hospital_heal(user_id, attacker_loss)
        if _healed > 0:
            heal_notes.append(f"🏥 بیمارستان‌های شما {_healed} سرباز زخمی را درمان کردند و به صف بازگشتند")
    if defender_weapon == "tank" and defender_loss > 0:
        _healed = hospital_heal(target_id, defender_loss)
        if _healed > 0:
            heal_notes.append(f"🏥 بیمارستان‌های حریف {_healed} سرباز زخمی را درمان کردند")
    # ========== 12. محاسبه امتیازات و غنیمت ==========
    attacker_score_change = 0
    defender_score_change = 0
    loot = 0
    base_score = int(10 * ratio)
    
    if base_score < 1:
        base_score = 1
    if base_score > 30:
        base_score = 30
    
    if result == "victory":
        loot = _dock_loot_bonus(user, weapon, random.randint(10000, 100000))
        attacker_score_change = base_score + 5
        defender_score_change = -(base_score + 10)
        players_data[user_id]["credit"] = user.get("credit", 0) + loot
        players_data[target_id]["credit"] = max(0, target.get("credit", 0) - loot // 2)
        result_text = f"🔥 **پیروزی قاطع!**\n━━━━━━━━━━━━━━━━━━\n📊 نسبت قدرت: {ratio:.2f}\n💀 تلفات شما: {attacker_loss}\n💀 تلفات حریف: {defender_loss}\n💰 غنیمت: {loot:,} سکه\n🏆 امتیاز شما: +{attacker_score_change}\n📉 امتیاز حریف: {defender_score_change}"
    
    elif result == "narrow_victory":
        loot = _dock_loot_bonus(user, weapon, random.randint(5000, 50000))
        attacker_score_change = base_score
        defender_score_change = -(base_score + 5)
        players_data[user_id]["credit"] = user.get("credit", 0) + loot
        players_data[target_id]["credit"] = max(0, target.get("credit", 0) - loot // 3)
        result_text = f"⚡ **پیروزی سخت!**\n━━━━━━━━━━━━━━━━━━\n📊 نسبت قدرت: {ratio:.2f}\n💀 تلفات شما: {attacker_loss}\n💀 تلفات حریف: {defender_loss}\n💰 غنیمت: {loot:,} سکه\n🏆 امتیاز شما: +{attacker_score_change}\n📉 امتیاز حریف: {defender_score_change}"
    
    elif result == "narrow_defeat":
        loot = _dock_loot_bonus(user, weapon, random.randint(5000, 50000))
        attacker_score_change = -(base_score + 10)
        defender_score_change = base_score
        players_data[user_id]["credit"] = max(0, user.get("credit", 0) - loot)
        players_data[target_id]["credit"] = target.get("credit", 0) + loot // 3
        result_text = f"💔 **شکست نزدیک!**\n━━━━━━━━━━━━━━━━━━\n📊 نسبت قدرت: {ratio:.2f}\n💀 تلفات شما: {attacker_loss}\n💀 تلفات حریف: {defender_loss}\n💰 خسارت: {loot:,} سکه\n📉 امتیاز شما: {attacker_score_change}\n🏆 امتیاز حریف: +{defender_score_change}"
    
    else:  # defeat
        loot = _dock_loot_bonus(user, weapon, random.randint(10000, 100000))
        attacker_score_change = -(base_score + 20)
        defender_score_change = base_score + 10
        players_data[user_id]["credit"] = max(0, user.get("credit", 0) - loot)
        players_data[target_id]["credit"] = target.get("credit", 0) + loot // 2
        result_text = f"💀 **شکست سنگین!**\n━━━━━━━━━━━━━━━━━━\n📊 نسبت قدرت: {ratio:.2f}\n💀 تلفات شما: {attacker_loss}\n💀 تلفات حریف: {defender_loss}\n💰 خسارت: {loot:,} سکه\n📉 امتیاز شما: {attacker_score_change}\n🏆 امتیاز حریف: +{defender_score_change}"
    
    # ========== 13. اعمال تغییرات امتیاز ==========
    players_data[user_id]["score"] = max(0, user.get("score", 0) + attacker_score_change)
    players_data[target_id]["score"] = max(0, target.get("score", 0) + defender_score_change)
    
    # ========== 14. ذخیره در دیتابیس ==========
    db.save_player(user_id, players_data[user_id])
    db.save_player(target_id, players_data[target_id])
    
    # ========== 15. ثبت حمله در تاریخچه (محدودیت) ==========
    add_attack_record(user_id)
    _res_fa = {"victory": "پیروزی قاطع", "narrow_victory": "پیروزی سخت",
               "narrow_defeat": "شکست نزدیک", "defeat": "شکست سنگین"}.get(result, result)
    log_battle(user_id, target_id,
               f"⚔️ {weapon_name_persian}×{count} علیه {target.get('player_name', 'نامشخص')} — {_res_fa}")
    
    # ========== 16. نمایش نتیجه به مهاجم ==========
    send_message(chat_id, result_text)
    
    for _hn in heal_notes:
        send_message(chat_id, "✚ " + _hn)

    # ========== 17. ارسال نتیجه نبرد به گروه ==========
    attacker_name = user.get('player_name', 'نامشخص')
    attacker_country = user.get('country', 'نامشخص')
    target_name = target.get('player_name', 'نامشخص')
    target_country = target.get('country', 'نامشخص')
    weapon_name = WEAPONS_SYSTEM.get(weapon, {}).get('name', weapon)
    
    _, remaining_attacks, _ = can_attack(user_id)
    
    if result == "victory":
        group_msg = f"⚔️ **نبرد نظامی** ⚔️\n━━━━━━━━━━━━━━━━━━\n🔥 {attacker_name} [{attacker_country}] با {weapon_name} به {target_name} [{target_country}] حمله کرد!\n💥 نتیجه: **پیروزی قاطع**\n💰 غنیمت: {loot:,} سکه\n🏆 امتیاز: {attacker_name} +{attacker_score_change} | {target_name} {defender_score_change}"
    elif result == "narrow_victory":
        group_msg = f"⚔️ **نبرد نظامی** ⚔️\n━━━━━━━━━━━━━━━━━━\n⚡ {attacker_name} [{attacker_country}] با {weapon_name} به {target_name} [{target_country}] حمله کرد!\n💥 نتیجه: **پیروزی سخت**\n💰 غنیمت: {loot:,} سکه\n🏆 امتیاز: {attacker_name} +{attacker_score_change} | {target_name} {defender_score_change}"
    elif result == "narrow_defeat":
        group_msg = f"⚔️ **نبرد نظامی** ⚔️\n━━━━━━━━━━━━━━━━━━\n💔 {attacker_name} [{attacker_country}] با {weapon_name} به {target_name} [{target_country}] حمله کرد!\n💥 نتیجه: **شکست نزدیک**\n💰 خسارت: {loot:,} سکه\n🏆 امتیاز: {attacker_name} {attacker_score_change} | {target_name} +{defender_score_change}"
    else:
        group_msg = f"⚔️ **نبرد نظامی** ⚔️\n━━━━━━━━━━━━━━━━━━\n💀 {attacker_name} [{attacker_country}] با {weapon_name} به {target_name} [{target_country}] حمله کرد!\n💥 نتیجه: **شکست سنگین**\n💰 خسارت: {loot:,} سکه\n🏆 امتیاز: {attacker_name} {attacker_score_change} | {target_name} +{defender_score_change}"
    
    send_to_group(group_msg)
    
    # ========== 18. نمایش پیام محدودیت باقیمانده ==========
    if remaining_attacks > 0:
        send_message(chat_id, f"📊 **تعداد حملات باقیمانده امروز: {remaining_attacks}/{ATTACK_LIMIT}**")
    else:
        send_message(chat_id, f"⚠️ **این آخرین حمله شما در 24 ساعت آینده بود!**\n⏳ 24 ساعت بعد می‌توانید دوباره حمله کنید.")
    
    # ========== 19. بازگشت به داشبورد ==========
    # 🔄 lazy import برای جلوگیری از حلقه
    from .dashboard import send_dashboard
    send_dashboard(chat_id, user_id)


def process_attack_text_input(chat_id, user_id, text):
    if user_id not in waiting_for_attack_count:
        return False
    try:
        count = int(text.replace(',', '').replace(' ', ''))
        attack_data = waiting_for_attack_count.pop(user_id)
        target_id = attack_data["target_id"]
        weapon = attack_data["weapon"]
        max_count = attack_data["max_count"]
        if count < 1:
            send_message(chat_id, "❌ تعداد باید حداقل 1 باشد!")
            return True
        if count > max_count:
            send_message(chat_id, f"❌ شما فقط {max_count} عدد {WEAPONS_SYSTEM.get(weapon, {}).get('name', weapon)} دارید!")
            return True
        process_attack(chat_id, user_id, target_id, weapon, count)
        return True
    except ValueError:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید! (مثال: 10, 50, 100)")
        return True


def reduce_user_weapon(user_id, weapon_type, loss_count):
    user = players_data.get(user_id, {})
    remaining_loss = loss_count
    
    if weapon_type == "tank":
        tank_list = ["simple", "zolfaghar", "karrar", "merkava", "challenger", 
                     "leclerc", "torpedo", "black_panther", "leopard", "abrams"]
        for tank_key in tank_list:
            if remaining_loss <= 0:
                break
            count_key = f"{tank_key}_tank_count"
            current = user.get(count_key, 0)
            if current > 0:
                remove = min(current, remaining_loss)
                players_data[user_id][count_key] = current - remove
                remaining_loss -= remove
        new_attack = 0
        for tank_key in tank_list:
            count = players_data[user_id].get(f"{tank_key}_tank_count", 0)
            power = TANKS.get(tank_key, {}).get("power", 0)
            new_attack += count * power
        players_data[user_id]["attack_power"] = new_attack
    
    elif weapon_type == "fighter":
        fighter_list = ["f4", "f18", "j10", "j16", "f16", "su27", "eurofighter", 
                        "j17", "golden_eagle", "j20", "su35", "su57", "f35", "su75", "f22"]
        for fighter_key in fighter_list:
            if remaining_loss <= 0:
                break
            count_key = f"{fighter_key}_fighter_count"
            current = user.get(count_key, 0)
            if current > 0:
                remove = min(current, remaining_loss)
                players_data[user_id][count_key] = current - remove
                remaining_loss -= remove
        new_attack = 0
        for fighter_key in fighter_list:
            count = players_data[user_id].get(f"{fighter_key}_fighter_count", 0)
            power = FIGHTERS.get(fighter_key, {}).get("power", 0)
            new_attack += count * power
        players_data[user_id]["attack_power"] = new_attack
    
    elif weapon_type == "helicopter":
        heli_list = ["normal", "cobra", "littlebird", "tiger", "crocodile", "shamook", "kamov52", "ah47", "apache"]
        for heli_key in heli_list:
            if remaining_loss <= 0:
                break
            count_key = f"{heli_key}_helicopter_count"
            current = user.get(count_key, 0)
            if current > 0:
                remove = min(current, remaining_loss)
                players_data[user_id][count_key] = current - remove
                remaining_loss -= remove
        new_attack = 0
        for heli_key in heli_list:
            count = players_data[user_id].get(f"{heli_key}_helicopter_count", 0)
            power = HELICOPTERS.get(heli_key, {}).get("power", 0)
            new_attack += count * power
        players_data[user_id]["attack_power"] = new_attack
    
    elif weapon_type == "drone":
        drone_list = ["ghaza", "surveillance", "suicide", "hermes", "shahed", "mk1", "mk9", "jetx147", "rq170"]
        for drone_key in drone_list:
            if remaining_loss <= 0:
                break
            count_key = f"{drone_key}_drone_count"
            current = user.get(count_key, 0)
            if current > 0:
                remove = min(current, remaining_loss)
                players_data[user_id][count_key] = current - remove
                remaining_loss -= remove
        new_attack = 0
        for drone_key in drone_list:
            count = players_data[user_id].get(f"{drone_key}_drone_count", 0)
            power = DRONES.get(drone_key, {}).get("power", 0)
            new_attack += count * power
        players_data[user_id]["attack_power"] = new_attack
    
    elif weapon_type == "missile":
        missile_list = ["point", "cruise", "ghadir", "khorramshahr", "sejil", "fatah", "tomahawk", "iskander", "dongfeng", "kinzhal", "hypersonic"]
        for missile_key in missile_list:
            if remaining_loss <= 0:
                break
            count_key = f"{missile_key}_missile_count"
            current = user.get(count_key, 0)
            if current > 0:
                remove = min(current, remaining_loss)
                players_data[user_id][count_key] = current - remove
                remaining_loss -= remove
        new_attack = 0
        for missile_key in missile_list:
            count = players_data[user_id].get(f"{missile_key}_missile_count", 0)
            power = MISSILES.get(missile_key, {}).get("power", 0)
            new_attack += count * power
        players_data[user_id]["attack_power"] = new_attack
    
    elif weapon_type == "naval":
        naval_list = ["simple_warship"]
        for naval_key in naval_list:
            if remaining_loss <= 0:
                break
            count_key = f"{naval_key}_naval_count"
            current = user.get(count_key, 0)
            if current > 0:
                remove = min(current, remaining_loss)
                players_data[user_id][count_key] = current - remove
                remaining_loss -= remove
        new_attack = 0
        for naval_key in naval_list:
            count = players_data[user_id].get(f"{naval_key}_naval_count", 0)
            power = NAVAL_VESSELS.get(naval_key, {}).get("power", 0)
            new_attack += count * power
        players_data[user_id]["attack_power"] = new_attack
    
    elif weapon_type == "submarine":
        sub_list = ["combat_sub"]
        for sub_key in sub_list:
            if remaining_loss <= 0:
                break
            count_key = f"{sub_key}_submarine_count"
            current = user.get(count_key, 0)
            if current > 0:
                remove = min(current, remaining_loss)
                players_data[user_id][count_key] = current - remove
                remaining_loss -= remove
        new_attack = 0
        for sub_key in sub_list:
            count = players_data[user_id].get(f"{sub_key}_submarine_count", 0)
            power = SUBMARINES.get(sub_key, {}).get("power", 0)
            new_attack += count * power
        players_data[user_id]["attack_power"] = new_attack
    
    elif weapon_type == "air_defense":
        defense_list = ["normal", "sling", "patriot", "s400", "iron_dome"]
        for defense_key in defense_list:
            if remaining_loss <= 0:
                break
            count_key = f"{defense_key}_air_defense_count"
            current = user.get(count_key, 0)
            if current > 0:
                remove = min(current, remaining_loss)
                players_data[user_id][count_key] = current - remove
                remaining_loss -= remove
        new_defense = 0
        for defense_key in defense_list:
            count = players_data[user_id].get(f"{defense_key}_air_defense_count", 0)
            power = AIR_DEFENSES.get(defense_key, {}).get("power", 0)
            new_defense += count * power
        players_data[user_id]["defense"] = 5000 + new_defense

    elif weapon_type == "ground":
        ground_list = ["normal_soldier", "professional_soldier", "border_guard", "commando", "bodyguard"]
        for ground_key in ground_list:
            if remaining_loss <= 0:
                break
            count_key = f"{ground_key}_ground_count"
            current = user.get(count_key, 0)
            if current > 0:
                remove = min(current, remaining_loss)
                players_data[user_id][count_key] = current - remove
                remaining_loss -= remove
    
    db.save_player(user_id, players_data[user_id])