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
from .helpers import is_sanctioned, send_message, show_screen
from .state import db, players_data, waiting_for_buy_count
from .static_data import AIRCRAFT_CARRIERS, AIR_DEFENSES, ARTILLERY, BOMBS, BUILDINGS, DRONES, ECONOMIC_ITEMS, FIGHTERS, GROUND_FORCES, HACKERS, HELICOPTERS, MINES, MISSILES, NAVAL_VESSELS, PILOTS, SHOP_PRICE_MULTIPLIER, SUBMARINES, TANKS

# ==================== ماژول shop ====================


# ==================== سیستم خرید ====================
def ask_for_buy_count(chat_id, user_id, category, item_key, item_name, price, profit=None, power=None, defense=None, count_per_unit=1):
    # دیباگ برای اطمینان از اجرا
    
    sanctioned, penalty, end_date = is_sanctioned(user_id)
    price = int(price * SHOP_PRICE_MULTIPLIER)
    original_price = price
    if sanctioned:
        price = int(price * (1 + penalty))
        penalty_percent = int(penalty * 100)
    
    # ذخیره اطلاعات خرید - این خط CRITICAL است
    waiting_for_buy_count[user_id] = {
        "category": category, 
        "item_key": item_key, 
        "item_name": item_name,
        "price": price, 
        "original_price": original_price, 
        "profit": profit,
        "power": power, 
        "defense": defense, 
        "count_per_unit": count_per_unit,
        "sanctioned": sanctioned, 
        "penalty": penalty
    }
    
    
    # متن پیام
    text = f"🔢 **تعداد {item_name} را وارد کن:**\n"
    if sanctioned:
        text += f"⚠️ **کشور شما تحریم است!**\n"
        text += f"💰 قیمت اصلی: {original_price:,} سکه\n"
        text += f"💸 قیمت با جریمه {penalty_percent}%: {price:,} سکه\n"
        remaining_days = int((end_date - time.time()) / 86400) + 1
        text += f"📅 زمان باقیمانده تحریم: {remaining_days} روز\n━━━━━━━━━━━━━━━━━━\n"
    else:
        text += f"💰 قیمت هر واحد: {price:,} سکه\n"
    if profit:
        text += f"📈 سود روزانه هر واحد: +{profit:,} سکه\n"
    if power:
        text += f"💥 قدرت تخریب هر واحد: +{power}\n"
    if defense:
        text += f"🛡 استقامت هر واحد: +{defense}\n"
    text += f"\n📌 فقط عدد وارد کن:\n\n(مثال: 10, 50, 100)"
    
    show_screen(chat_id, text)


def process_buy_item(chat_id, user_id, category, item_key, count):
    """پردازش خرید با بررسی کامل موجودی"""
    # 🔄 lazy import برای جلوگیری از حلقه import
    from .dashboard import send_dashboard

    # 🔒 کاربر بدون ثبت‌نام (حتی ادمین) نمی‌تواند خرید کند و رکورد قلابی ساخته نمی‌شود
    if not players_data.get(user_id, {}).get("player_name"):
        send_message(chat_id, "🔒 **ابتدا باید در بازی ثبت‌نام کنید!**\nدستور /start را بفرستید.")
        return
    # 🚫 سقف تجهیزات: بیشتر از سقف تعیین‌شده نمی‌توان بخری
    _CAT_MAP = {
        "defense": (AIR_DEFENSES, "air_defense_count"), "tank": (TANKS, "tank_count"),
        "fighter": (FIGHTERS, "fighter_count"), "helicopter": (HELICOPTERS, "helicopter_count"),
        "missile": (MISSILES, "missile_count"), "drone": (DRONES, "drone_count"),
        "naval": (NAVAL_VESSELS, "naval_count"), "submarine": (SUBMARINES, "submarine_count"),
        "carrier": (AIRCRAFT_CARRIERS, "carrier_count"), "ground": (GROUND_FORCES, "ground_count"),
        "artillery": (ARTILLERY, "artillery_count"), "hacker": (HACKERS, "hacker_count"),
        "bomb": (BOMBS, "bomb_count"), "mine": (MINES, "count"),
    }
    _cat = _CAT_MAP.get(category)
    if _cat:
        _item = _cat[0].get(item_key, {})
        _cap = _item.get("cap", _item.get("max"))
        if _cap is not None:
            _current = players_data.get(user_id, {}).get(f"{item_key}_{_cat[1]}", 0)
            _add = count * _item.get("count", 1)
            if _current + _add > _cap:
                send_message(chat_id, f"🚫 **سقف تجهیزات!** حداکثر {_cap:,} عدد از {_item.get('name')} می‌توانی داشته باشی (فعلاً {_current:,} داری).")
                return
    
    
    # دریافت اطلاعات کاربر
    user = players_data.get(user_id, {})
    if not isinstance(user, dict):
        user = {}
        players_data[user_id] = user
    
    # دریافت موجودی فعلی کاربر
    current_credit = user.get("credit", 0)
    
    # بررسی تحریم
    sanctioned, penalty, end_date = is_sanctioned(user_id)
    
    # ==================== محدودیت 100 تایی برای تجهیزات اقتصادی ====================
    MAX_ECONOMIC_ITEMS = 100
    
    # تابع کمکی برای نمایش پیام موجودی ناکافی
    def show_insufficient_balance(chat_id, current_credit, total_price):
        shortage = total_price - current_credit
        send_message(chat_id, f"❌ **موجودی کافی نیست!**\n━━━━━━━━━━━━━━━━━━\n💰 موجودی شما: {current_credit:,} سکه\n💰 قیمت کل: {total_price:,} سکه\n💸 کمبود: {shortage:,} سکه\n━━━━━━━━━━━━━━━━━━\n💡 ابتدا سکه بیشتری بدست آورید!")
    
    # ==================== پردازش بر اساس دسته ====================
    
    # 1. معادن
    if category == "mine" and item_key in MINES:
        item = MINES[item_key]
        price_per_unit = item["price"]
        profit_per_unit = item["daily_profit"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_profit = profit_per_unit * count
        item_name = item["name"]
        current = user.get(f"{item_key}_count", 0)
        
        # بررسی موجودی
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        # محدودیت حداکثر 100 عدد
        if current + count > MAX_ECONOMIC_ITEMS:
            send_message(chat_id, f"❌ شما نمی‌توانید بیش از {MAX_ECONOMIC_ITEMS} عدد از {item_name} داشته باشید!\n📊 موجودی فعلی: {current}/{MAX_ECONOMIC_ITEMS}")
            return
        
        # انجام خرید
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_count"] = current + count
        players_data[user_id]["daily_profit"] = user.get("daily_profit", 0) + total_profit
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n📈 سود روزانه +{total_profit:,} سکه\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 2. تجهیزات اقتصادی
    elif category == "economic" and item_key in ECONOMIC_ITEMS:
        item = ECONOMIC_ITEMS[item_key]
        price_per_unit = item["price"]
        profit_per_unit = item["profit"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_profit = profit_per_unit * count
        item_name = item["name"]
        current = user.get(f"{item_key}_count", 0)
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        if current + count > MAX_ECONOMIC_ITEMS:
            send_message(chat_id, f"❌ شما نمی‌توانید بیش از {MAX_ECONOMIC_ITEMS} عدد از {item_name} داشته باشید!\n📊 موجودی فعلی: {current}/{MAX_ECONOMIC_ITEMS}")
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_count"] = current + count
        players_data[user_id]["daily_profit"] = user.get("daily_profit", 0) + total_profit
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n📈 سود روزانه +{total_profit:,} سکه\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 3. پدافندها
    elif category == "defense" and item_key in AIR_DEFENSES:
        item = AIR_DEFENSES[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_power = item["power"] * count * item["count"]
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_air_defense_count"] = user.get(f"{item_key}_air_defense_count", 0) + (count * item["count"])
        players_data[user_id]["defense"] = user.get("defense", 5000) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count * item['count']} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n🛡 استقامت +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 4. تانک‌ها
    elif category == "tank" and item_key in TANKS:
        item = TANKS[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_power = item["power"] * count * item["count"]
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_tank_count"] = user.get(f"{item_key}_tank_count", 0) + (count * item["count"])
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count * item['count']} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 5. جنگنده‌ها
    elif category == "fighter" and item_key in FIGHTERS:
        item = FIGHTERS[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_power = item["power"] * count * item["count"]
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_fighter_count"] = user.get(f"{item_key}_fighter_count", 0) + (count * item["count"])
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count * item['count']} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 6. هلیکوپترها
    elif category == "helicopter" and item_key in HELICOPTERS:
        item = HELICOPTERS[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_power = item["power"] * count * item["count"]
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_helicopter_count"] = user.get(f"{item_key}_helicopter_count", 0) + (count * item["count"])
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count * item['count']} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 7. موشک‌ها
    elif category == "missile" and item_key in MISSILES:
        item = MISSILES[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_power = item["power"] * count * item["count"]
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_missile_count"] = user.get(f"{item_key}_missile_count", 0) + (count * item["count"])
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count * item['count']} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 8. ناوها
    elif category == "naval" and item_key in NAVAL_VESSELS:
        item = NAVAL_VESSELS[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_power = item["power"] * count * item["count"]
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_naval_count"] = user.get(f"{item_key}_naval_count", 0) + (count * item["count"])
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count * item['count']} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 9. زیردریایی‌ها
    elif category == "submarine" and item_key in SUBMARINES:
        item = SUBMARINES[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_power = item["power"] * count * item["count"]
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_submarine_count"] = user.get(f"{item_key}_submarine_count", 0) + (count * item["count"])
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count * item['count']} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 10. هکرها
    elif category == "hacker" and item_key in HACKERS:
        item = HACKERS[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_count = count * item["count"]
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_hacker_count"] = user.get(f"{item_key}_hacker_count", 0) + total_count
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{total_count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💪 توانایی: {item['abilities']}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 11. بمب‌ها
    elif category == "bomb" and item_key in BOMBS:
        item = BOMBS[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_count = count * item["count"]
        total_power = item["power"] * total_count
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_bomb_count"] = user.get(f"{item_key}_bomb_count", 0) + total_count
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{total_count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 12. خلبان‌ها
    elif category == "pilot" and item_key in PILOTS:
        item = PILOTS[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_count = count * item.get("count", 1)
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        pilot_key = f"{item_key}_pilot_count"
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][pilot_key] = user.get(pilot_key, 0) + total_count
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{total_count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if item_key == "helicopter":
            msg += f"\n🚁 این خلبان فقط برای هلیکوپترها قابل استفاده است!"
        elif item_key == "normal":
            msg += f"\n🟠 این خلبان برای جنگنده‌های اف4، اف18، جی10، جی16، اف16، سوخو27 است!"
        elif item_key == "strong":
            msg += f"\n🔴 این خلبان برای جنگنده‌های یوروفایتر، جی17، گلدن ایگل، جی20، سوخو35 است!"
        elif item_key == "professional":
            msg += f"\n⭐ این خلبان برای جنگنده‌های سوخو57، اف35، سوخو75، اف22 است!"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 13. پهپادها
    elif category == "drone" and item_key in DRONES:
        item = DRONES[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_count = count * item["count"]
        total_power = item["power"] * total_count
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_drone_count"] = user.get(f"{item_key}_drone_count", 0) + total_count
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{total_count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 14. توپخانه
    elif category == "artillery" and item_key in ARTILLERY:
        item = ARTILLERY[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_count = count * item["count"]
        total_power = item["power"] * total_count
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_artillery_count"] = user.get(f"{item_key}_artillery_count", 0) + total_count
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{total_count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 15. نیروی زمینی
    elif category == "ground" and item_key in GROUND_FORCES:
        item = GROUND_FORCES[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_count = count * item["count"]
        total_power = item["power"] * total_count
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_ground_count"] = user.get(f"{item_key}_ground_count", 0) + total_count
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) + total_power
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{total_count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💥 قدرت تخریب +{total_power:,}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 16. ناو هواپیمابر
    elif category == "carrier" and item_key in AIRCRAFT_CARRIERS:
        item = AIRCRAFT_CARRIERS[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        total_count = count * item["count"]
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_carrier_count"] = user.get(f"{item_key}_carrier_count", 0) + total_count
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{total_count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    # 17. ساختمان‌ها
    elif category == "building" and item_key in BUILDINGS:
        item = BUILDINGS[item_key]
        price_per_unit = item["price"]
        
        if sanctioned:
            price_per_unit = int(price_per_unit * (1 + penalty))
        
        total_price = price_per_unit * count
        item_name = item["name"]
        
        if current_credit < total_price:
            show_insufficient_balance(chat_id, current_credit, total_price)
            return
        
        players_data[user_id]["credit"] = current_credit - total_price
        players_data[user_id][f"{item_key}_count"] = user.get(f"{item_key}_count", 0) + count
        db.save_player(user_id, players_data[user_id])
        
        msg = f"✅ **{count} عدد {item_name} خریداری شد!**\n💰 هزینه: {total_price:,} سکه\n📝 {item['description']}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}"
        if sanctioned:
            msg += f"\n⚠️ قیمت با احتساب جریمه {int(penalty*100)}% تحریم محاسبه شده است!"
        send_message(chat_id, msg)
        send_dashboard(chat_id, user_id)
    
    else:
        send_message(chat_id, "❌ دسته بندی نامعتبر!")
    
    # پاک کردن اطلاعات خرید از حافظه (اگه وجود داشته باشه)
    if user_id in waiting_for_buy_count:
        del waiting_for_buy_count[user_id]


# ==================== فروشگاه ====================
def send_shop_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "💰 اقتصادی (ساختن کسب و کار)", "callback_data": "shop_economic"}],
            [{"text": "🛡 دفاعی (تقویت استقامت)", "callback_data": "shop_defense"}],
            [{"text": "⚔️ تهاجمی (افزایش قدرت)", "callback_data": "shop_offensive"}],
            [{"text": "🏗️ ساختمان‌ها", "callback_data": "shop_building"}],
            [{"text": "🔙 بازگشت", "callback_data": "dashboard"}]
        ]
    }
    show_screen(chat_id, "🛒 **فروشگاه سکه**\n\nدسته مورد نظر را انتخاب کنید:", keyboard)


def send_shop_economic(chat_id):
    rows = []
    for key, item in MINES.items():
        rows.append([{"text": f"{item['icon']} {item['name']} | {item['price']:,} سکه | سود روزانه: {item['daily_profit']:,}",
                      "callback_data": f"buy_mine_{key}"}])
    for key, item in ECONOMIC_ITEMS.items():
        rows.append([{"text": f"{item['name']} | {item['price']:,} سکه | سود روزانه: {item['profit']:,}",
                      "callback_data": f"buy_economic_{key}"}])
    rows.append([{"text": "🔙 بازگشت", "callback_data": "shop_menu"}])
    show_screen(chat_id,
        "💰 **فروشگاه اقتصادی**\n━━━━━━━━━━━━━━━━━━\n"
        "⚠️ حداکثر ۱۰۰ عدد از هر کالا | سودها هر شب ساعت ۲۲ واریز می‌شود\n━━━━━━━━━━━━━━━━━━\nکالا را انتخاب کنید:",
        {"inline_keyboard": rows})


def send_shop_defense(chat_id):
    rows = []
    for key, item in AIR_DEFENSES.items():
        rows.append([{"text": f"{item['icon']} {item['name']} | {item['price']:,} سکه | {item['count']} عدد | قدرت: {item['power']}",
                      "callback_data": f"buy_defense_{key}"}])
    rows.append([{"text": "🔙 بازگشت", "callback_data": "shop_menu"}])
    show_screen(chat_id,
        "🛡️ **فروشگاه دفاعی**\n━━━━━━━━━━━━━━━━━━\n"
        "هر خرید به اندازه (تعداد × قدرت) به استقامت شما اضافه می‌کند.\n"
        "پدافندها در برابر حمله‌های هوایی می‌جنگند و رهگیری هم انجام می‌دهند.\n━━━━━━━━━━━━━━━━━━\nپدافند را انتخاب کنید:",
        {"inline_keyboard": rows})


def send_shop_offensive(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "👨‍💻 هکرها", "callback_data": "shop_hacker"}],
            [{"text": "💣 بمب‌ها", "callback_data": "shop_bomb"}],
            [{"text": "👨‍✈️ خلبان‌ها", "callback_data": "shop_pilot"}],
            [{"text": "🚀 موشک‌ها", "callback_data": "shop_missile"}],
            [{"text": "🛸 پهبادها", "callback_data": "shop_drone"}],
            [{"text": "🚁 هلیکوپترها", "callback_data": "shop_helicopter"}],
            [{"text": "🛩️ جنگنده‌ها", "callback_data": "shop_fighter"}],
            [{"text": "⚙️ تانک‌ها", "callback_data": "shop_tank"}],
            [{"text": "⚔️ توپخانه", "callback_data": "shop_artillery"}],
            [{"text": "🚢 نیروی دریایی", "callback_data": "shop_navy"}],
            [{"text": "🥷🏻 نیروی زمینی", "callback_data": "shop_ground"}],
            [{"text": "🔙 بازگشت", "callback_data": "shop_menu"}]
        ]
    }
    show_screen(chat_id, "⚔️ **فروشگاه تهاجمی**\n\nدسته مورد نظر را انتخاب کنید:", keyboard)


def send_shop_building(chat_id):
    keyboard = []
    for key, item in BUILDINGS.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه", "callback_data": f"buy_building_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_menu"}])
    show_screen(chat_id, "🏗️ **ساختمان‌ها**\n\n🏥 بیمارستان: درمان سربازان زخمی\n🛕 پادگان: آموزش و ارتقا سربازان\n🚉 مترو: حمل و نقل داخلی\n🛬 فرودگاه: حمل و نقل خارجی\n⛴️ اسکله: حمل تجهیزات دریایی", {"inline_keyboard": keyboard})


def send_shop_hacker(chat_id):
    keyboard = []
    for key, item in HACKERS.items():
        abilities_text = ""
        if "defense_only" in item["abilities"]:
            abilities_text = "فقط دفاعی"
        elif "info_attack" in item["abilities"] and "defense_hack" in item["abilities"] and "missile_hack" in item["abilities"]:
            abilities_text = "همه قابلیت‌ها"
        elif "info_attack" in item["abilities"]:
            abilities_text = "اطلاعاتی + پدافند"
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد | {abilities_text}", "callback_data": f"buy_hacker_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}])
    show_screen(chat_id, "💻 **هکرها**\n\n🟡 ضعیف: فقط دفاعی\n🟠 متوسط: اطلاعاتی + از کار انداختن پدافند\n🔴 قوی: همه قابلیت‌ها", {"inline_keyboard": keyboard})


def send_shop_bomb(chat_id):
    keyboard = []
    for key, item in BOMBS.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_bomb_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}])
    show_screen(chat_id, "💣 **بمب‌ها**", {"inline_keyboard": keyboard})


def send_shop_pilot(chat_id):
    ranges = {"helicopter": "برای بالگردها", "normal": "اف4 تا سوخو27",
              "strong": "یوروفایتر تا سوخو35", "professional": "سوخو57 تا اف22"}
    rows = []
    for key, item in PILOTS.items():
        rows.append([{"text": f"{item['icon']} {item['name']} | {item['price']:,} سکه ({item['count']} خلبان) | {ranges[key]}",
                      "callback_data": f"buy_pilot_{key}"}])
    rows.append([{"text": "🔙 بازگشت", "callback_data": "shop_menu"}])
    show_screen(chat_id,
        "👨‍✈️ **فروشگاه خلبان‌ها**\n━━━━━━━━━━━━━━━━━━\n"
        "جنگنده و بالگرد بدون خلبان پرواز نمی‌کند! هر خلبان مخصوص یک دسته هواپیماست.\n━━━━━━━━━━━━━━━━━━\nخلبان را انتخاب کنید:",
        {"inline_keyboard": rows})


def send_shop_missile(chat_id):
    keyboard = []
    for key, item in MISSILES.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_missile_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}])
    show_screen(chat_id, "🚀 **موشک‌ها**\n\nبرد: تا انتهای قاره", {"inline_keyboard": keyboard})


def send_shop_drone(chat_id):
    keyboard = []
    for key, item in DRONES.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_drone_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}])
    show_screen(chat_id, "🛸 **پهبادها**", {"inline_keyboard": keyboard})


def send_shop_helicopter(chat_id):
    keyboard = []
    for key, item in HELICOPTERS.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_helicopter_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}])
    show_screen(chat_id, "🚁 **هلیکوپترها**", {"inline_keyboard": keyboard})


def send_shop_fighter(chat_id):
    keyboard = []
    for key, item in FIGHTERS.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_fighter_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}])
    show_screen(chat_id, "🛩️ **جنگنده‌ها**", {"inline_keyboard": keyboard})


def send_shop_tank(chat_id):
    keyboard = []
    for key, item in TANKS.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_tank_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}])
    show_screen(chat_id, "⚙️ **تانک‌ها**", {"inline_keyboard": keyboard})


def send_shop_artillery(chat_id):
    keyboard = []
    for key, item in ARTILLERY.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_artillery_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}])
    show_screen(chat_id, "⚔️ **توپخانه**", {"inline_keyboard": keyboard})


def send_shop_ground(chat_id):
    keyboard = []
    for key, item in GROUND_FORCES.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_ground_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}])
    show_screen(chat_id, "🥷🏻 **نیروی زمینی**", {"inline_keyboard": keyboard})


def send_shop_navy(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "🛳️ وسایل نقلیه دریایی", "callback_data": "shop_naval_vehicles"}],
            [{"text": "🐋 زیردریایی‌ها", "callback_data": "shop_submarine"}],
            [{"text": "🚢 ناوهای هواپیمابر", "callback_data": "shop_carrier"}],
            [{"text": "🔙 بازگشت", "callback_data": "shop_offensive"}]
        ]
    }
    show_screen(chat_id, "🚢 **نیروی دریایی**", keyboard)


def send_shop_naval_vehicles(chat_id):
    keyboard = []
    for key, item in NAVAL_VESSELS.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_naval_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_navy"}])
    show_screen(chat_id, "🛳️ **وسایل نقلیه دریایی**", {"inline_keyboard": keyboard})


def send_shop_submarine(chat_id):
    keyboard = []
    for key, item in SUBMARINES.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_submarine_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_navy"}])
    show_screen(chat_id, "🐋 **زیردریایی‌ها**", {"inline_keyboard": keyboard})


def send_shop_carrier(chat_id):
    keyboard = []
    for key, item in AIRCRAFT_CARRIERS.items():
        keyboard.append([{"text": f"{item['icon']} {item['name']} | {item['price']} سکه | {item['count']} عدد", "callback_data": f"buy_carrier_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "shop_navy"}])
    show_screen(chat_id, "🚢 **ناوهای هواپیمابر**", {"inline_keyboard": keyboard})


# ==================== خرید ساختمان ====================
def buy_building(chat_id, user_id, building_key):
    # 🔄 lazy import برای جلوگیری از حلقه import
    from .dashboard import send_dashboard

    item = BUILDINGS[building_key]
    user = players_data.get(user_id, {})
    sanctioned, penalty, end_date = is_sanctioned(user_id)
    original_price = item["price"]
    if sanctioned:
        price = int(original_price * (1 + penalty))
        penalty_percent = int(penalty * 100)
        remaining_days = int((end_date - time.time()) / 86400) + 1
        if user.get("credit", 0) >= price:
            players_data[user_id]["credit"] = user.get("credit", 0) - price
            players_data[user_id][f"{building_key}_count"] = user.get(f"{building_key}_count", 0) + 1
            db.save_player(user_id, players_data[user_id])
            send_message(chat_id, f"✅ **{item['name']} خریداری شد!**\n💰 هزینه اصلی: {original_price:,} سکه\n⚠️ هزینه با جریمه {penalty_percent}%: {price:,} سکه\n📝 {item['description']}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}\n📅 تا {remaining_days} روز دیگر تحریم دارید!")
        else:
            send_message(chat_id, f"❌ موجودی کافی نیست! به {price:,} سکه نیاز دارید.")
    else:
        price = original_price
        if user.get("credit", 0) >= price:
            players_data[user_id]["credit"] = user.get("credit", 0) - price
            players_data[user_id][f"{building_key}_count"] = user.get(f"{building_key}_count", 0) + 1
            db.save_player(user_id, players_data[user_id])
            send_message(chat_id, f"✅ **{item['name']} خریداری شد!**\n💰 هزینه: {price:,} سکه\n📝 {item['description']}\n💎 سکه باقیمانده: {players_data[user_id]['credit']:,}")
        else:
            send_message(chat_id, f"❌ موجودی کافی نیست! به {price:,} سکه نیاز دارید.")
    send_dashboard(chat_id, user_id)
