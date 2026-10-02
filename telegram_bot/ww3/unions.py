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
from .config import MAX_ITEM_DONATION, UNION_DONATION_LIMITS
from .helpers import generate_union_id, get_union_capacity, get_union_level_price, send_message, send_to_group, show_screen
from .state import db, donation_cooldown, players_data, union_requests, unions_data, waiting_for_donation_amount, waiting_for_union_create, waiting_for_union_deposit, waiting_for_union_search, waiting_for_union_withdraw
from .static_data import AIR_DEFENSES, DRONES, ECONOMIC_ITEMS, FIGHTERS, HELICOPTERS, MINES, MISSILES, TANKS

# ==================== ماژول unions ====================


# ==================== اتحاد ====================
def send_alliance_panel(chat_id, user_id):
    user = players_data.get(user_id, {})
    user_union = user.get("union")
    
    # ==================== بررسی و رفع خودکار اتحاد نامعتبر ====================
    if user_union and user_union not in unions_data:
        # اتحاد کاربر وجود ندارد، پاک کن
        players_data[user_id]["union"] = None
        db.save_player(user_id, players_data[user_id])
        user_union = None
        show_screen(chat_id, "⚠️ **اتحاد شما نامعتبر بود و حذف شد!**\n━━━━━━━━━━━━━━━━━━\n💡 اکنون می‌توانید عضو اتحاد دیگری شوید یا اتحاد جدید بسازید.")
    # ==========================================================================
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📋 لیست اتحادها", "callback_data": "union_list"}],
            [{"text": "🔍 جستجو", "callback_data": "union_search"}],
            [{"text": "🏭 تولید", "callback_data": "union_production"}],
            [{"text": "💰 ثروت", "callback_data": "union_wealth"}],
            [{"text": "⚔️ قدرت", "callback_data": "union_power"}],
            [{"text": "🆕 ساخت اتحاد", "callback_data": "union_create"}],
        ]
    }
    
    if user_union and user_union in unions_data:
        info = unions_data[user_union]
        is_owner = info.get('owner') == user_id
        capacity = get_union_capacity(info.get('level', 1))
        pending_count = sum(1 for req in union_requests.values() if req.get("union_name") == user_union and req.get("status") == "pending")
        
        keyboard["inline_keyboard"].insert(0, [{"text": "📋 اعضا", "callback_data": f"union_members_{user_union}"}])
        keyboard["inline_keyboard"].insert(1, [{"text": "🎁 اهدا به هم‌اتحدی", "callback_data": f"union_donate_{user_union}"}])
        keyboard["inline_keyboard"].insert(2, [{"text": "🚪 خروج از اتحاد", "callback_data": f"union_leave_{user_union}"}])
        
        if is_owner:
            keyboard["inline_keyboard"].insert(3, [{"text": f"📥 درخواست‌ها ({pending_count})", "callback_data": f"union_requests_{user_union}"}])
            keyboard["inline_keyboard"].insert(4, [{"text": "🏦 خزانه", "callback_data": f"union_treasury_{user_union}"}])
            keyboard["inline_keyboard"].insert(5, [{"text": "⬆️ آپگرید", "callback_data": f"union_upgrade_{user_union}"}])
            keyboard["inline_keyboard"].insert(6, [{"text": "🚪 اخراج عضو", "callback_data": f"union_kick_menu_{user_union}"}])  # <--- این خط رو اضافه کن
            keyboard["inline_keyboard"].insert(7, [{"text": "🗑 حذف اتحاد", "callback_data": f"union_delete_{user_union}"}])
        
        donation_limit = UNION_DONATION_LIMITS.get(info.get('level', 1), 20000)
        
        text = f"""🤝 **اتحاد | {user_union}**
━━━━━━━━━━━━━━━━━━
🆔 آیدی: {info.get('union_id')}
👑 رهبر: {info.get('owner_name')}
👥 اعضا: {len(info.get('members', []))}/{capacity}
⭐ لول: {info.get('level', 1)}
🏦 خزانه: {info.get('treasury', 0):,} سکه
🎁 سقف اهدا: {donation_limit:,} سکه
📦 سقف اهدای تجهیزات: {MAX_ITEM_DONATION} عدد
📅 محدودیت اهدا: هر 48 ساعت یکبار
📥 درخواست‌های pending: {pending_count}"""
    else:
        text = "🤝 **پنل اتحاد**\n━━━━━━━━━━━━━━━━━━\n❌ شما عضو هیچ اتحادی نیستید.\n\nاز دکمه‌های زیر برای پیدا کردن یا ساخت اتحاد استفاده کنید:"
    
    keyboard["inline_keyboard"].append([{"text": "🔙 بازگشت", "callback_data": "dashboard"}])
    show_screen(chat_id, text, keyboard)



def union_list(chat_id):
    if not unions_data:
        send_message(chat_id, "📋 هیچ اتحادی وجود ندارد!")
        return
    items = list(unions_data.items())
    random.shuffle(items)
    items = items[:20]
    text = "📋 **لیست اتحادها**\n━━━━━━━━━━━━━━━━━━\n"
    for name, info in items:
        text += f"\n🏛 **{name}**\n🆔 {info.get('union_id')}\n👥 {len(info.get('members', []))} عضو\n⭐ لول {info.get('level', 1)}\n━━━━━━━━━━━━━━━━━━"
    keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "alliance"}]]}
    send_message(chat_id, text, keyboard)



def union_search(chat_id, user_id):
    send_message(chat_id, "🔍 **نام یا آیدی اتحاد را وارد کن:**")
    waiting_for_union_search[user_id] = True



def process_union_search(chat_id, search_term):
    found = None
    for name, info in unions_data.items():
        if name == search_term or info.get('union_id') == search_term:
            found = name
            break
    if not found:
        send_message(chat_id, "❌ اتحاد یافت نشد!")
        return
    info = unions_data[found]
    capacity = get_union_capacity(info.get('level', 1))
    text = f"""🔍 **نتیجه جستجو: {found}**
━━━━━━━━━━━━━━━━━━
🆔 آیدی: {info.get('union_id')}
👑 رهبر: {info.get('owner_name')}
👥 اعضا: {len(info.get('members', []))}/{capacity}
⭐ لول: {info.get('level', 1)}
🏦 خزانه: {info.get('treasury', 0):,} سکه"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "📋 اعضا", "callback_data": f"union_members_{found}"}],
            [{"text": "🆕 درخواست عضویت", "callback_data": f"union_join_request_{found}"}],
            [{"text": "🔙 بازگشت", "callback_data": "alliance"}]
        ]
    }
    send_message(chat_id, text, keyboard)



def union_production(chat_id):
    if not unions_data:
        send_message(chat_id, "❌ هیچ اتحادی وجود ندارد!")
        return
    scores = []
    for name, info in unions_data.items():
        total = 0
        for m in info.get('members', []):
            total += players_data.get(m, {}).get('daily_profit', 0)
        scores.append((name, total, len(info.get('members', []))))
    scores.sort(key=lambda x: x[1], reverse=True)
    text = "🏭 **10 اتحاد برتر تولید**\n━━━━━━━━━━━━━━━━━━\n"
    for i, (name, profit, members) in enumerate(scores[:10], 1):
        text += f"\n{i}. 🏛 **{name}**\n   📈 سود: {profit:,}\n   👥 {members} عضو\n━━━━━━━━━━━━━━━━━━"
    keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "alliance"}]]}
    send_message(chat_id, text, keyboard)



def union_wealth(chat_id):
    if not unions_data:
        send_message(chat_id, "❌ هیچ اتحادی وجود ندارد!")
        return
    sorted_unions = sorted(unions_data.items(), key=lambda x: x[1].get('treasury', 0), reverse=True)
    text = "💰 **10 اتحاد برتر ثروت**\n━━━━━━━━━━━━━━━━━━\n"
    for i, (name, info) in enumerate(sorted_unions[:10], 1):
        text += f"\n{i}. 🏛 **{name}**\n   🏦 خزانه: {info.get('treasury', 0):,}\n   👥 {len(info.get('members', []))} عضو\n━━━━━━━━━━━━━━━━━━"
    keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "alliance"}]]}
    send_message(chat_id, text, keyboard)



def union_power(chat_id):
    if not unions_data:
        send_message(chat_id, "❌ هیچ اتحادی وجود ندارد!")
        return
    scores = []
    for name, info in unions_data.items():
        total = 0
        count = 0
        for m in info.get('members', []):
            member = players_data.get(m, {})
            total += member.get('defense', 0) + member.get('attack_power', 0)
            count += 1
        avg = total / count if count > 0 else 0
        scores.append((name, avg, count))
    scores.sort(key=lambda x: x[1], reverse=True)
    text = "⚔️ **10 اتحاد برتر قدرت**\n━━━━━━━━━━━━━━━━━━\n"
    for i, (name, power, members) in enumerate(scores[:10], 1):
        text += f"\n{i}. 🏛 **{name}**\n   💪 قدرت: {int(power):,}\n   👥 {members} عضو\n━━━━━━━━━━━━━━━━━━"
    keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "alliance"}]]}
    send_message(chat_id, text, keyboard)



def union_create(chat_id, user_id):
    if players_data.get(user_id, {}).get("union"):
        send_message(chat_id, "❌ شما قبلاً عضو یک اتحاد هستید!")
        return
    send_message(chat_id, "🆕 **نام اتحاد را وارد کن (۳ تا ۲۰ کاراکتر):**")
    waiting_for_union_create[user_id] = True



def process_union_create(chat_id, user_id, union_name):
    if len(union_name) < 3 or len(union_name) > 20:
        send_message(chat_id, "❌ نام باید بین ۳ تا ۲۰ کاراکتر باشد!")
        return
    if union_name in unions_data:
        send_message(chat_id, f"❌ اتحاد '{union_name}' وجود دارد!")
        return
    union_id = generate_union_id()
    unions_data[union_name] = {
        "union_id": union_id,
        "owner": user_id,
        "owner_name": players_data[user_id].get("player_name", "نامشخص"),
        "members": [user_id],
        "level": 1,
        "treasury": 0,
        "total_deposits": 0,
        "total_withdrawals": 0,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    players_data[user_id]["union"] = union_name
    db.save_union(union_name, unions_data[union_name])
    db.save_player(user_id, players_data[user_id])
    send_message(chat_id, f"✅ **اتحاد '{union_name}' ساخته شد!**\n🆔 آیدی: `{union_id}`\n⭐ لول 1 | ظرفیت: 2 عضو")
    send_alliance_panel(chat_id, user_id)



def show_union_members(chat_id, union_name):
    info = unions_data.get(union_name)
    if not info:
        send_message(chat_id, "❌ اتحاد یافت نشد!")
        return
    text = f"📋 **اعضای اتحاد {union_name}**\n━━━━━━━━━━━━━━━━━━\n"
    for i, m in enumerate(info.get('members', []), 1):
        member = players_data.get(m, {})
        prefix = "👑" if m == info.get('owner') else "👤"
        text += f"\n{i}. {prefix} {member.get('player_name', 'ناشناس')}\n   🌍 {member.get('country', 'نامشخص')}"
    keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "alliance"}]]}
    send_message(chat_id, text, keyboard)



def union_treasury_menu(chat_id, user_id, union_name):
    info = unions_data.get(union_name)
    if not info or info.get('owner') != user_id:
        show_screen(chat_id, "❌ دسترسی ندارید!")
        return
    keyboard = {
        "inline_keyboard": [
            [{"text": "💰 واریز", "callback_data": f"union_deposit_{union_name}"}],
            [{"text": "💸 برداشت", "callback_data": f"union_withdraw_{union_name}"}],
            [{"text": "🔙 بازگشت", "callback_data": "alliance"}]
        ]
    }
    show_screen(chat_id, f"🏦 **خزانه {union_name}**\n💰 موجودی: {info.get('treasury', 0):,} سکه", keyboard)



def union_deposit(chat_id, user_id, union_name):
    info = unions_data.get(union_name)
    if not info or info.get('owner') != user_id:
        send_message(chat_id, "❌ دسترسی ندارید!")
        return
    send_message(chat_id, "💰 **مبلغ واریز را وارد کن (سکه):**")
    waiting_for_union_deposit[user_id] = union_name



def process_union_deposit(chat_id, user_id, union_name, amount):
    try:
        amount = int(amount)
        if amount <= 0:
            send_message(chat_id, "❌ مقدار باید بیشتر از 0 باشد!")
            return
        info = unions_data.get(union_name)
        user = players_data.get(user_id, {})
        if user.get('credit', 0) >= amount:
            players_data[user_id]['credit'] = user.get('credit', 0) - amount
            info['treasury'] = info.get('treasury', 0) + amount
            info['total_deposits'] = info.get('total_deposits', 0) + amount
            db.save_player(user_id, players_data[user_id])
            db.save_union(union_name, info)
            send_message(chat_id, f"✅ {amount:,} سکه واریز شد!")
        else:
            send_message(chat_id, f"❌ موجودی کافی نیست!")
        union_treasury_menu(chat_id, user_id, union_name)
    except:
        send_message(chat_id, "❌ عدد معتبر وارد کن!")



def union_withdraw(chat_id, user_id, union_name):
    info = unions_data.get(union_name)
    if not info or info.get('owner') != user_id:
        send_message(chat_id, "❌ دسترسی ندارید!")
        return
    send_message(chat_id, "💸 **مبلغ برداشت را وارد کن (سکه):**")
    waiting_for_union_withdraw[user_id] = union_name



def process_union_withdraw(chat_id, user_id, union_name, amount):
    try:
        amount = int(amount)
        if amount <= 0:
            send_message(chat_id, "❌ مقدار باید بیشتر از 0 باشد!")
            return
        info = unions_data.get(union_name)
        if info.get('treasury', 0) >= amount:
            info['treasury'] = info.get('treasury', 0) - amount
            info['total_withdrawals'] = info.get('total_withdrawals', 0) + amount
            players_data[user_id]['credit'] = players_data[user_id].get('credit', 0) + amount
            db.save_player(user_id, players_data[user_id])
            db.save_union(union_name, info)
            send_message(chat_id, f"✅ {amount:,} سکه برداشت شد!")
        else:
            send_message(chat_id, f"❌ موجودی خزانه کافی نیست!")
        union_treasury_menu(chat_id, user_id, union_name)
    except:
        send_message(chat_id, "❌ عدد معتبر وارد کن!")



def union_upgrade(chat_id, user_id, union_name):
    info = unions_data.get(union_name)
    if not info or info.get('owner') != user_id:
        send_message(chat_id, "❌ دسترسی ندارید!")
        return
    level = info.get('level', 1)
    if level >= 5:
        send_message(chat_id, "❌ حداکثر لول 5 است!")
        return
    price = get_union_level_price(level)
    if info.get('treasury', 0) >= price:
        info['treasury'] = info.get('treasury', 0) - price
        info['level'] = level + 1
        db.save_union(union_name, info)
        new_capacity = get_union_capacity(level + 1)
        send_message(chat_id, f"✅ **اتحاد به لول {level + 1} ارتقا یافت!**\n👥 ظرفیت جدید: {new_capacity} عضو")
    else:
        send_message(chat_id, f"❌ خزانه کافی نیست! به {price:,} سکه نیاز دارید.")
    send_alliance_panel(chat_id, user_id)



def union_delete(chat_id, user_id, union_name):
    info = unions_data.get(union_name)
    if not info or info.get('owner') != user_id:
        send_message(chat_id, "❌ دسترسی ندارید!")
        return
    for m in info.get('members', []):
        if m in players_data:
            players_data[m]['union'] = None
            db.save_player(m, players_data[m])
    del unions_data[union_name]
    db.delete_union(union_name)
    send_message(chat_id, f"✅ **اتحاد '{union_name}' حذف شد!**")
    send_alliance_panel(chat_id, user_id)



def union_leave(chat_id, user_id, union_name):
    info = unions_data.get(union_name)
    if not info:
        send_message(chat_id, "❌ اتحاد یافت نشد!")
        return
    if user_id not in info.get('members', []):
        send_message(chat_id, "❌ شما عضو این اتحاد نیستید!")
        return
    info['members'].remove(user_id)
    players_data[user_id]['union'] = None
    if info.get('owner') == user_id:
        if info.get('members'):
            new_owner = info['members'][0]
            info['owner'] = new_owner
            info['owner_name'] = players_data[new_owner].get('player_name', 'نامشخص')
            send_message(int(new_owner), f"👑 **شما لیدر جدید اتحاد {union_name} شدید!**")
        else:
            del unions_data[union_name]
            db.delete_union(union_name)
            send_message(chat_id, f"🗑 **اتحاد {union_name} به دلیل نبود عضو حذف شد!**")
            send_alliance_panel(chat_id, user_id)
            return
    db.save_union(union_name, info)
    db.save_player(user_id, players_data[user_id])
    send_message(chat_id, f"🚪 **شما از اتحاد {union_name} خارج شدید!**")
    send_alliance_panel(chat_id, user_id)




# ==================== توابع اهدا در اتحاد ====================

def union_donate_menu(chat_id, user_id, union_name):
    """نمایش اعضای اتحاد برای انتخاب فرد مورد نظر برای اهدا"""
    user = players_data.get(user_id, {})
    
    if user.get("union") != union_name:
        show_screen(chat_id, "❌ شما عضو این اتحاد نیستید!")
        return
    
    # بررسی محدودیت 48 ساعت
    if user_id in donation_cooldown:
        last_donation = donation_cooldown[user_id]
        if time.time() - last_donation < 172800:
            remaining_hours = int((172800 - (time.time() - last_donation)) / 3600)
            remaining_minutes = int(((172800 - (time.time() - last_donation)) % 3600) / 60)
            show_screen(chat_id, f"⏰ **شما در محدودیت اهدا هستید!**\n"
                                 f"📅 زمان باقیمانده: {remaining_hours} ساعت {remaining_minutes} دقیقه\n"
                                 f"💡 هر 48 ساعت فقط یک بار می‌توانید اهدا کنید.")
            return
    
    union_info = unions_data.get(union_name, {})
    members = union_info.get('members', [])
    
    if len(members) <= 1:
        show_screen(chat_id, "❌ شما تنها عضو اتحاد هستید! کسی برای اهدا وجود ندارد.")
        return
    
    keyboard = []
    for member_id in members:
        if member_id != user_id:
            member_data = players_data.get(member_id, {})
            if member_data.get("player_name"):
                keyboard.append([{"text": f"🎁 {member_data.get('player_name')} - {member_data.get('country', 'نامشخص')}", 
                                 "callback_data": f"union_donate_select_{member_id}"}])
    
    if not keyboard:
        show_screen(chat_id, "❌ هیچ عضو دیگری در اتحاد یافت نشد!")
        return
    
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "alliance"}])
    
    donation_limit = UNION_DONATION_LIMITS.get(union_info.get('level', 1), 20000)
    
    show_screen(chat_id, f"🎁 **اهدای سکه و تجهیزات**\n━━━━━━━━━━━━━━━━━━\n"
                          f"🤝 اتحاد: {union_name}\n"
                          f"💰 سقف اهدای سکه: {donation_limit:,} سکه\n"
                          f"📦 سقف اهدای تجهیزات: {MAX_ITEM_DONATION} عدد\n"
                          f"⏰ محدودیت: هر 48 ساعت یکبار\n━━━━━━━━━━━━━━━━━━\n\n"
                          f"**فرد مورد نظر را انتخاب کنید:**", 
                 {"inline_keyboard": keyboard})




def union_donate_select_target(chat_id, user_id, target_id):
    """انتخاب نوع اهدا بعد از انتخاب فرد"""
    target_data = players_data.get(target_id, {})
    if not target_data.get("player_name"):
        send_message(chat_id, "❌ کاربر یافت نشد!")
        return
    
    user_union = players_data.get(user_id, {}).get("union")
    target_union = target_data.get("union")
    
    if not user_union or user_union != target_union:
        send_message(chat_id, "❌ این کاربر هم‌اتحدی شما نیست!")
        return
    
    union_info = unions_data.get(user_union, {})
    donation_limit = UNION_DONATION_LIMITS.get(union_info.get('level', 1), 20000)
    
    keyboard = {
        "inline_keyboard": [
            [{"text": f"💰 اهدای سکه (حداکثر {donation_limit:,})", "callback_data": f"union_donate_credit_{target_id}"}],
            [{"text": f"📦 اهدای تجهیزات (حداکثر {MAX_ITEM_DONATION} عدد)", "callback_data": f"union_donate_item_{target_id}"}],
            [{"text": "🔙 بازگشت", "callback_data": f"union_donate_{user_union}"}]
        ]
    }
    
    send_message(chat_id, f"🎁 **اهدای به {target_data.get('player_name')}**\n━━━━━━━━━━━━━━━━━━\n"
                          f"💰 سقف اهدای سکه: {donation_limit:,}\n"
                          f"📦 سقف اهدای تجهیزات: {MAX_ITEM_DONATION} عدد\n"
                          f"⏰ محدودیت: هر 48 ساعت یکبار\n━━━━━━━━━━━━━━━━━━\n\n"
                          f"**نوع اهدا را انتخاب کنید:**", keyboard)




def union_donate_credit(chat_id, user_id, target_id):
    """دریافت مبلغ برای اهدای سکه"""
    target_data = players_data.get(target_id, {})
    user_union = players_data.get(user_id, {}).get("union")
    union_info = unions_data.get(user_union, {})
    donation_limit = UNION_DONATION_LIMITS.get(union_info.get('level', 1), 20000)
    
    waiting_for_donation_amount[user_id] = {
        "target_id": target_id,
        "type": "credit"
    }
    
    send_message(chat_id, f"💰 **مبلغ اهدای سکه به {target_data.get('player_name')} را وارد کنید:**\n"
                          f"━━━━━━━━━━━━━━━━━━\n"
                          f"💰 سقف مجاز: {donation_limit:,} سکه\n"
                          f"💎 موجودی شما: {players_data[user_id].get('credit', 0):,}\n\n"
                          f"(فقط عدد وارد کنید)")



def process_donation_credit(chat_id, user_id, amount, target_id):
    """پردازش اهدای سکه"""
    user = players_data.get(user_id, {})
    target = players_data.get(target_id, {})
    
    if user_id in donation_cooldown:
        if time.time() - donation_cooldown[user_id] < 172800:
            send_message(chat_id, "❌ شما در محدودیت اهدا هستید!")
            return
    
    if user.get("union") != target.get("union"):
        send_message(chat_id, "❌ این کاربر هم‌اتحدی شما نیست!")
        return
    
    user_union = user.get("union")
    union_info = unions_data.get(user_union, {})
    donation_limit = UNION_DONATION_LIMITS.get(union_info.get('level', 1), 20000)
    
    if amount > donation_limit:
        send_message(chat_id, f"❌ مبلغ اهدا بیشتر از سقف مجاز ({donation_limit:,}) است!")
        return
    
    if amount > user.get("credit", 0):
        send_message(chat_id, f"❌ موجودی شما کافی نیست! شما {user.get('credit', 0):,} سکه دارید.")
        return
    
    if amount <= 0:
        send_message(chat_id, "❌ مبلغ باید بیشتر از 0 باشد!")
        return
    
    players_data[user_id]["credit"] = user.get("credit", 0) - amount
    players_data[target_id]["credit"] = target.get("credit", 0) + amount
    
    donation_cooldown[user_id] = time.time()
    
    db.save_player(user_id, players_data[user_id])
    db.save_player(target_id, players_data[target_id])
    
    send_message(chat_id, f"✅ **{amount:,} سکه به {target.get('player_name')} اهدا شد!**\n"
                          f"💰 موجودی شما: {players_data[user_id]['credit']:,}")
    
    send_message(int(target_id), f"🎁 **شما {amount:,} سکه از {user.get('player_name')} دریافت کردید!**\n"
                                 f"💰 موجودی جدید شما: {players_data[target_id]['credit']:,}")
    
    send_alliance_panel(chat_id, user_id)




def union_donate_item(chat_id, user_id, target_id):
    """نمایش لیست تجهیزات قابل اهدا"""
    target_data = players_data.get(target_id, {})
    
    keyboard = []
    
    for mine_key, mine_info in MINES.items():
        count = players_data[user_id].get(f"{mine_key}_count", 0)
        if count > 0:
            keyboard.append([{"text": f"⛏️ {mine_info['name']} (موجودی: {count})", 
                             "callback_data": f"union_donate_item_mine_{mine_key}_{target_id}"}])
    
    for fighter_key, fighter_info in FIGHTERS.items():
        count = players_data[user_id].get(f"{fighter_key}_fighter_count", 0)
        if count > 0:
            keyboard.append([{"text": f"✈️ {fighter_info['name']} (موجودی: {count})", 
                             "callback_data": f"union_donate_item_fighter_{fighter_key}_{target_id}"}])
    
    for tank_key, tank_info in TANKS.items():
        count = players_data[user_id].get(f"{tank_key}_tank_count", 0)
        if count > 0:
            keyboard.append([{"text": f"🪖 {tank_info['name']} (موجودی: {count})", 
                             "callback_data": f"union_donate_item_tank_{tank_key}_{target_id}"}])
    
    for missile_key, missile_info in MISSILES.items():
        count = players_data[user_id].get(f"{missile_key}_missile_count", 0)
        if count > 0:
            keyboard.append([{"text": f"🚀 {missile_info['name']} (موجودی: {count})", 
                             "callback_data": f"union_donate_item_missile_{missile_key}_{target_id}"}])
    
    for heli_key, heli_info in HELICOPTERS.items():
        count = players_data[user_id].get(f"{heli_key}_helicopter_count", 0)
        if count > 0:
            keyboard.append([{"text": f"🚁 {heli_info['name']} (موجودی: {count})", 
                             "callback_data": f"union_donate_item_helicopter_{heli_key}_{target_id}"}])
    
    for drone_key, drone_info in DRONES.items():
        count = players_data[user_id].get(f"{drone_key}_drone_count", 0)
        if count > 0:
            keyboard.append([{"text": f"🛸 {drone_info['name']} (موجودی: {count})", 
                             "callback_data": f"union_donate_item_drone_{drone_key}_{target_id}"}])
    
    for defense_key, defense_info in AIR_DEFENSES.items():
        count = players_data[user_id].get(f"{defense_key}_air_defense_count", 0)
        if count > 0:
            keyboard.append([{"text": f"🛡️ {defense_info['name']} (موجودی: {count})", 
                             "callback_data": f"union_donate_item_defense_{defense_key}_{target_id}"}])
    
    if not keyboard:
        send_message(chat_id, "❌ شما هیچ تجهیزی برای اهدا ندارید!")
        return
    
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": f"union_donate_{target_id}"}])
    
    send_message(chat_id, f"📦 **انتخاب تجهیزات برای اهدا به {target_data.get('player_name')}**\n"
                          f"━━━━━━━━━━━━━━━━━━\n"
                          f"📊 سقف اهدا: حداکثر {MAX_ITEM_DONATION} عدد\n"
                          f"⏰ محدودیت: هر 48 ساعت یکبار\n━━━━━━━━━━━━━━━━━━\n\n"
                          f"**نوع تجهیزات را انتخاب کنید:**", 
                 {"inline_keyboard": keyboard})




def union_donate_item_amount(chat_id, user_id, category, item_key, target_id):
    """دریافت تعداد برای اهدای تجهیزات"""
    waiting_for_donation_amount[user_id] = {
        "target_id": target_id,
        "type": "item",
        "category": category,
        "item_key": item_key
    }
    
    item_name = "تجهیزات"
    if category == "mine":
        item_name = MINES.get(item_key, {}).get("name", item_key)
    elif category == "fighter":
        item_name = FIGHTERS.get(item_key, {}).get("name", item_key)
    elif category == "tank":
        item_name = TANKS.get(item_key, {}).get("name", item_key)
    elif category == "missile":
        item_name = MISSILES.get(item_key, {}).get("name", item_key)
    elif category == "helicopter":
        item_name = HELICOPTERS.get(item_key, {}).get("name", item_key)
    elif category == "drone":
        item_name = DRONES.get(item_key, {}).get("name", item_key)
    elif category == "defense":
        item_name = AIR_DEFENSES.get(item_key, {}).get("name", item_key)
    
    current_count = 0
    if category == "mine":
        current_count = players_data[user_id].get(f"{item_key}_count", 0)
    elif category == "fighter":
        current_count = players_data[user_id].get(f"{item_key}_fighter_count", 0)
    elif category == "tank":
        current_count = players_data[user_id].get(f"{item_key}_tank_count", 0)
    elif category == "missile":
        current_count = players_data[user_id].get(f"{item_key}_missile_count", 0)
    elif category == "helicopter":
        current_count = players_data[user_id].get(f"{item_key}_helicopter_count", 0)
    elif category == "drone":
        current_count = players_data[user_id].get(f"{item_key}_drone_count", 0)
    elif category == "defense":
        current_count = players_data[user_id].get(f"{item_key}_air_defense_count", 0)
    
    send_message(chat_id, f"📦 **تعداد {item_name} برای اهدا به {players_data[target_id].get('player_name')} را وارد کنید:**\n"
                          f"━━━━━━━━━━━━━━━━━━\n"
                          f"📊 سقف مجاز: حداکثر {MAX_ITEM_DONATION} عدد\n"
                          f"💎 موجودی شما: {current_count} عدد\n\n"
                          f"(فقط عدد وارد کنید)")



# ==================== اخراج عضو از اتحاد ====================

def union_kick_member(chat_id, user_id, union_name, target_id):
    """اخراج عضو از اتحاد توسط لیدر"""
    
    # بررسی وجود اتحاد
    if union_name not in unions_data:
        send_message(chat_id, "❌ اتحاد یافت نشد!")
        return
    
    union_info = unions_data[union_name]
    
    # بررسی اینکه کاربر لیدر است
    if union_info.get("owner") != user_id:
        send_message(chat_id, "❌ فقط لیدر اتحاد می‌تواند اعضا را اخراج کند!")
        return
    
    # بررسی اینکه هدف خود لیدر نباشد
    if target_id == user_id:
        send_message(chat_id, "❌ نمی‌توانید خودتان را اخراج کنید!\nبرای خروج از اتحاد از گزینه خروج استفاده کنید.")
        return
    
    # بررسی اینکه هدف عضو اتحاد باشد
    if target_id not in union_info.get("members", []):
        send_message(chat_id, "❌ این کاربر عضو اتحاد شما نیست!")
        return
    
    target_name = players_data.get(target_id, {}).get("player_name", "نامشخص")
    target_country = players_data.get(target_id, {}).get("country", "نامشخص")
    
    # اخراج عضو
    union_info["members"].remove(target_id)
    players_data[target_id]["union"] = None
    
    # ذخیره در دیتابیس
    db.save_union(union_name, union_info)
    db.save_player(target_id, players_data[target_id])
    
    # پیام به لیدر
    send_message(chat_id, f"✅ **عضو از اتحاد اخراج شد!**\n━━━━━━━━━━━━━━━━━━\n👤 کاربر: {target_name}\n🌍 کشور: {target_country}\n🤝 اتحاد: {union_name}")
    
    # پیام به عضو اخراج شده
    send_message(int(target_id), 
        f"⚠️ **شما از اتحاد {union_name} اخراج شدید!**\n━━━━━━━━━━━━━━━━━━\n"
        f"👑 لیدر اتحاد: {union_info.get('owner_name')}\n"
        f"💡 اکنون می‌توانید به اتحاد دیگری بپیوندید یا اتحاد جدید بسازید.")
    
    # اطلاع به گروه
    send_to_group(f"🚪 **اخراج از اتحاد**\n━━━━━━━━━━━━━━━━━━\n"
                  f"👤 {target_name} از اتحاد {union_name} اخراج شد.\n"
                  f"👑 توسط لیدر: {union_info.get('owner_name')}")




def show_union_kick_menu(chat_id, user_id, union_name):
    """نمایش لیست اعضا برای اخراج"""
    
    if union_name not in unions_data:
        send_message(chat_id, "❌ اتحاد یافت نشد!")
        return
    
    union_info = unions_data[union_name]
    
    # بررسی اینکه کاربر لیدر است
    if union_info.get("owner") != user_id:
        send_message(chat_id, "❌ فقط لیدر اتحاد می‌تواند اعضا را اخراج کند!")
        return
    
    members = union_info.get("members", [])
    
    if len(members) <= 1:
        send_message(chat_id, "❌ فقط شما در اتحاد هستید! کسی برای اخراج وجود ندارد.")
        return
    
    text = f"🚪 **اخراج عضو از اتحاد {union_name}**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👑 لیدر: {union_info.get('owner_name')}\n"
    text += f"👥 اعضا: {len(members)} نفر\n━━━━━━━━━━━━━━━━━━\n\n"
    text += f"**عضو مورد نظر برای اخراج را انتخاب کنید:**\n\n"
    
    keyboard = []
    for member_id in members:
        if member_id != user_id:  # خود لیدر رو نشون نده
            member_data = players_data.get(member_id, {})
            member_name = member_data.get("player_name", "نامشخص")
            member_country = member_data.get("country", "نامشخص")
            text += f"👤 {member_name} - {member_country}\n"
            keyboard.append([{"text": f"🚪 اخراج {member_name}", "callback_data": f"union_kick_{union_name}_{member_id}"}])
    
    keyboard.append([{"text": "🔙 بازگشت به پنل اتحاد", "callback_data": "alliance"}])
    
    send_message(chat_id, text, {"inline_keyboard": keyboard})


def process_donation_item(chat_id, user_id, count, target_id, category, item_key):
    """پردازش اهدای تجهیزات"""
    user = players_data.get(user_id, {})
    target = players_data.get(target_id, {})
    
    # بررسی محدودیت
    if user_id in donation_cooldown:
        if time.time() - donation_cooldown[user_id] < 172800:
            send_message(chat_id, "❌ شما در محدودیت اهدا هستید!")
            return
    
    # بررسی اتحاد
    if user.get("union") != target.get("union"):
        send_message(chat_id, "❌ این کاربر هم‌اتحدی شما نیست!")
        return
    
    if count > MAX_ITEM_DONATION:
        send_message(chat_id, f"❌ تعداد اهدا بیشتر از سقف مجاز ({MAX_ITEM_DONATION}) است!")
        return
    
    if count <= 0:
        send_message(chat_id, "❌ تعداد باید بیشتر از 0 باشد!")
        return
    
    # ========== محدودیت 10 تایی برای معادن و تجهیزات اقتصادی ==========
    LIMITED_CATEGORIES = ["mine", "economic"]  # معادن و تجهیزات اقتصادی
    
    if category in LIMITED_CATEGORIES:
        # بررسی سقف 10 تایی در سمت گیرنده
        current_target = target.get(f"{item_key}_count", 0)
        if current_target + count > 10:
            max_allowed = 10 - current_target
            if max_allowed <= 0:
                send_message(chat_id, f"❌ کاربر {target.get('player_name')} قبلاً 10 عدد از این تجهیزات دارد و نمی‌تواند بیشتر دریافت کند!")
                return
            else:
                send_message(chat_id, f"⚠️ کاربر {target.get('player_name')} فقط می‌تواند {max_allowed} عدد دیگر از این تجهیزات دریافت کند (حداکثر ۱۰ عدد).")
                return
    
    # بررسی موجودی و اهدا بر اساس نوع
    if category == "mine":
        current = user.get(f"{item_key}_count", 0)
        if count > current:
            send_message(chat_id, f"❌ شما فقط {current} عدد از این معدن دارید!")
            return
        
        # بررسی محدودیت سمت گیرنده
        current_target = target.get(f"{item_key}_count", 0)
        if current_target + count > 10:
            send_message(chat_id, f"❌ کاربر {target.get('player_name')} نمی‌تواند بیش از 10 عدد از این معدن داشته باشد!")
            return
        
        players_data[user_id][f"{item_key}_count"] = current - count
        players_data[target_id][f"{item_key}_count"] = current_target + count
        item_name = MINES.get(item_key, {}).get("name", item_key)
        
        mine_profit = MINES.get(item_key, {}).get("daily_profit", 0)
        players_data[user_id]["daily_profit"] = user.get("daily_profit", 0) - (mine_profit * count)
        players_data[target_id]["daily_profit"] = target.get("daily_profit", 0) + (mine_profit * count)
        
    elif category == "economic":
        current = user.get(f"{item_key}_count", 0)
        if count > current:
            send_message(chat_id, f"❌ شما فقط {current} عدد از این تجهیزات اقتصادی دارید!")
            return
        
        # بررسی محدودیت سمت گیرنده
        current_target = target.get(f"{item_key}_count", 0)
        if current_target + count > 10:
            send_message(chat_id, f"❌ کاربر {target.get('player_name')} نمی‌تواند بیش از 10 عدد از این تجهیزات اقتصادی داشته باشد!")
            return
        
        players_data[user_id][f"{item_key}_count"] = current - count
        players_data[target_id][f"{item_key}_count"] = current_target + count
        item_name = ECONOMIC_ITEMS.get(item_key, {}).get("name", item_key)
        
        economic_profit = ECONOMIC_ITEMS.get(item_key, {}).get("profit", 0)
        players_data[user_id]["daily_profit"] = user.get("daily_profit", 0) - (economic_profit * count)
        players_data[target_id]["daily_profit"] = target.get("daily_profit", 0) + (economic_profit * count)
        
    elif category == "fighter":
        current = user.get(f"{item_key}_fighter_count", 0)
        if count > current:
            send_message(chat_id, f"❌ شما فقط {current} عدد از این جنگنده دارید!")
            return
        players_data[user_id][f"{item_key}_fighter_count"] = current - count
        players_data[target_id][f"{item_key}_fighter_count"] = target.get(f"{item_key}_fighter_count", 0) + count
        item_name = FIGHTERS.get(item_key, {}).get("name", item_key)
        
        fighter_power = FIGHTERS.get(item_key, {}).get("power", 0)
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) - (fighter_power * count)
        players_data[target_id]["attack_power"] = target.get("attack_power", 0) + (fighter_power * count)
        
    elif category == "tank":
        current = user.get(f"{item_key}_tank_count", 0)
        if count > current:
            send_message(chat_id, f"❌ شما فقط {current} عدد از این تانک دارید!")
            return
        players_data[user_id][f"{item_key}_tank_count"] = current - count
        players_data[target_id][f"{item_key}_tank_count"] = target.get(f"{item_key}_tank_count", 0) + count
        item_name = TANKS.get(item_key, {}).get("name", item_key)
        
        tank_power = TANKS.get(item_key, {}).get("power", 0)
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) - (tank_power * count)
        players_data[target_id]["attack_power"] = target.get("attack_power", 0) + (tank_power * count)
        
    elif category == "missile":
        current = user.get(f"{item_key}_missile_count", 0)
        if count > current:
            send_message(chat_id, f"❌ شما فقط {current} عدد از این موشک دارید!")
            return
        players_data[user_id][f"{item_key}_missile_count"] = current - count
        players_data[target_id][f"{item_key}_missile_count"] = target.get(f"{item_key}_missile_count", 0) + count
        item_name = MISSILES.get(item_key, {}).get("name", item_key)
        
        missile_power = MISSILES.get(item_key, {}).get("power", 0)
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) - (missile_power * count)
        players_data[target_id]["attack_power"] = target.get("attack_power", 0) + (missile_power * count)
        
    elif category == "helicopter":
        current = user.get(f"{item_key}_helicopter_count", 0)
        if count > current:
            send_message(chat_id, f"❌ شما فقط {current} عدد از این هلیکوپتر دارید!")
            return
        players_data[user_id][f"{item_key}_helicopter_count"] = current - count
        players_data[target_id][f"{item_key}_helicopter_count"] = target.get(f"{item_key}_helicopter_count", 0) + count
        item_name = HELICOPTERS.get(item_key, {}).get("name", item_key)
        
        heli_power = HELICOPTERS.get(item_key, {}).get("power", 0)
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) - (heli_power * count)
        players_data[target_id]["attack_power"] = target.get("attack_power", 0) + (heli_power * count)
        
    elif category == "drone":
        current = user.get(f"{item_key}_drone_count", 0)
        if count > current:
            send_message(chat_id, f"❌ شما فقط {current} عدد از این پهباد دارید!")
            return
        players_data[user_id][f"{item_key}_drone_count"] = current - count
        players_data[target_id][f"{item_key}_drone_count"] = target.get(f"{item_key}_drone_count", 0) + count
        item_name = DRONES.get(item_key, {}).get("name", item_key)
        
        drone_power = DRONES.get(item_key, {}).get("power", 0)
        players_data[user_id]["attack_power"] = user.get("attack_power", 0) - (drone_power * count)
        players_data[target_id]["attack_power"] = target.get("attack_power", 0) + (drone_power * count)
        
    elif category == "defense":
        current = user.get(f"{item_key}_air_defense_count", 0)
        if count > current:
            send_message(chat_id, f"❌ شما فقط {current} عدد از این پدافند دارید!")
            return
        players_data[user_id][f"{item_key}_air_defense_count"] = current - count
        players_data[target_id][f"{item_key}_air_defense_count"] = target.get(f"{item_key}_air_defense_count", 0) + count
        item_name = AIR_DEFENSES.get(item_key, {}).get("name", item_key)
        
        defense_power = AIR_DEFENSES.get(item_key, {}).get("power", 0)
        players_data[user_id]["defense"] = user.get("defense", 5000) - (defense_power * count)
        players_data[target_id]["defense"] = target.get("defense", 5000) + (defense_power * count)
        
    else:
        send_message(chat_id, "❌ نوع تجهیزات نامعتبر!")
        return
    
    donation_cooldown[user_id] = time.time()
    
    db.save_player(user_id, players_data[user_id])
    db.save_player(target_id, players_data[target_id])
    
    send_message(chat_id, f"✅ **{count} عدد {item_name} به {target.get('player_name')} اهدا شد!**")
    send_message(int(target_id), f"🎁 **شما {count} عدد {item_name} از {user.get('player_name')} دریافت کردید!**")
    
    send_to_group(f"🎁 **اهدای تجهیزات در اتحاد**\n━━━━━━━━━━━━━━━━━━\n"
                  f"👤 از: {user.get('player_name')}\n"
                  f"🎯 به: {target.get('player_name')}\n"
                  f"📦 تعداد: {count} عدد {item_name}\n"
                  f"🤝 اتحاد: {user.get('union')}")
    
    send_alliance_panel(chat_id, user_id)




def send_join_request(chat_id, user_id, union_name):
    user = players_data.get(user_id, {})
    if user.get("union"):
        send_message(chat_id, f"❌ شما قبلاً عضو اتحاد {user['union']} هستید!")
        return
    if union_name not in unions_data:
        send_message(chat_id, "❌ اتحاد یافت نشد!")
        return
    union_info = unions_data[union_name]
    capacity = get_union_capacity(union_info.get('level', 1))
    if len(union_info.get('members', [])) >= capacity:
        send_message(chat_id, "❌ ظرفیت اتحاد پر است!")
        return
    for req_id, req in union_requests.items():
        if req.get("user_id") == user_id and req.get("union_name") == union_name and req.get("status") == "pending":
            remaining_time = 24 - int((time.time() - req.get("request_time")) / 3600)
            send_message(chat_id, f"❌ شما قبلاً درخواست عضویت داده‌اید!\n⏳ زمان باقیمانده: {remaining_time} ساعت")
            return
    request_id = generate_union_id()
    request_time = time.time()
    expiry_time = request_time + (24 * 3600)
    union_requests[request_id] = {
        "user_id": user_id,
        "user_name": user.get("player_name", "نامشخص"),
        "user_country": user.get("country", "نامشخص"),
        "user_score": user.get("score", 0),
        "union_name": union_name,
        "union_owner": union_info.get("owner"),
        "request_time": request_time,
        "expiry_time": expiry_time,
        "status": "pending"
    }
    db.save_union_request(request_id, union_requests[request_id])
    send_message(chat_id, f"✅ **درخواست عضویت شما به اتحاد {union_name} ارسال شد!**\n━━━━━━━━━━━━━━━━━━\n⏳ زمان انتظار: حداکثر 24 ساعت\n👑 لیدر اتحاد درخواست شما را بررسی خواهد کرد.\n\n💡 پس از تایید، شما به اتحاد اضافه خواهید شد.")
    owner_id = union_info.get("owner")
    if owner_id:
        remaining_requests = sum(1 for req in union_requests.values() if req.get("union_name") == union_name and req.get("status") == "pending")
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ تایید", "callback_data": f"approve_request_{request_id}"}],
                [{"text": "❌ رد", "callback_data": f"reject_request_{request_id}"}],
                [{"text": "📋 مشاهده درخواست", "callback_data": f"view_request_{request_id}"}]
            ]
        }
        send_message(int(owner_id), f"🆕 **درخواست عضویت جدید**\n━━━━━━━━━━━━━━━━━━\n🎮 اتحاد: {union_name}\n👤 کاربر: {user.get('player_name', 'نامشخص')}\n🌍 کشور: {user.get('country', 'نامشخص')}\n🏆 امتیاز: {user.get('score', 0)}\n⏳ مهلت تصمیم‌گیری: 24 ساعت\n━━━━━━━━━━━━━━━━━━\n📊 درخواست‌های pending: {remaining_requests}", keyboard)



def show_union_requests(chat_id, user_id, union_name):
    union_info = unions_data.get(union_name)
    if union_info.get('owner') != user_id:
        send_message(chat_id, "❌ فقط لیدر اتحاد می‌تواند درخواست‌ها را مشاهده کند!")
        return
    pending_requests = []
    for req_id, req in union_requests.items():
        if req.get("union_name") == union_name and req.get("status") == "pending":
            pending_requests.append((req_id, req))
    if not pending_requests:
        send_message(chat_id, "📋 **هیچ درخواست عضویت pending ای وجود ندارد!**")
        return
    text = f"📋 **درخواست‌های عضویت اتحاد {union_name}**\n━━━━━━━━━━━━━━━━━━\n"
    keyboard = []
    for req_id, req in pending_requests:
        remaining_hours = 24 - int((time.time() - req.get("request_time")) / 3600)
        text += f"\n👤 کاربر: {req.get('user_name')}\n"
        text += f"🌍 کشور: {req.get('user_country')}\n"
        text += f"🏆 امتیاز: {req.get('user_score')}\n"
        text += f"⏳ مهلت باقیمانده: {remaining_hours} ساعت\n"
        text += f"🆔 کد درخواست: {req_id[:8]}...\n━━━━━━━━━━━━━━━━━━\n"
        keyboard.append([
            {"text": f"✅ تایید {req.get('user_name')}", "callback_data": f"approve_request_{req_id}"},
            {"text": f"❌ رد {req.get('user_name')}", "callback_data": f"reject_request_{req_id}"}
        ])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": f"union_members_{union_name}"}])
    send_message(chat_id, text, {"inline_keyboard": keyboard})



def approve_join_request(chat_id, user_id, request_id):
    if request_id not in union_requests:
        send_message(chat_id, "❌ درخواست یافت نشد!")
        return
    request = union_requests[request_id]
    union_name = request.get("union_name")
    requester_id = request.get("user_id")
    union_info = unions_data.get(union_name)
    if union_info.get('owner') != user_id:
        send_message(chat_id, "❌ فقط لیدر اتحاد می‌تواند درخواست را تایید کند!")
        return
    if time.time() > request.get("expiry_time"):
        request["status"] = "expired"
        db.update_union_request_status(request_id, "expired")
        send_message(chat_id, "❌ زمان درخواست به اتمام رسیده است!")
        return
    requester_data = players_data.get(requester_id, {})
    if requester_data.get("union"):
        request["status"] = "rejected"
        db.update_union_request_status(request_id, "rejected")
        send_message(chat_id, f"❌ کاربر {requester_data.get('player_name')} قبلاً به اتحاد دیگری پیوسته است!")
        return
    capacity = get_union_capacity(union_info.get('level', 1))
    if len(union_info.get('members', [])) >= capacity:
        send_message(chat_id, "❌ ظرفیت اتحاد پر است!")
        request["status"] = "rejected"
        db.update_union_request_status(request_id, "rejected")
        return
    union_info['members'].append(requester_id)
    players_data[requester_id]['union'] = union_name
    request["status"] = "approved"
    db.save_union(union_name, union_info)
    db.save_player(requester_id, players_data[requester_id])
    db.update_union_request_status(request_id, "approved")
    send_message(chat_id, f"✅ درخواست عضویت {request.get('user_name')} تایید شد!")
    send_message(int(requester_id), f"🎉 **درخواست عضویت شما در اتحاد {union_name} تایید شد!**\n━━━━━━━━━━━━━━━━━━\n🎮 به خانواده {union_name} خوش آمدید!\n👑 لیدر اتحاد: {union_info.get('owner_name')}\n👥 اعضا: {len(union_info.get('members', []))}/{capacity}\n\n💡 از پنل اتحاد می‌توانید اطلاعات بیشتری ببینید.")
    for member_id in union_info.get('members', []):
        if member_id != user_id and member_id != requester_id:
            try:
                send_message(int(member_id), f"🎉 **کاربر جدید به اتحاد پیوست!**\n━━━━━━━━━━━━━━━━━━\n👤 کاربر: {request.get('user_name')}\n🌍 کشور: {request.get('user_country')}\n🏆 امتیاز: {request.get('user_score')}\n🎮 اتحاد: {union_name}")
            except:
                pass



def reject_join_request(chat_id, user_id, request_id):
    if request_id not in union_requests:
        send_message(chat_id, "❌ درخواست یافت نشد!")
        return
    request = union_requests[request_id]
    union_name = request.get("union_name")
    requester_id = request.get("user_id")
    union_info = unions_data.get(union_name)
    if union_info.get('owner') != user_id:
        send_message(chat_id, "❌ فقط لیدر اتحاد می‌تواند درخواست را رد کند!")
        return
    request["status"] = "rejected"
    db.update_union_request_status(request_id, "rejected")
    send_message(chat_id, f"❌ درخواست عضویت {request.get('user_name')} رد شد!")
    send_message(int(requester_id), f"❌ **درخواست عضویت شما در اتحاد {union_name} رد شد!**\n━━━━━━━━━━━━━━━━━━\nمی‌توانید بعداً دوباره درخواست دهید یا به اتحاد دیگری بپیوندید.")



def check_expired_requests():
    current_time = time.time()
    for req_id, request in union_requests.items():
        if request.get("status") == "pending" and current_time > request.get("expiry_time", 0):
            request["status"] = "expired"
            db.update_union_request_status(req_id, "expired")
            user_id = request.get("user_id")
            union_name = request.get("union_name")
            if user_id:
                try:
                    send_message(int(user_id), f"⏰ **درخواست عضویت شما در اتحاد {union_name} منقضی شد!**\n━━━━━━━━━━━━━━━━━━\nزمان 24 ساعت به اتمام رسید.\nبرای عضویت، دوباره درخواست دهید.")
                except:
                    pass
