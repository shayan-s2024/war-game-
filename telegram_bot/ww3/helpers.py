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
from .config import TG, ATTACK_LIMIT, ATTACK_WINDOW, BASE_URL, COMMAND_COOLDOWN, GROUP_ID, REQUIRED_CHANNELS, SPAM_LIMIT, SPAM_WINDOW, STATEMENT_LIMIT, STATEMENT_WINDOW, TG
from .state import cabinet_codes, db, hack_cooldown, players_data, sanctions_data, user_attacks, user_command_count, user_last_command, user_statements
from .static_data import AIR_DEFENSES, ARTILLERY, CABINET_KEYS, COUNTRIES_LIST, DRONES, FIGHTERS, HELICOPTERS, MISSILES, NAVAL_VESSELS, PILOTS, SUBMARINES, TANKS, WEAPONS_SYSTEM

# ==================== ماژول helpers ====================


# ==================== توابع کمکی ====================
def is_admin(user_id):
    return db.is_admin(user_id)


def generate_union_id():
    return ''.join(str(random.randint(0, 9)) for _ in range(12))


def get_union_capacity(level):
    capacities = {1: 2, 2: 4, 3: 6, 4: 8, 5: 10}
    return capacities.get(level, 2)


def get_union_level_price(level):
    return 50000 * level


def generate_unique_code():
    while True:
        code = str(random.randint(100000, 999999))
        code_exists = False
        for player_codes in cabinet_codes.values():
            if code in player_codes.values():
                code_exists = True
                break
        if not code_exists:
            return code


def get_cabinet_code(user_id, position_key):
    return cabinet_codes.get(user_id, {}).get(position_key)


def verify_cabinet_code(target_id, position_key, entered_code):
    stored_code = cabinet_codes.get(target_id, {}).get(position_key)
    return stored_code == entered_code


def log_battle(attacker_id, target_id, summary):
    """📜 ثبت نبرد در تاریخچه هر دو طرف"""
    stamp = time.strftime("%m/%d %H:%M")
    try:
        db.add_battle_log(attacker_id, f"{stamp} — {summary}")
        db.add_battle_log(target_id, f"{stamp} — {summary}")
    except Exception:
        pass


def get_missing_channels(user_id, force=False):
    """لیست کانال‌های اجباری که کاربر عضو آن‌ها نیست (با کش ۶۰ ثانیه‌ای)"""
    if not REQUIRED_CHANNELS:
        return []
    now = time.time()
    cached = state.join_check_cache.get(user_id)
    if not force and cached and now - cached[1] < 60:
        return cached[0]
    missing = []
    for ch in REQUIRED_CHANNELS:
        try:
            resp = TG.get(f"{BASE_URL}/getChatMember",
                          params={"chat_id": ch, "user_id": int(user_id)},
                          timeout=8).json()
            if resp.get("ok"):
                member = resp["result"]
                status = member.get("status")
                is_member = status in ("creator", "administrator", "member") or (
                    status == "restricted" and member.get("is_member"))
                if not is_member:
                    missing.append(ch)
            else:
                print(f"⚠️ عضویت در {ch} قابل بررسی نیست: {resp.get('description')}\n"
                      f"   🔑 راه‌حل: ربات را به عنوان ادمین به کانال {ch} اضافه کنید")
        except Exception as e:
            print(f"⚠️ خطا در بررسی عضویت کانال {ch}: {e}")
    state.join_check_cache[user_id] = (missing, now)
    return missing


def edit_message(chat_id, message_id, text, keyboard=None):
    """ویرایش همون پیام منو (به‌جای اسپم پیام جدید)"""
    url = f"{BASE_URL}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if keyboard:
        payload["reply_markup"] = keyboard
    try:
        resp = TG.post(url, json=payload, timeout=10).json()
        if resp.get("ok"):
            return True
    except Exception:
        pass
    return False


def show_screen(chat_id, text, keyboard=None):
    """نمایش منو: اگر پیام منویی قبلاً باز باشد همان را ویرایش می‌کند، وگرنه پیام جدید می‌فرستد"""
    mid = state.menu_message.get(str(chat_id))
    if mid:
        if edit_message(chat_id, mid, text, keyboard):
            return
        state.menu_message.pop(str(chat_id), None)
    send_message(chat_id, text, keyboard)


def hospital_heal(player_id, lost_units):
    """🏥 بیمارستان‌ها بخشی از تلفات زمینی را درمان می‌کنند (با سقف روزانه)"""
    if lost_units <= 0:
        return 0
    p = players_data.get(player_id)
    if not p:
        return 0
    normal = p.get("normal_hospital_count", 0)
    pro = p.get("professional_hospital_count", 0)
    if normal <= 0 and pro <= 0:
        return 0
    today = time.strftime("%Y%m%d")
    if p.get("heal_date") != today:
        p["heal_date"] = today
        p["healed_today"] = 0
    remaining = (normal * 1500 + pro * 3000) - p.get("healed_today", 0)
    if remaining <= 0:
        return 0
    heal_pct = min(0.5, normal * 0.15 + pro * 0.25)
    healed = min(int(lost_units * heal_pct), remaining)
    if healed > 0:
        p["healed_today"] = p.get("healed_today", 0) + healed
        p["normal_soldier_ground_count"] = p.get("normal_soldier_ground_count", 0) + healed
    return healed


def metro_shelter_factor(player_id):
    """🚉 مترو پناهگاه است: تلفات جمعیت را کم می‌کند — هر مترو ۱۵٪، حداکثر ۶۰٪"""
    metros = players_data.get(player_id, {}).get("metro_count", 0)
    return max(0.4, 1.0 - 0.15 * metros)


def weighted_quality(player_id, cat_dict, suffix):
    """⚖️ میانگین وزنی کیفیت واحدهای یک دسته — (میانگین q، تعداد واقعی)"""
    p = players_data.get(player_id, {})
    total = 0
    qsum = 0.0
    for key, item in cat_dict.items():
        c = p.get(f"{key}_{suffix}", 0)
        if c > 0:
            total += c
            qsum += c * item.get("q", 1.0)
    if total == 0:
        return 1.0, 0
    return qsum / total, total


def send_message(chat_id, text, keyboard=None):
    """ارسال پیام جدید (بدون ویرایش)"""
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = keyboard
    try:
        response = TG.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"خطا: {e}")
        return None


def send_to_group(text):
    """ارسال پیام به گروه"""
    if not GROUP_ID:
        return None
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": GROUP_ID, "text": text}
    try:
        response = TG.post(url, json=payload, timeout=10)
        return response.json()
    except:
        return None


def answer_callback(callback_id):
    """پاسخ به callback query"""
    url = f"{BASE_URL}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    try:
        TG.post(url, json=payload, timeout=10)
    except:
        pass


# ==================== 📌 Reply Keyboard ====================
def send_reply_keyboard(chat_id, user_id=None, force=False):
    """ارسال Reply Keyboard با دکمه‌های اصلی بازی
    
    آرایش:
    ┌─────────────────────────────┐
    │        🚀 شروع              │  ← یه ردیف تنها (بزرگ‌ترین)
    ├──────────────┬──────────────┤
    │ 🔄 بروزرسانی │ 👥 دعوت      │
    ├──────────────┼──────────────┤
    │ 📖 راهنما    │ 📜 نبردها    │
    └──────────────┴──────────────┘
    """
    # 📌 چک کن اگه قبلاً فرستاده شده، دوباره نفرست
    if user_id and not force:
        key = f"reply_kb_sent_{user_id}"
        if state.menu_message.get(key):
            return  # قبلاً فرستاده شده
    elif not force:
        key = f"reply_kb_sent_{chat_id}"
        if state.menu_message.get(key):
            return
    
    url = f"{BASE_URL}/sendMessage"
    
    keyboard = {
        "keyboard": [
            # 🚀 ردیف اول: دکمه شروع (تنها — بزرگ‌ترین)
            [{"text": "🚀 شروع"}],
            # ردیف دوم: بروزرسانی + دعوت
            [{"text": "🔄 بروزرسانی"}, {"text": "👥 دعوت دوستان"}],
            # ردیف سوم: راهنما + نبردها
            [{"text": "📖 راهنمای بازی"}, {"text": "📜 نبردهای من"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "is_persistent": True
    }
    
    payload = {
        "chat_id": chat_id,
        "text": "🎮 **منوی سریع فعال شد**\nاز دکمه‌های زیر می‌تونی به راحتی استفاده کنی 👇",
        "reply_markup": keyboard,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = TG.post(url, json=payload, timeout=10).json()
        if resp.get("ok"):
            cache_key = f"reply_kb_sent_{user_id or chat_id}"
            state.menu_message[cache_key] = True
            return True
    except Exception as e:
        print(f"خطا در ارسال reply keyboard: {e}")
    return False


def remove_reply_keyboard(chat_id, user_id=None):
    """حذف Reply Keyboard"""
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "❌ منوی سریع حذف شد",
        "reply_markup": {"remove_keyboard": True}
    }
    try:
        TG.post(url, json=payload, timeout=10)
        cache_key = f"reply_kb_sent_{user_id or chat_id}"
        state.menu_message.pop(cache_key, None)
        return True
    except Exception as e:
        print(f"خطا در حذف reply keyboard: {e}")
        return False


def is_reply_keyboard_sent(user_id):
    """چک میکنه که آیا Reply Keyboard قبلاً فرستاده شده یا نه"""
    key = f"reply_kb_sent_{user_id}"
    return bool(state.menu_message.get(key))


# ==================== 📌 توابع پایان فصل ====================
def delete_message(chat_id, message_id):
    """حذف یک پیام (فقط پیام‌های ربات در 48 ساعت اخیر)"""
    url = f"{BASE_URL}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    try:
        resp = TG.post(url, json=payload, timeout=5).json()
        return resp.get("ok", False)
    except Exception:
        return False


def send_season_ended_notification(chat_id):
    """ارسال پیام «فصل تمام شد» + حذف Reply Keyboard"""
    url = f"{BASE_URL}/sendMessage"
    text = (
        "🏁 **فصل به پایان رسید!** 🏁\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🎊 از بازی شما در این فصل متشکریم!\n\n"
        "🔄 **فصل جدید شروع شده است.**\n\n"
        "📌 برای شرکت در فصل جدید:\n"
        "1️⃣ دستور /start را بفرستید\n"
        "2️⃣ مجدداً ثبت‌نام کنید\n"
        "3️⃣ نام و کشور جدید انتخاب کنید\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🚀 **منتظر شما در فصل جدید هستیم!**"
    )
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"remove_keyboard": True},
        "parse_mode": "Markdown"
    }
    try:
        return TG.post(url, json=payload, timeout=10).json()
    except Exception:
        return None


# ==================== توابع کشور ====================
def get_country_continent(country_name):
    """پیدا کردن قاره یک کشور با جستجوی کامل"""
    if not country_name:
        return None, None
    for continent_key, continent_data in COUNTRIES_LIST.items():
        countries = continent_data.get("countries", {})
        
        if country_name in countries:
            return continent_key, continent_data["name"]
        
        for c_name in countries.keys():
            if c_name.strip() == country_name.strip():
                return continent_key, continent_data["name"]
    
    return None, None


def get_country_continent_key(country_name):
    """پیدا کردن کلید قاره یک کشور"""
    if not country_name:
        return None
    for continent_key, continent_data in COUNTRIES_LIST.items():
        if country_name in continent_data.get("countries", {}):
            return continent_key
        for c_name in continent_data.get("countries", {}).keys():
            if c_name.strip() == country_name.strip():
                return continent_key
    return None


def get_total_countries_count():
    """تعداد کل کشورهای بازی"""
    total = 0
    for continent in COUNTRIES_LIST.values():
        total += len(continent.get("countries", {}))
    return total


# ==================== توابع ضد اسپم ====================
def is_spam(user_id):
    """بررسی اسپم بودن کاربر"""
    current_time = time.time()
    
    if user_id in user_last_command:
        time_diff = current_time - user_last_command[user_id]
        if time_diff < COMMAND_COOLDOWN:
            remaining = int(COMMAND_COOLDOWN - time_diff)
            return True, f"⏰ **لطفاً {remaining} ثانیه بین هر عملیات صبر کنید!**"
    
    if user_id not in user_command_count:
        user_command_count[user_id] = {"count": 1, "reset_time": current_time + SPAM_WINDOW}
    else:
        user_data = user_command_count[user_id]
        if current_time > user_data["reset_time"]:
            user_command_count[user_id] = {"count": 1, "reset_time": current_time + SPAM_WINDOW}
        else:
            user_data["count"] += 1
            if user_data["count"] > SPAM_LIMIT:
                remaining = int(user_data["reset_time"] - current_time)
                return True, f"⚠️ **شما بیش از حد مجاز درخواست ارسال کردید!**\n⏳ لطفاً {remaining} ثانیه صبر کنید."
    
    user_last_command[user_id] = current_time
    return False, ""


# ==================== توابع دریافت تعداد تجهیزات ====================
def get_user_tank_count(user_id):
    user = players_data.get(user_id, {})
    count = 0
    for key in TANKS.keys():
        count += user.get(f"{key}_tank_count", 0)
    return count


def get_user_fighter_count(user_id):
    user = players_data.get(user_id, {})
    count = 0
    for key in FIGHTERS.keys():
        count += user.get(f"{key}_fighter_count", 0)
    return count


def get_user_helicopter_count(user_id):
    user = players_data.get(user_id, {})
    count = 0
    for key in HELICOPTERS.keys():
        count += user.get(f"{key}_helicopter_count", 0)
    return count


def get_user_missile_count(user_id):
    user = players_data.get(user_id, {})
    count = 0
    for key in MISSILES.keys():
        count += user.get(f"{key}_missile_count", 0)
    return count


def get_user_drone_count(user_id):
    user = players_data.get(user_id, {})
    count = 0
    for key in DRONES.keys():
        count += user.get(f"{key}_drone_count", 0)
    return count


def get_user_navy_count(user_id):
    user = players_data.get(user_id, {})
    count = 0
    for key in NAVAL_VESSELS.keys():
        count += user.get(f"{key}_naval_count", 0)
    return count


def get_user_submarine_count(user_id):
    user = players_data.get(user_id, {})
    count = 0
    for key in SUBMARINES.keys():
        count += user.get(f"{key}_submarine_count", 0)
    return count


def get_user_air_defense_count(user_id):
    user = players_data.get(user_id, {})
    count = 0
    for key in AIR_DEFENSES.keys():
        count += user.get(f"{key}_air_defense_count", 0)
    return count


# ==================== توابع کمکی خلبان ====================
def get_pilot_type_for_fighter(fighter_key):
    for pilot_type, pilot_info in PILOTS.items():
        if pilot_info.get("for_type") == "helicopter":
            continue
        if fighter_key in pilot_info.get("fighters", []):
            return pilot_type
    return None


def check_pilot_available(user_id, fighter_key):
    user = players_data.get(user_id, {})
    if fighter_key == "helicopter":
        pilot_count = user.get("helicopter_pilot_count", 0)
        return pilot_count > 0, "helicopter"
    pilot_type = get_pilot_type_for_fighter(fighter_key)
    if pilot_type:
        pilot_count = user.get(f"{pilot_type}_pilot_count", 0)
        return pilot_count > 0, pilot_type
    return False, None


def use_pilot(user_id, fighter_key, count=1):
    user = players_data.get(user_id, {})
    if fighter_key == "helicopter":
        pilot_type = "helicopter"
    else:
        pilot_type = get_pilot_type_for_fighter(fighter_key)
    if not pilot_type:
        return False
    pilot_key = f"{pilot_type}_pilot_count"
    current = user.get(pilot_key, 0)
    if current >= count:
        players_data[user_id][pilot_key] = current - count
        db.save_player(user_id, players_data[user_id])
        return True
    return False


def get_user_fighter_count_with_pilot(user_id):
    user = players_data.get(user_id, {})
    total = 0
    for fighter_key in FIGHTERS.keys():
        fighter_count = user.get(f"{fighter_key}_fighter_count", 0)
        pilot_type = get_pilot_type_for_fighter(fighter_key)
        if pilot_type:
            pilot_count = user.get(f"{pilot_type}_pilot_count", 0)
            total += min(fighter_count, pilot_count)
    return total


def get_user_helicopter_count_with_pilot(user_id):
    user = players_data.get(user_id, {})
    heli_count = 0
    for heli_key in HELICOPTERS.keys():
        heli_count += user.get(f"{heli_key}_helicopter_count", 0)
    pilot_count = user.get("helicopter_pilot_count", 0)
    return min(heli_count, pilot_count)


# ==================== توابع تحریم ====================
def is_sanctioned(user_id):
    """چک میکنه که آیا کاربر تحریمه یا نه"""
    if user_id in sanctions_data:
        sanction = sanctions_data[user_id]
        if sanction["end_date"] > time.time():
            return True, sanction["price_penalty"], sanction["end_date"]
        else:
            del sanctions_data[user_id]
            db.remove_sanction(user_id)
    return False, 0, 0


# ==================== توابع سیستم کابینه ====================
def generate_all_cabinet_codes(user_id, cabinet):
    """تولید کدهای امنیتی برای همه مقام‌های کابینه"""
    if user_id not in cabinet_codes:
        cabinet_codes[user_id] = {}
    for key in CABINET_KEYS:
        member_name = cabinet.get(key, "")
        if member_name and member_name != "❌":
            if key not in cabinet_codes[user_id]:
                cabinet_codes[user_id][key] = generate_unique_code()
    for key, code in cabinet_codes[user_id].items():
        db.save_cabinet_code(user_id, key, code)
    return cabinet_codes[user_id]


def is_war_allowed():
    """چک میکنه که آیا جنگ فعاله یا نه"""
    return state.war_active or (state.war_start_time and state.war_end_time and state.war_start_time <= time.time() <= state.war_end_time)


WEAPON_CATEGORIES = {
    "tank": (TANKS, "tank_count"),
    "fighter": (FIGHTERS, "fighter_count"),
    "helicopter": (HELICOPTERS, "helicopter_count"),
    "drone": (DRONES, "drone_count"),
    "navy": (NAVAL_VESSELS, "naval_count"),
    "submarine": (SUBMARINES, "submarine_count"),
    "missile": (MISSILES, "missile_count"),
    "artillery": (ARTILLERY, "artillery_count"),
    "air_defense": (AIR_DEFENSES, "air_defense_count"),
}


def calculate_battle_power(attacker_weapon, defender_weapon, attacker_count, defender_count,
                           target_id=None, attacker_quality=1.0, defender_quality=1.0):
    """⚖️ نبرد کیفی: کیفیت واحدها هم‌ارز تعداد است و واحدهای باکیفیت کمتر تلف می‌دهند"""
    attacker = WEAPONS_SYSTEM[attacker_weapon]
    defender = WEAPONS_SYSTEM[defender_weapon]
    effectiveness = attacker["effectiveness"].get(defender_weapon, 1.0)
    attacker_power = attacker["damage"] * math.sqrt(max(1, attacker_count) * attacker_quality) * effectiveness
    defender_power = defender["defense"] * math.sqrt(max(1, defender_count) * defender_quality)
    if defender_weapon == "air_defense" and target_id and is_defense_disabled(target_id):
        defender_power = defender_power * 0.3
    random_factor = random.uniform(0.85, 1.15)
    attacker_power *= random_factor
    defender_power *= random_factor
    power_ratio = attacker_power / (defender_power + 1)
    if power_ratio > 1.5:
        result, a_f, d_f = "victory", 0.05, 0.7
    elif power_ratio > 0.9:
        result, a_f, d_f = "narrow_victory", 0.2, 0.5
    elif power_ratio > 0.6:
        result, a_f, d_f = "narrow_defeat", 0.5, 0.3
    else:
        result, a_f, d_f = "defeat", 0.7, 0.1
    attacker_loss = min(attacker_count, max(1, int(attacker_count * a_f / max(0.3, attacker_quality))))
    defender_loss = min(defender_count, max(1, int(defender_count * d_f / max(0.3, defender_quality))))
    return result, attacker_loss, defender_loss, power_ratio


def get_defense_power(user_id):
    """قدرت دفاع هکری کاربر (بر اساس تعداد هکرها)"""
    user = players_data.get(user_id, {})
    weak_count = user.get("weak_hacker_count", 0)
    medium_count = user.get("medium_hacker_count", 0)
    strong_count = user.get("strong_hacker_count", 0)
    elite_count = user.get("elite_hacker_count", 0)
    defense_power = (weak_count * 1) + (medium_count * 5) + (strong_count * 25) + (elite_count * 50)
    return defense_power


def is_defense_hacker_active(user_id):
    """چک میکنه که آیا حالت تدافعی هکری فعاله یا نه"""
    defense_data = hack_cooldown.get("defense_hackers", {})
    if user_id in defense_data:
        if defense_data[user_id] > time.time():
            return True
        else:
            del defense_data[user_id]
            db.save_hack_cooldown(user_id, "defense_hackers", 0)
    return False


def is_missile_disabled(target_id):
    """چک میکنه که آیا موشک‌های کاربر غیرفعال شدن یا نه"""
    missiles = hack_cooldown.get("disabled_missiles", {})
    if target_id in missiles:
        if missiles[target_id] > time.time():
            return True
        else:
            del missiles[target_id]
            db.save_hack_cooldown(target_id, "disabled_missiles", 0)
    return False


def is_defense_disabled(target_id):
    """چک میکنه که آیا پدافندهای کاربر غیرفعال شدن یا نه"""
    defenses = hack_cooldown.get("disabled_defenses", {})
    if target_id in defenses:
        if defenses[target_id] > time.time():
            return True
        else:
            del defenses[target_id]
            db.save_hack_cooldown(target_id, "disabled_defenses", 0)
    return False


# ==================== توابع محدودیت حمله ====================
def can_attack(user_id):
    """بررسی می‌کند که کاربر می‌تواند حمله کند یا نه"""
    current_time = time.time()
    
    if user_id not in user_attacks:
        user_attacks[user_id] = []
        return True, ATTACK_LIMIT, 0
    
    user_attacks[user_id] = [ts for ts in user_attacks[user_id] if current_time - ts < ATTACK_WINDOW]
    
    remaining = ATTACK_LIMIT - len(user_attacks[user_id])
    
    if len(user_attacks[user_id]) >= ATTACK_LIMIT:
        oldest = min(user_attacks[user_id])
        wait_seconds = int((oldest + ATTACK_WINDOW) - current_time)
        wait_hours = wait_seconds // 3600
        wait_minutes = (wait_seconds % 3600) // 60
        return False, 0, (wait_hours, wait_minutes)
    
    return True, remaining, 0


def add_attack_record(user_id):
    """ثبت یک حمله جدید برای کاربر"""
    current_time = time.time()
    
    if user_id not in user_attacks:
        user_attacks[user_id] = []
    
    user_attacks[user_id] = [ts for ts in user_attacks[user_id] if current_time - ts < ATTACK_WINDOW]
    user_attacks[user_id].append(current_time)
    # 🔒 ماندگار در دیتابیس
    db.set_game_config('attack_limits', json.dumps(user_attacks))


def find_player_by_input(search_text):
    """جستجوی بازیکن با آیدی یا نام کشور"""
    search_text = search_text.strip()
    
    if search_text.isdigit():
        if search_text in players_data:
            return search_text, players_data[search_text].get('player_name', 'نامشخص')
    
    for uid, data in players_data.items():
        country = data.get('country')
        if country is not None and country.lower() == search_text.lower():
            return uid, data.get('player_name', 'نامشخص')
    
    for uid, data in players_data.items():
        country = data.get('country')
        if country is not None and search_text.lower() in country.lower():
            return uid, data.get('player_name', 'نامشخص')
    
    return None, None


def get_game_day():
    """محاسبه روز بازی از زمان شروع"""
    elapsed_seconds = time.time() - state.game_start_date
    elapsed_days = elapsed_seconds // 86400
    return int(elapsed_days) + 1


def is_virus_active():
    """چک میکنه که آیا ویروس‌ها فعالن یا نه"""
    current_day = get_game_day()
    return current_day >= state.virus_start_day


# ==================== توابع محدودیت بیانیه ====================
def can_send_statement(user_id):
    """بررسی می‌کند که کاربر می‌تواند بیانیه بفرستد یا نه"""
    current_time = time.time()
    
    if user_id not in user_statements:
        user_statements[user_id] = []
        return True, STATEMENT_LIMIT, 0
    
    user_statements[user_id] = [ts for ts in user_statements[user_id] if current_time - ts < STATEMENT_WINDOW]
    
    remaining = STATEMENT_LIMIT - len(user_statements[user_id])
    
    if len(user_statements[user_id]) >= STATEMENT_LIMIT:
        oldest = min(user_statements[user_id])
        wait_seconds = int((oldest + STATEMENT_WINDOW) - current_time)
        wait_hours = wait_seconds // 3600
        wait_minutes = (wait_seconds % 3600) // 60
        return False, 0, (wait_hours, wait_minutes)
    
    return True, remaining, 0


def add_statement_record(user_id):
    """ثبت یک بیانیه جدید برای کاربر"""
    current_time = time.time()
    
    if user_id not in user_statements:
        user_statements[user_id] = []
    
    user_statements[user_id] = [ts for ts in user_statements[user_id] if current_time - ts < STATEMENT_WINDOW]
    user_statements[user_id].append(current_time)


def get_updates():
    """دریافت آپدیت‌ها از تلگرام"""
    url = f"{BASE_URL}/getUpdates"
    params = {"offset": state.last_update_id + 1, "timeout": 30}
    try:
        response = TG.get(url, params=params, timeout=35)
        data = response.json()
        return data.get("result", []) if data.get("ok") else []
    except Exception:
        return []