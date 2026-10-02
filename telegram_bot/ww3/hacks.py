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
from .helpers import get_defense_power, get_user_drone_count, get_user_fighter_count, is_war_allowed, send_message, send_to_group
from .state import assassination_cooldown, assassination_info, cabinet_codes, db, hack_cooldown, players_data, waiting_for_assassination_code, waiting_for_assassination_method, waiting_for_hack_count, waiting_for_hack_target
from .static_data import CABINET_OPTIONS, GROUND_FORCES

# ==================== ماژول hacks ====================


def attack_hacker_from_search(chat_id, user_id, target_id):
    """حمله هکری مستقیم از نتایج جستجو"""
    if not is_war_allowed():
        send_message(chat_id, "⛔ **جنگ جهانی فعال نیست!**")
        return
    
    user = players_data.get(user_id, {})
    weak_count = user.get("weak_hacker_count", 0)
    medium_count = user.get("medium_hacker_count", 0)
    strong_count = user.get("strong_hacker_count", 0)
    
    if medium_count == 0 and strong_count == 0:
        send_message(chat_id, "❌ **شما هکر متوسط یا قوی ندارید!**\n\n💻 هکر متوسط: اطلاعاتی + از کار انداختن پدافند\n💻 هکر قوی: همه قابلیت‌ها\n💰 از فروشگاه تهاجمی بخرید.")
        return
    
    keyboard = []
    if medium_count > 0:
        keyboard.append([{"text": f"🟠 هکر متوسط (موجودی: {medium_count})", "callback_data": f"hack_search_medium_{target_id}"}])
    if strong_count > 0:
        keyboard.append([{"text": f"🔴 هکر قوی (موجودی: {strong_count})", "callback_data": f"hack_search_strong_{target_id}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": f"attack_weapon_back_{target_id}"}])
    
    target_name = players_data.get(target_id, {}).get("player_name", "نامشخص")
    
    send_message(chat_id, 
        f"💻 **حمله هکری به {target_name}**\n━━━━━━━━━━━━━━━━━━\n"
        f"🌍 بدون محدودیت قاره‌ای!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ هکر ضعیف فقط برای دفاع است!\n\n"
        f"**سطح هکر را انتخاب کنید:**", 
        {"inline_keyboard": keyboard})


def process_hack_from_search(chat_id, user_id, hacker_level, target_id):
    """پردازش حمله هکری از نتایج جستجو"""
    if hacker_level == "medium":
        max_count = players_data.get(user_id, {}).get("medium_hacker_count", 0)
        power_per_hacker = 5
        hacker_name = "هکر متوسط"
    elif hacker_level == "strong":
        max_count = players_data.get(user_id, {}).get("strong_hacker_count", 0)
        power_per_hacker = 25
        hacker_name = "هکر قوی"
    else:
        send_message(chat_id, "❌ سطح هکر نامعتبر!")
        return
    
    if max_count <= 0:
        send_message(chat_id, f"❌ شما {hacker_name} ندارید!")
        return
    
    waiting_for_hack_count[user_id] = {
        "target_id": target_id,
        "hacker_level": hacker_level,
        "max_count": max_count,
        "power_per_hacker": power_per_hacker
    }
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "1", "callback_data": f"hack_count_1"}, {"text": "2", "callback_data": f"hack_count_2"}, {"text": "3", "callback_data": f"hack_count_3"}],
            [{"text": "5", "callback_data": f"hack_count_5"}, {"text": "10", "callback_data": f"hack_count_10"}, {"text": f"حداکثر ({max_count})", "callback_data": f"hack_count_{max_count}"}],
            [{"text": "🔙 انصراف", "callback_data": "attack_menu"}]
        ]
    }
    
    target_name = players_data.get(target_id, {}).get("player_name", "نامشخص")
    
    send_message(chat_id, 
        f"💻 **حمله با {hacker_name}**\n━━━━━━━━━━━━━━━━━━\n"
        f"🎯 هدف: {target_name}\n"
        f"📊 تعداد موجود: {max_count}\n"
        f"⚡ قدرت هر هکر: {power_per_hacker}\n\n"
        f"🔢 **تعداد هکر برای حمله را انتخاب کنید:**", 
        keyboard)


def attack_hacker_menu(chat_id, user_id):
    user = players_data.get(user_id, {})
    weak_count = user.get("weak_hacker_count", 0)
    medium_count = user.get("medium_hacker_count", 0)
    strong_count = user.get("strong_hacker_count", 0)
    if weak_count == 0 and medium_count == 0 and strong_count == 0:
        send_message(chat_id, "❌ **شما هیچ هکری ندارید!** از فروشگاه بخرید.")
        return
    text = f"💻 **حمله هکری**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"🟡 هکر ضعیف: {weak_count} عدد (فقط دفاعی)\n"
    text += f"🟠 هکر متوسط: {medium_count} عدد (اطلاعاتی + پدافند)\n"
    text += f"🔴 هکر قوی: {strong_count} عدد (همه قابلیت‌ها)\n━━━━━━━━━━━━━━━━━━\n"
    text += f"نوع حمله را انتخاب کنید:"
    keyboard = {
        "inline_keyboard": [
            [{"text": "🟡 حمله با هکر ضعیف", "callback_data": "hack_weak"}],
            [{"text": "🟠 حمله با هکر متوسط", "callback_data": "hack_medium"}],
            [{"text": "🔴 حمله با هکر قوی", "callback_data": "hack_strong"}],
            [{"text": "🔙 بازگشت", "callback_data": "attack_menu"}]
        ]
    }
    send_message(chat_id, text, keyboard)


def select_hack_target(chat_id, user_id, hacker_level):
    if hacker_level == "weak":
        send_message(chat_id, "❌ **هکر ضعیف فقط برای دفاع است!**\nبرای حمله از هکر متوسط یا قوی استفاده کنید.")
        return
    targets = []
    for target_id, target_data in players_data.items():
        if target_id == user_id:
            continue
        if not target_data.get("player_name"):
            continue
        targets.append(target_id)
    if not targets:
        send_message(chat_id, "❌ **هیچ هدف قابل حمله‌ای یافت نشد!**")
        return
    waiting_for_hack_target[user_id] = {"level": hacker_level, "targets": targets}
    keyboard = []
    for tid in targets[:10]:
        target_name = players_data[tid].get('player_name', 'نامشخص')
        keyboard.append([{"text": f"🎯 {target_name}", "callback_data": f"hack_target_{tid}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    hacker_name = "هکر متوسط" if hacker_level == "medium" else "هکر قوی"
    send_message(chat_id, f"💻 **حمله با {hacker_name}**\n\n🌍 بدون محدودیت قاره‌ای!\n\nهدف مورد نظر را انتخاب کنید:", {"inline_keyboard": keyboard})


def process_hack_target_selection(chat_id, user_id, target_id):
    if user_id not in waiting_for_hack_target:
        send_message(chat_id, "❌ درخواست نامعتبر!")
        return
    hack_data = waiting_for_hack_target.pop(user_id)
    hacker_level = hack_data["level"]
    select_hack_attack_count(chat_id, user_id, target_id, hacker_level)


def select_hack_attack_count(chat_id, user_id, target_id, hacker_level):
    user = players_data.get(user_id, {})
    if hacker_level == "medium":
        max_count = user.get("medium_hacker_count", 0)
        hacker_name = "هکر متوسط"
        power_per_hacker = 5
    elif hacker_level == "strong":
        max_count = user.get("strong_hacker_count", 0)
        hacker_name = "هکر قوی"
        power_per_hacker = 25
    else:
        send_message(chat_id, "❌ هکر ضعیف نمی‌تواند حمله کند! فقط دفاعی است.")
        return
    if max_count <= 0:
        send_message(chat_id, f"❌ شما {hacker_name} ندارید!")
        return
    waiting_for_hack_count[user_id] = {
        "target_id": target_id,
        "hacker_level": hacker_level,
        "max_count": max_count,
        "power_per_hacker": power_per_hacker
    }
    keyboard = {
        "inline_keyboard": [
            [{"text": "1", "callback_data": f"hack_count_1"}, {"text": "2", "callback_data": f"hack_count_2"}, {"text": "3", "callback_data": f"hack_count_3"}],
            [{"text": "5", "callback_data": f"hack_count_5"}, {"text": "10", "callback_data": f"hack_count_10"}, {"text": f"حداکثر ({max_count})", "callback_data": f"hack_count_{max_count}"}],
            [{"text": "🔙 انصراف", "callback_data": "attack_menu"}]
        ]
    }
    send_message(chat_id, f"💻 **حمله با {hacker_name}**\n━━━━━━━━━━━━━━━━━━\n🎯 هدف: {players_data[target_id].get('player_name')}\n📊 تعداد موجود: {max_count}\n⚡ قدرت هر هکر: {power_per_hacker}\n\n🔢 تعداد هکر برای حمله را انتخاب کنید:", keyboard)


def process_hack_attack(chat_id, user_id, target_id, hacker_level, count):
    user = players_data.get(user_id, {})
    target = players_data.get(target_id, {})
    if hacker_level == "medium":
        if user.get("medium_hacker_count", 0) < count:
            send_message(chat_id, "❌ تعداد هکر متوسط کافی نیست!")
            return
        attack_power = count * 5
    elif hacker_level == "strong":
        if user.get("strong_hacker_count", 0) < count:
            send_message(chat_id, "❌ تعداد هکر قوی کافی نیست!")
            return
        attack_power = count * 25
    else:
        send_message(chat_id, "❌ نوع هکر نامعتبر!")
        return
    defense_power = get_defense_power(target_id)
    if defense_power == 0:
        success = True
        attacker_loss = 0
    elif attack_power > defense_power:
        success = True
        attacker_loss = max(1, int(count * 0.2))
    else:
        success = False
        attacker_loss = max(1, int(count * 0.2))
    if hacker_level == "medium":
        players_data[user_id]["medium_hacker_count"] = user.get("medium_hacker_count", 0) - attacker_loss
    else:
        players_data[user_id]["strong_hacker_count"] = user.get("strong_hacker_count", 0) - attacker_loss
    if success:
        target_codes = cabinet_codes.get(target_id, {})
        if not target_codes:
            send_message(chat_id, "❌ **هدف کدهای امنیتی ندارد!**")
            db.save_player(user_id, players_data[user_id])
            return
        text = f"✅ **حمله هکری موفق!**\n━━━━━━━━━━━━━━━━━━\n"
        text += f"🎯 هدف: {target.get('player_name')}\n"
        text += f"🌍 کشور: {target.get('country')}\n"
        text += f"⚔️ قدرت حمله: {attack_power} | 🛡 قدرت دفاع: {defense_power}\n"
        text += f"💀 تلفات شما: {attacker_loss} هکر (20%)\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"🔐 **کدهای امنیتی به دست آمده:**\n━━━━━━━━━━━━━━━━━━\n"
        if user_id not in assassination_info:
            assassination_info[user_id] = {}
        for key, code in target_codes.items():
            cabinet_name = CABINET_OPTIONS.get(key, {}).get("name", key)
            icon = CABINET_OPTIONS.get(key, {}).get("icon", "🔑")
            member_name = target.get("cabinet", {}).get(key, "نامشخص")
            text += f"\n{icon} {cabinet_name}\n"
            text += f"🔑 کد: `{code}`\n"
            text += f"👤 {member_name}\n━━━━━━━━━━━━━━━━━━\n"
            assassination_info[user_id][f"{target_id}_{key}"] = {
                "code": code,
                "member_name": member_name,
                "position_name": cabinet_name,
                "icon": icon,
                "member_key": key,
                "target_id": target_id,
                "obtained_at": time.time()
            }
            db.save_assassination_info(user_id, target_id, key, assassination_info[user_id][f"{target_id}_{key}"])
        db.save_player(user_id, players_data[user_id])
        send_message(chat_id, text)
        send_message(int(target_id), 
            f"⚠️ **هشدار امنیتی شدید!**\n━━━━━━━━━━━━━━━━━━\n"
            f"🔐 کدهای امنیتی کابینه شما به سرقت رفت!\n"
            f"🛡 قدرت دفاعی شما: {defense_power}\n"
            f"⚔️ قدرت حمله دشمن: {attack_power}\n"
            f"⚠️ دشمن می‌تواند مقامات شما را ترور کند!")
    else:
        text = f"❌ **حمله هکری ناموفق!**\n━━━━━━━━━━━━━━━━━━\n"
        text += f"🎯 هدف: {target.get('player_name')}\n"
        text += f"⚔️ قدرت حمله شما: {attack_power}\n"
        text += f"🛡 قدرت دفاع هدف: {defense_power}\n"
        text += f"💀 تلفات شما: {attacker_loss} هکر (20%)\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"💡 هکرهای بیشتری بخرید و دوباره تلاش کنید!"
        send_message(chat_id, text)
        send_message(int(target_id),
            f"🛡 **دفاع هکری موفق!**\n━━━━━━━━━━━━━━━━━━\n"
            f"🎯 حمله کننده: {user.get('player_name')}\n"
            f"🛡 قدرت دفاع شما: {defense_power}\n"
            f"⚔️ قدرت حمله دشمن: {attack_power}\n"
            f"✅ هکرهای دشمن 20% تلفات دادند!")
    if success:
        group_msg = f"💻 **حمله هکری** 💻\n━━━━━━━━━━━━━━━━━━\n🎯 {user.get('player_name', 'نامشخص')} [{user.get('country', 'نامشخص')}] کدهای امنیتی {target.get('player_name', 'نامشخص')} [{target.get('country', 'نامشخص')}] را دزدید!\n🔐 اطلاعات محرمانه به سرقت رفت!"
        send_to_group(group_msg)
    db.save_player(user_id, players_data[user_id])
    # 🔄 lazy import برای جلوگیری از حلقه import
    from .dashboard import send_dashboard
    send_dashboard(chat_id, user_id)


def execute_hack_defense(chat_id, user_id):
    user = players_data.get(user_id, {})
    weak_count = user.get("weak_hacker_count", 0)
    if weak_count <= 0:
        send_message(chat_id, "❌ هکر ضعیف برای حالت تدافعی ندارید!")
        return
    players_data[user_id]["weak_hacker_count"] = weak_count - 1
    if "defense_hackers" not in hack_cooldown:
        hack_cooldown["defense_hackers"] = {}
    hack_cooldown["defense_hackers"][user_id] = time.time() + 3600
    db.save_hack_cooldown(user_id, "defense_hackers", hack_cooldown["defense_hackers"][user_id])
    send_message(chat_id, f"✅ **حالت تدافعی فعال شد!**\n🛡 هکرهای شما به مدت 1 ساعت از کشور محافظت می‌کنند.\n📊 در این مدت حملات هکری به شما 50% شانس کمتری دارند.")
    db.save_player(user_id, players_data[user_id])
    # 🔄 lazy import برای جلوگیری از حلقه import
    from .dashboard import send_dashboard
    send_dashboard(chat_id, user_id)


def attack_assassination_menu(chat_id, user_id):
    if user_id not in assassination_info or not assassination_info[user_id]:
        send_message(chat_id, "❌ **شما هیچ کد امنیتی از کابینه دشمنان ندارید!**\n\nابتدا با هکرهای متوسط یا قوی، کدهای کابینه را به دست آورید.")
        return
    targets_info = {}
    for key, info in assassination_info[user_id].items():
        target_id = info["target_id"]
        if target_id not in targets_info:
            targets_info[target_id] = []
        targets_info[target_id].append(info)
    if not targets_info:
        send_message(chat_id, "❌ **هیچ کد امنیتی برای ترور یافت نشد!**")
        return
    text = f"🗡️ **حمله ترور**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"🔑 کدهای امنیتی به دست آمده:\n\n"
    keyboard = []
    for target_id, members in targets_info.items():
        target_name = players_data.get(target_id, {}).get("player_name", "نامشخص")
        text += f"🎯 {target_name}:\n"
        for member in members:
            text += f"   {member['icon']} {member['position_name']}: `{member['code']}`\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        keyboard.append([{"text": f"🗡️ ترور در {target_name}", "callback_data": f"assassinate_target_{target_id}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_menu"}])
    send_message(chat_id, text, {"inline_keyboard": keyboard})


def select_assassination_member(chat_id, user_id, target_id):
    if user_id not in assassination_info:
        send_message(chat_id, "❌ اطلاعاتی ندارید!")
        return
    available_members = []
    for key, info in assassination_info[user_id].items():
        if info["target_id"] == target_id:
            available_members.append(info)
    if not available_members:
        send_message(chat_id, "❌ شما کدهای امنیتی این کشور را ندارید!")
        return
    text = f"🗡️ **انتخاب هدف برای ترور**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"🎯 کشور: {players_data.get(target_id, {}).get('player_name', 'نامشخص')}\n\n"
    text += f"🔑 **کد امنیتی مقام مورد نظر را وارد کنید:**\n\n"
    for member in available_members:
        text += f"{member['icon']} {member['position_name']}: کد `{member['code']}`\n"
    text += f"\n━━━━━━━━━━━━━━━━━━\n📝 لطفاً کد 6 رقمی را وارد کنید:"
    waiting_for_assassination_code[user_id] = {"target_id": target_id, "members": available_members}
    send_message(chat_id, text)


def process_assassination_code(chat_id, user_id, entered_code):
    if user_id not in waiting_for_assassination_code:
        send_message(chat_id, "❌ درخواست نامعتبر!")
        return
    data = waiting_for_assassination_code.pop(user_id)
    target_id = data["target_id"]
    members = data["members"]
    target_member = None
    for member in members:
        if member["code"] == entered_code:
            target_member = member
            break
    if not target_member:
        send_message(chat_id, "❌ **کد نامعتبر است!**\nلطفاً کد صحیح را وارد کنید.")
        return
    if "used_codes" not in assassination_cooldown:
        assassination_cooldown["used_codes"] = {}
    if entered_code in assassination_cooldown["used_codes"]:
        send_message(chat_id, "❌ **این کد قبلاً استفاده شده است!**")
        return
    waiting_for_assassination_method[user_id] = {
        "target_id": target_id,
        "member_key": target_member["member_key"],
        "code": entered_code,
        "member_info": target_member
    }
    show_assassination_methods(chat_id, user_id, target_id, target_member)


def show_assassination_methods(chat_id, user_id, target_id, member_info):
    user = players_data.get(user_id, {})
    methods = []
    drone_count = get_user_drone_count(user_id)
    if drone_count > 0:
        methods.append(("🛸 پهباد", "drone", drone_count, 60))
    fighter_count = get_user_fighter_count(user_id)
    if fighter_count > 0:
        methods.append(("✈️ جنگنده", "fighter", fighter_count, 75))
    commando_count = user.get("commando_ground_count", 0)
    if commando_count > 0:
        methods.append(("🥷 کماندو", "commando", commando_count, 50))
    if not methods:
        send_message(chat_id, "❌ **شما تجهیزات برای ترور ندارید!**\n\nلطفاً پهباد، جنگنده یا کماندو بخرید.")
        return
    text = f"🗡️ **انتخاب روش ترور**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"🎯 هدف: {players_data.get(target_id, {}).get('player_name', 'نامشخص')}\n"
    text += f"{member_info['icon']} مقام: {member_info['position_name']}\n"
    text += f"🔑 کد: `{member_info['code']}`\n━━━━━━━━━━━━━━━━━━\n\n"
    text += f"روش ترور را انتخاب کنید:\n\n"
    keyboard = []
    for name, method, count, success in methods:
        text += f"{name}: {count} عدد موجود | شانس موفقیت: {success}%\n"
        keyboard.append([{"text": f"{name} (شانس {success}%)", "callback_data": f"assassinate_method_{method}_{target_id}_{member_info['member_key']}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "attack_assassination"}])
    send_message(chat_id, text, {"inline_keyboard": keyboard})


def execute_assassination(chat_id, user_id, method, target_id, member_key):
    # 🔄 lazy import برای جلوگیری از حلقه import
    from .attack import reduce_user_weapon
    from .dashboard import send_dashboard

    user = players_data.get(user_id, {})
    target = players_data.get(target_id, {})
    found_code = None
    stored_info = None
    for key, info in assassination_info.get(user_id, {}).items():
        if info["target_id"] == target_id and info["member_key"] == member_key:
            found_code = info["code"]
            stored_info = info
            break
    if not found_code:
        send_message(chat_id, "❌ شما کد این مقام را ندارید!")
        return
    if method == "drone":
        count = get_user_drone_count(user_id)
        if count <= 0:
            send_message(chat_id, "❌ پهباد ندارید!")
            return
        success_rate = 60
        cost_count = 1
        equipment_name = "پهباد"
    elif method == "fighter":
        count = get_user_fighter_count(user_id)
        if count <= 0:
            send_message(chat_id, "❌ جنگنده ندارید!")
            return
        success_rate = 75
        cost_count = 1
        equipment_name = "جنگنده"
    elif method == "commando":
        count = user.get("commando_ground_count", 0)
        if count <= 0:
            send_message(chat_id, "❌ کماندو ندارید!")
            return
        success_rate = 50
        cost_count = 1
        equipment_name = "کماندو"
    else:
        send_message(chat_id, "❌ روش نامعتبر!")
        return
    success = random.randint(1, 100) <= success_rate
    if method == "drone":
        reduce_user_weapon(user_id, "drone", cost_count)
    elif method == "fighter":
        reduce_user_weapon(user_id, "fighter", cost_count)
    elif method == "commando":
        current = user.get("commando_ground_count", 0)
        players_data[user_id]["commando_ground_count"] = current - cost_count
        new_attack = 0
        for key in GROUND_FORCES.keys():
            count_item = players_data[user_id].get(f"{key}_ground_count", 0)
            power = GROUND_FORCES.get(key, {}).get("power", 0)
            new_attack += count_item * power
        players_data[user_id]["attack_power"] = new_attack
    damage_rates = {
        "leader": 25,
        "diplomat": 20,
        "defense": 20,
        "intelligence": 18,
        "economy": 10
    }
    damage_percent = damage_rates.get(member_key, 10)
    if success:
        old_defense = target.get("defense", 5000)
        reduction = int(old_defense * damage_percent / 100)
        new_defense = max(0, old_defense - reduction)
        players_data[target_id]["defense"] = new_defense
        for key in list(assassination_info[user_id].keys()):
            if assassination_info[user_id][key]["target_id"] == target_id and assassination_info[user_id][key]["member_key"] == member_key:
                del assassination_info[user_id][key]
                db.save_assassination_info(user_id, target_id, member_key, {})
                break
        assassination_cooldown["used_codes"][found_code] = time.time() + 86400
        db.save_assassination_cooldown(found_code, assassination_cooldown["used_codes"][found_code])
        if target_id in cabinet_codes and member_key in cabinet_codes[target_id]:
            del cabinet_codes[target_id][member_key]
            db.delete_cabinet_code(target_id, member_key)
        text = f"✅ **ترور موفق!**\n━━━━━━━━━━━━━━━━━━\n"
        text += f"🗡️ روش: {equipment_name}\n"
        text += f"🎯 هدف: {target.get('player_name', 'نامشخص')}\n"
        text += f"{stored_info['icon']} مقام ترور شده: {stored_info['position_name']}\n"
        text += f"🔑 کد استفاده شده: `{found_code}`\n"
        text += f"📉 کاهش استقامت: {damage_percent}% ({reduction:,} واحد)\n"
        text += f"🛡 استقامت باقیمانده هدف: {new_defense:,}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"💀 عملیات با موفقیت انجام شد!"
        send_message(chat_id, text)
        send_message(int(target_id),
            f"💀 **ترور!**\n━━━━━━━━━━━━━━━━━━\n"
            f"🗡️ {stored_info['position_name']} کشور شما ترور شد!\n"
            f"🔑 کد امنیتی `{found_code}` استفاده شد!\n"
            f"📉 استقامت کشور {damage_percent}% کاهش یافت!\n"
            f"🛡 استقامت فعلی: {new_defense:,}\n\n"
            f"⚠️ هشدار امنیتی! باید کدهای باقیمانده را تغییر دهید.")
        send_to_group(f"💀 **اخبار فوری**\n━━━━━━━━━━━━━━━━━━\n🗡️ {stored_info['position_name']} کشور {target.get('country', 'نامشخص')} ترور شد!\n🎯 توسط: {user.get('player_name', 'نامشخص')}")
    else:
        text = f"❌ **عملیات ترور ناموفق!**\n━━━━━━━━━━━━━━━━━━\n"
        text += f"🗡️ روش: {equipment_name}\n"
        text += f"🎯 هدف: {target.get('player_name', 'نامشخص')}\n"
        text += f"{stored_info['icon']} مقام هدف: {stored_info['position_name']}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"💀 تیم ترور شناسایی شد و {equipment_name} شما از دست رفت!\n"
        text += f"🔑 اما کد `{found_code}` همچنان معتبر است و می‌توانید دوباره تلاش کنید."
        send_message(chat_id, text)
        send_message(int(target_id),
            f"⚠️ **تلاش برای ترور نافرجام!**\n━━━━━━━━━━━━━━━━━━\n"
            f"🗡️ تلاش شد {stored_info['position_name']} شما ترور شود!\n"
            f"🔑 کد `{found_code}` استفاده شد اما عملیات ناموفق بود.\n"
            f"⚠️ برای امنیت بیشتر، کدهای خود را تغییر دهید.")
    db.save_player(user_id, players_data[user_id])
    db.save_player(target_id, players_data[target_id])
    send_dashboard(chat_id, user_id)