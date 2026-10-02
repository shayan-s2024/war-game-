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
from .helpers import generate_union_id, is_admin, send_message, send_to_group, show_screen
from .state import base_costs, bases_data, country_base_count, db, free_countries_with_bases, players_data, used_countries, waiting_for_base_permission
from .static_data import CONTINENT_NAMES, COUNTRIES_LIST

# ==================== ماژول bases ====================


# ==================== سیستم پایگاه ====================
def send_build_base_menu(chat_id, user_id):
    base_price = 20000
    keyboard = {
        "inline_keyboard": [
            [{"text": "🌏 آسیا", "callback_data": "build_base_continent_asia"}],
            [{"text": "🌍 اروپا", "callback_data": "build_base_continent_europe"}],
            [{"text": "🌍 آفریقا", "callback_data": "build_base_continent_africa"}],
            [{"text": "🌎 آمریکای شمالی", "callback_data": "build_base_continent_north_america"}],
            [{"text": "🌎 آمریکای جنوبی", "callback_data": "build_base_continent_south_america"}],
            [{"text": "🌏 اقیانوسیه", "callback_data": "build_base_continent_oceania"}],
            [{"text": "🔙 بازگشت", "callback_data": "dashboard"}]
        ]
    }
    total_bases = len(bases_data)
    text = f"🏗️ **ساخت پایگاه نظامی**\n━━━━━━━━━━━━━━━━━━\n💰 هزینه: {base_price:,} سکه\n🕐 زمان ساخت: 30 دقیقه\n🏗️ پایگاه‌های ساخته شده: {total_bases}\n\n📍 ابتدا قاره مورد نظر را انتخاب کنید:"
    show_screen(chat_id, text, keyboard)



def process_build_base_continent(chat_id, user_id, continent_key):
    continent_data = COUNTRIES_LIST.get(continent_key, {})
    countries_dict = continent_data.get("countries", {})
    countries = list(countries_dict.keys())
    if not countries:
        send_message(chat_id, f"❌ قاره {CONTINENT_NAMES.get(continent_key, 'نامشخص')} کشوری ندارد!")
        return
    keyboard = []
    row = []
    for country_name in countries:
        has_base = any(base.get("country") == country_name for base in bases_data.values())
        is_taken = country_name in used_countries
        country_emoji = countries_dict.get(country_name, {}).get("emoji", "🏳️")
        if has_base:
            display_text = f"❌ {country_emoji} {country_name}"
        elif is_taken:
            owner_id = used_countries[country_name]
            owner_name = players_data.get(owner_id, {}).get("player_name", "نامشخص")
            user_union = players_data.get(user_id, {}).get("union")
            owner_union = players_data.get(owner_id, {}).get("union")
            if user_union and user_union == owner_union:
                display_text = f"✅ {country_emoji} {country_name} (متحد)"
            else:
                display_text = f"⚠️ {country_emoji} {country_name} ({owner_name})"
        else:
            display_text = f"✅ {country_emoji} {country_name}"
        row.append({"text": display_text, "callback_data": f"build_base_country_{continent_key}_{country_name}"})
        if len(row) == 1:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    if len(keyboard) > 20:
        keyboard = keyboard[:20]
    keyboard.append([{"text": "🔙 بازگشت به قاره‌ها", "callback_data": "build_base_menu"}])
    total_countries = len(countries)
    bases_in_continent = sum(1 for base in bases_data.values() if base.get("continent") == continent_key)
    send_message(chat_id, 
        f"🏗️ **ساخت پایگاه در {CONTINENT_NAMES.get(continent_key, 'قاره')}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 آمار: {bases_in_continent}/{total_countries} پایگاه\n\n"
        f"✅ = قابل ساخت\n"
        f"⚠️ = نیاز به اتحاد با مالک\n"
        f"❌ = پایگاه وجود دارد\n\n"
        f"کشور مورد نظر را انتخاب کنید:", 
        {"inline_keyboard": keyboard})


def build_base_in_country(chat_id, user_id, continent_key, country_name):
    user = players_data.get(user_id, {})
    base_price = 20000
    
    # بررسی وجود پایگاه در کشور
    for base_id, base in bases_data.items():
        if base.get("country") == country_name:
            send_message(chat_id, f"❌ در کشور {country_name} قبلاً پایگاه وجود دارد!")
            return
    
    # اگر کشور صاحب دارد
    if country_name in used_countries:
        owner_id = used_countries[country_name]
        
        # اگر مالک خود کاربر است
        if owner_id == user_id:
            # بررسی تعداد پایگاه‌های کاربر در این کشور (حداکثر 2)
            user_bases_in_country = sum(1 for b in bases_data.values() if b.get("owner") == user_id and b.get("country") == country_name)
            if user_bases_in_country >= 2:
                send_message(chat_id, f"❌ شما نمی‌توانید بیش از ۲ پایگاه در کشور خودتان بسازید!")
                return
        else:
            # بررسی اتحاد
            user_union = user.get("union")
            owner_union = players_data.get(owner_id, {}).get("union")
            
            # اگر هم‌اتحاد هستند
            if user_union and user_union == owner_union:
                user_bases_in_country = sum(1 for b in bases_data.values() if b.get("owner") == user_id and b.get("country") == country_name)
                if user_bases_in_country >= 2:
                    send_message(chat_id, f"❌ در کشور هم‌اتحاد {country_name} بیش از ۲ پایگاه نمی‌توان ساخت!")
                    return
            else:
                # ==================== درخواست مجوز از مالک ====================
                # بررسی اینکه قبلاً درخواست فعالی وجود نداشته باشد
                if user_id in waiting_for_base_permission:
                    send_message(chat_id, "❌ شما قبلاً یک درخواست مجوز فعال دارید! لطفاً منتظر پاسخ باشید.")
                    return
                
                # ذخیره درخواست
                waiting_for_base_permission[user_id] = {
                    "country": country_name,
                    "continent": continent_key,
                    "owner_id": owner_id,
                    "timestamp": time.time()
                }
                
                # ساخت کیبورد برای مالک
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "✅ اجازه ساخت", "callback_data": f"allow_base_{user_id}_{country_name}"}],
                        [{"text": "❌ رد کردن", "callback_data": f"deny_base_{user_id}_{country_name}"}]
                    ]
                }
                
                # ارسال پیام به کاربر درخواست‌دهنده
                send_message(chat_id, f"📨 **درخواست مجوز ساخت پایگاه ارسال شد!**\n━━━━━━━━━━━━━━━━━━\n🌍 کشور: {country_name}\n👑 مالک کشور: {players_data[owner_id].get('player_name')}\n💰 هزینه ساخت: {base_price:,} سکه\n\n⏳ منتظر تایید مالک باشید...")
                
                # ارسال درخواست به مالک کشور
                send_message(int(owner_id), 
                    f"🏗️ **درخواست ساخت پایگاه**\n━━━━━━━━━━━━━━━━━━\n"
                    f"👤 کاربر درخواست‌دهنده: {user.get('player_name')}\n"
                    f"🌍 کشور: {country_name}\n"
                    f"💰 هزینه ساخت: {base_price:,} سکه\n"
                    f"🕐 زمان ساخت: 30 دقیقه\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"آیا اجازه ساخت پایگاه در کشور خود را می‌دهید؟",
                    keyboard)
                return
    
    # اگر کشور بدون صاحب است
    else:
        # بررسی حداکثر ۱۰ کشور بدون صاحب
        if len(free_countries_with_bases) >= 10 and country_name not in free_countries_with_bases:
            send_message(chat_id, f"❌ حداکثر ۱۰ کشور بدون صاحب می‌توانند پایگاه داشته باشند!\n📍 کشورهای دارای پایگاه بدون صاحب: {len(free_countries_with_bases)}/۱۰")
            return
        
        # بررسی تعداد پایگاه در کشور بدون صاحب (حداکثر 1)
        existing_bases_in_country = [b for b in bases_data.values() if b.get("country") == country_name]
        if len(existing_bases_in_country) >= 1:
            send_message(chat_id, f"❌ در کشور بدون صاحب {country_name} فقط یک پایگاه می‌توان ساخت!")
            return
    
    # بررسی موجودی کاربر
    if user.get("credit", 0) < base_price:
        send_message(chat_id, f"❌ موجودی کافی نیست! به {base_price:,} سکه نیاز دارید.")
        return
    
    # ساخت پایگاه
    base_id = generate_union_id()
    country_emoji = COUNTRIES_LIST.get(continent_key, {}).get("countries", {}).get(country_name, {}).get("emoji", "🏳️")
    
    bases_data[base_id] = {
        "owner": user_id,
        "country": country_name,
        "country_emoji": country_emoji,
        "continent": continent_key,
        "built_at": time.time(),
        "ready_at": time.time() + 1,
        "ground_troops": 0,
        "air_troops": 0,
        "max_ground": 5000,
        "max_air": 1000
    }
    
    # ذخیره هزینه پایگاه برای بازپرداخت بعدی
    base_costs[base_id] = base_price
    
    # به‌روزرسانی آمار کشور
    if country_name not in country_base_count:
        country_base_count[country_name] = 0
    country_base_count[country_name] += 1
    
    # اگر کشور بدون صاحب است، به مجموعه اضافه کن
    if country_name not in used_countries:
        free_countries_with_bases.add(country_name)
    
    players_data[user_id]["credit"] = user.get("credit", 0) - base_price
    db.save_player(user_id, players_data[user_id])
    db.save_base(base_id, bases_data[base_id])
    
    send_message(chat_id, 
        f"✅ **ساخت پایگاه در {country_emoji} {country_name} شروع شد!**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🕐 زمان اتمام: 30 دقیقه دیگر\n"
        f"💰 هزینه: {base_price:,} سکه\n"
        f"🏗️ پایگاه‌های این کشور: {country_base_count[country_name]}\n"
        f"💎 سکه باقیمانده: {players_data[user_id]['credit']:,}")




def allow_base_construction(chat_id, owner_id, requester_id, country_name):
    """تایید درخواست ساخت پایگاه توسط مالک کشور"""
    
    # بررسی اینکه درخواست معتبر باشد
    if requester_id not in waiting_for_base_permission:
        send_message(chat_id, "❌ این درخواست منقضی شده است یا وجود ندارد!")
        return
    
    request_data = waiting_for_base_permission.pop(requester_id)
    
    # بررسی صحت اطلاعات
    if request_data["country"] != country_name or request_data["owner_id"] != owner_id:
        send_message(chat_id, "❌ اطلاعات درخواست نامعتبر است!")
        return
    
    # بررسی زمان (درخواست‌های بیش از 5 دقیقه منقضی می‌شوند)
    if time.time() - request_data["timestamp"] > 300:
        send_message(chat_id, "❌ زمان درخواست به اتمام رسیده است! (بیش از 5 دقیقه)")
        send_message(int(requester_id), f"⏰ درخواست شما برای ساخت پایگاه در {country_name} منقضی شد!")
        return
    
    # دریافت اطلاعات کاربر درخواست‌دهنده
    requester = players_data.get(requester_id, {})
    base_price = 20000
    
    # بررسی مجدد موجودی کاربر
    if requester.get("credit", 0) < base_price:
        send_message(chat_id, f"❌ کاربر {requester.get('player_name')} بودجه کافی برای ساخت پایگاه ندارد!")
        send_message(int(requester_id), f"❌ بودجه کافی برای ساخت پایگاه در {country_name} ندارید! به {base_price:,} سکه نیاز دارید.")
        return
    
    # بررسی مجدد وجود پایگاه در کشور
    for base_id, base in bases_data.items():
        if base.get("country") == country_name:
            send_message(chat_id, f"❌ در کشور {country_name} قبلاً پایگاه وجود دارد!")
            send_message(int(requester_id), f"❌ در کشور {country_name} قبلاً پایگاه وجود دارد!")
            return
    
    # ساخت پایگاه
    continent_key = request_data["continent"]
    base_id = generate_union_id()
    country_emoji = COUNTRIES_LIST.get(continent_key, {}).get("countries", {}).get(country_name, {}).get("emoji", "🏳️")
    
    bases_data[base_id] = {
        "owner": requester_id,
        "country": country_name,
        "country_emoji": country_emoji,
        "continent": continent_key,
        "built_at": time.time(),
        "ready_at": time.time() + 1800,
        "ground_troops": 0,
        "air_troops": 0,
        "max_ground": 5000,
        "max_air": 1000
    }
    
    # ذخیره هزینه
    base_costs[base_id] = base_price
    
    # به‌روزرسانی آمار
    if country_name not in country_base_count:
        country_base_count[country_name] = 0
    country_base_count[country_name] += 1
    
    # کسر هزینه
    players_data[requester_id]["credit"] = requester.get("credit", 0) - base_price
    db.save_player(requester_id, players_data[requester_id])
    db.save_base(base_id, bases_data[base_id])
    
    # ارسال پیام تایید
    send_message(chat_id, f"✅ **شما به {requester.get('player_name')} اجازه ساخت پایگاه در {country_name} دادید!**")
    
    send_message(int(requester_id),
        f"✅ **مجوز ساخت پایگاه دریافت شد!**\n━━━━━━━━━━━━━━━━━━\n"
        f"🏗️ ساخت پایگاه در {country_emoji} {country_name} شروع شد!\n"
        f"💰 هزینه: {base_price:,} سکه\n"
        f"🕐 زمان اتمام: 30 دقیقه دیگر\n"
        f"👑 مالک کشور: {players_data[owner_id].get('player_name')}")
    
    # اطلاع‌رسانی در گروه
    send_to_group(f"🏗️ **ساخت پایگاه جدید**\n━━━━━━━━━━━━━━━━━━\n"
                  f"📍 کشور: {country_emoji} {country_name}\n"
                  f"👤 سازنده: {requester.get('player_name')}\n"
                  f"👑 مجوز از: {players_data[owner_id].get('player_name')}")




def deny_base_construction(chat_id, owner_id, requester_id, country_name):
    """رد درخواست ساخت پایگاه توسط مالک کشور"""
    
    if requester_id in waiting_for_base_permission:
        request_data = waiting_for_base_permission.pop(requester_id)
        
        # بررسی صحت اطلاعات
        if request_data.get("owner_id") != owner_id or request_data.get("country") != country_name:
            send_message(chat_id, "❌ اطلاعات درخواست نامعتبر است!")
            return
        
        requester_name = players_data.get(requester_id, {}).get("player_name", "نامشخص")
        send_message(chat_id, f"❌ درخواست ساخت پایگاه {requester_name} در {country_name} رد شد!")
        send_message(int(requester_id), f"❌ درخواست ساخت پایگاه شما در {country_name} توسط مالک کشور رد شد!")
    else:
        send_message(chat_id, "❌ درخواست یافت نشد!")







def send_bases_menu(chat_id, user_id):
    user_bases = []
    for base_id, base in bases_data.items():
        if base.get("owner") == user_id:
            user_bases.append(base)
    if not user_bases:
        keyboard = {
            "inline_keyboard": [
                [{"text": "➕ ساخت پایگاه جدید", "callback_data": "build_base_menu"}],
                [{"text": "🔙 بازگشت", "callback_data": "dashboard"}]
            ]
        }
        show_screen(chat_id, "🏗️ **شما هیچ پایگاهی ندارید!**\n\nاز دکمه زیر برای ساخت پایگاه استفاده کنید:", keyboard)
        return
    total_bases = len(user_bases)
    ready_bases = sum(1 for b in user_bases if b.get("ready_at", 0) <= time.time())
    building_bases = total_bases - ready_bases
    text = f"🏗️ **پایگاه‌های شما**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 آمار: {ready_bases} آماده | {building_bases} در حال ساخت\n━━━━━━━━━━━━━━━━━━\n"
    for base in user_bases:
        ready_time = base.get("ready_at", 0)
        if ready_time > time.time():
            remaining = int((ready_time - time.time()) / 60)
            status = f"🟡 در حال ساخت ({remaining} دقیقه)"
        else:
            status = "✅ آماده"
        country_emoji = base.get("country_emoji", "🏳️")
        text += f"\n{country_emoji} **{base.get('country')}** - {status}\n"
        text += f"   🪖 {base.get('ground_troops', 0)}/{base.get('max_ground', 5000)} | ✈️ {base.get('air_troops', 0)}/{base.get('max_air', 1000)}\n━━━━━━━━━━━━━━━━━━"
    keyboard = {
        "inline_keyboard": [
            [{"text": "➕ ساخت پایگاه جدید", "callback_data": "build_base_menu"}],
            [{"text": "🔄 بروزرسانی", "callback_data": "bases_menu"}],
            [{"text": "🔙 بازگشت", "callback_data": "dashboard"}]
        ]
    }
    show_screen(chat_id, text, keyboard)



def debug_bases(chat_id, user_id):
    if not is_admin(user_id):
        send_message(chat_id, "⛔ فقط ادمین!")
        return
    if not bases_data:
        send_message(chat_id, "📋 **هیچ پایگاهی در دیتابیس وجود ندارد!**")
        return
    text = "🏗️ **لیست همه پایگاه‌ها:**\n━━━━━━━━━━━━━━━━━━\n"
    for base_id, base in bases_data.items():
        text += f"\n🆔 {base_id}\n📍 کشور: {base.get('country')}\n👤 مالک: {base.get('owner')}\n🕐 ساخته شده: {time.ctime(base.get('built_at', 0))}\n━━━━━━━━━━━━━━━━━━"
    send_message(chat_id, text)


def clear_all_bases(chat_id, user_id):
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    bases_data.clear()
    db.delete_all_bases()
    send_message(chat_id, "✅ همه پایگاه‌ها با موفقیت پاک شدند!")
