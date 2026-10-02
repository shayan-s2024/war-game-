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
from .config import ATTACK_LIMIT, ATTACK_WINDOW, MAIN_ADMIN_ID
from .helpers import (generate_unique_code, get_country_continent, get_country_continent_key,
                      get_total_countries_count, is_admin, send_message, send_to_group,
                      show_screen, send_season_ended_notification, remove_reply_keyboard)
from .state import (assassination_info, cabinet_codes, db, donation_cooldown,
                    pending_deletions, pending_incomplete_deletions, players_data,
                    sanctions_data, unions_data, used_countries, user_attacks,
                    user_in_cabinet_setup, waiting_for_add_admin, waiting_for_add_credit,
                    waiting_for_add_virus, waiting_for_assassination_code,
                    waiting_for_attack_count, waiting_for_base_permission,
                    waiting_for_broadcast, waiting_for_buy_count, waiting_for_cabinet,
                    waiting_for_cabinet_manual, waiting_for_confirm_delete,
                    waiting_for_delete_all_economy, waiting_for_delete_economy_confirm,
                    waiting_for_delete_player, waiting_for_donation_amount,
                    waiting_for_edit_attack, waiting_for_edit_country,
                    waiting_for_edit_defense, waiting_for_edit_name,
                    waiting_for_edit_player, waiting_for_edit_population,
                    waiting_for_edit_score, waiting_for_fix_union_id,
                    waiting_for_give_item, waiting_for_global_reward_amount,
                    waiting_for_global_reward_type, waiting_for_hack_count,
                    waiting_for_item_count, waiting_for_remove_admin,
                    waiting_for_remove_credit, waiting_for_sanction_target,
                    waiting_for_union_join_request, waiting_for_war_time,
                    warning_sent_users)
from .static_data import (BUILDINGS, CABINET_OPTIONS, CONTINENT_NAMES, COUNTRIES_LIST,
                          ECONOMIC_ITEMS, MINES, VIRUSES)

# ==================== ماژول admin ====================


def admin_list_all_countries(chat_id, user_id):
    """نمایش لیست همه کشورهای موجود در بازی"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    all_countries = []
    for continent_key, continent_data in COUNTRIES_LIST.items():
        for country_name in continent_data.get("countries", {}).keys():
            all_countries.append(f"{continent_data['flag']} {country_name}")
    
    text = f"📋 **لیست همه کشورها ({len(all_countries)} عدد)**\n━━━━━━━━━━━━━━━━━━\n"
    text += "\n".join(all_countries[:30])
    if len(all_countries) > 30:
        text += f"\n... و {len(all_countries) - 30} کشور دیگر"
    
    send_message(chat_id, text)


# ==================== جستجوی کشور در سازمان ملل ====================

def un_search_country(chat_id, user_id):
    """جستجوی کشور برای تحریم"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    send_message(chat_id, "🔍 **نام کشور مورد نظر برای تحریم را وارد کنید:**\n\n(مثال: ایران، آمریکا، آلمان)")
    waiting_for_sanction_target[user_id] = True


def process_un_search_country(chat_id, user_id, country_name):
    """پردازش جستجوی کشور و نمایش نتایج"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    found_players = []
    for uid, data in players_data.items():
        if data.get("player_name") and data.get("country"):
            if country_name.lower() in data.get("country").lower():
                found_players.append({
                    "user_id": uid,
                    "name": data.get("player_name"),
                    "country": data.get("country"),
                    "continent": data.get("continent", "نامشخص"),
                    "credit": data.get("credit", 0),
                    "score": data.get("score", 0),
                    "union": data.get("union", "ندارد")
                })
    
    if not found_players:
        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت به سازمان ملل", "callback_data": "un_panel"}]]}
        send_message(chat_id, f"❌ **هیچ بازیکنی با کشور '{country_name}' یافت نشد!**\n\nلطفاً نام کشور را دقیق‌تر وارد کنید.", keyboard)
        return
    
    if len(found_players) == 1:
        target_id = found_players[0]["user_id"]
        select_sanction_type(chat_id, user_id, target_id)
        return
    
    text = f"🔍 **نتایج جستجوی '{country_name}'**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 {len(found_players)} بازیکن یافت شد:\n━━━━━━━━━━━━━━━━━━\n\n"
    
    keyboard = []
    for player in found_players[:20]:
        text += f"👤 **{player['name']}**\n"
        text += f"🌍 کشور: {player['country']}\n"
        text += f"🗺️ قاره: {player['continent']}\n"
        text += f"💰 سکه: {player['credit']:,} | 🏆 امتیاز: {player['score']}\n"
        text += f"🤝 اتحاد: {player['union']}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        keyboard.append([{"text": f"⚖️ تحریم {player['name']} - {player['country']}", "callback_data": f"un_sanction_select_{player['user_id']}"}])
    
    if len(found_players) > 20:
        text += f"\n... و {len(found_players) - 20} بازیکن دیگر"
    
    keyboard.append([{"text": "🔍 جستجوی مجدد", "callback_data": "un_search"}])
    keyboard.append([{"text": "🔙 بازگشت به سازمان ملل", "callback_data": "un_panel"}])
    
    send_message(chat_id, text, {"inline_keyboard": keyboard})


def un_select_sanction_from_search(chat_id, user_id, target_id):
    """انتخاب بازیکن از نتایج جستجو برای تحریم"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    select_sanction_type(chat_id, user_id, target_id)


def admin_delete_player_menu(chat_id, admin_id):
    """منوی حذف بازیکن - دریافت آیدی یا نام کشور (فقط ادمین)"""
    
    if not db.is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    text = """🗑 **حذف بازیکن**
━━━━━━━━━━━━━━━━━━
🔍 **روش‌های جستجو:**

1️⃣ **آیدی عددی** (مثال: `1429674818`)
2️⃣ **نام کشور** (مثال: `ایران`، `آمریکا`)
3️⃣ **نام بازیکن** (مثال: `رضا`)

━━━━━━━━━━━━━━━━━━
📝 لطفاً آیدی، نام کشور یا نام بازیکن را وارد کنید:

⚠️ **توجه:** این عمل غیرقابل بازگشت است!"""
    
    send_message(chat_id, text)
    waiting_for_delete_player[admin_id] = True


def admin_show_players_with_country_no_cabinet(chat_id, user_id):
    """نمایش بازیکنانی که کشور دارند اما کابینه ندارند"""
    if not is_admin(user_id):
        return
    
    players = []
    for uid, data in players_data.items():
        if data.get("player_name") and data.get("country") and not data.get("cabinet"):
            players.append(f"• {data.get('player_name')} - {data.get('country')} (🆔 {uid})")
    
    if players:
        text = "👥 **بازیکنان با کشور اما بدون کابینه:**\n━━━━━━━━━━━━━━━━━━\n" + "\n".join(players[:30])
        send_message(chat_id, text)
    else:
        send_message(chat_id, "✅ همه بازیکنان دارای کشور، کابینه هم دارند!")


def admin_attack_stats(chat_id, user_id):
    """نمایش آمار حملات کاربران (فقط ادمین)"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    active_users = 0
    total_attacks = 0
    users_with_limit = []
    
    for uid, timestamps in user_attacks.items():
        current_time = time.time()
        valid_ts = [ts for ts in timestamps if current_time - ts < ATTACK_WINDOW]
        
        if valid_ts:
            active_users += 1
            total_attacks += len(valid_ts)
            if len(valid_ts) >= ATTACK_LIMIT:
                player_name = players_data.get(uid, {}).get("player_name", "نامشخص")
                users_with_limit.append(f"• {player_name} (🆔 {uid}) - {len(valid_ts)} حمله")
    
    text = f"📊 **آمار حملات (24 ساعت گذشته)**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 کاربران فعال: {active_users}\n"
    text += f"⚔️ کل حملات: {total_attacks}\n"
    text += f"⛔ کاربران در محدودیت: {len(users_with_limit)}\n"
    text += f"📊 سقف مجاز: {ATTACK_LIMIT} حمله\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    
    if users_with_limit:
        text += f"\n**کاربران در محدودیت:**\n"
        text += "\n".join(users_with_limit[:10])
        if len(users_with_limit) > 10:
            text += f"\n... و {len(users_with_limit) - 10} نفر دیگر"
    
    send_message(chat_id, text)


def admin_send_smart_warning(chat_id, admin_id):
    """ارسال هشدار هوشمند به بازیکنان ناقص"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    send_message(chat_id, "🔄 در حال ارسال هشدار هوشمند...")
    
    incomplete_players = []
    for uid, data in players_data.items():
        if not data.get("player_name"):
            continue
        
        has_country = data.get("country") and data.get("country") != ""
        has_cabinet = data.get("cabinet") and len(data.get("cabinet", {})) == 5
        
        if not has_country or not has_cabinet:
            incomplete_players.append(uid)
    
    if not incomplete_players:
        send_message(chat_id, "✅ هیچ بازیکنی با اطلاعات ناقص وجود ندارد!")
        return
    
    warning_text = """⚠️ **هشدار مهم!** ⚠️
━━━━━━━━━━━━━━━━━━
اطلاعات شما **کامل نیست**!

❌ شما یا:
• کشور خود را انتخاب نکرده‌اید
• کابینه خود را کامل نکرده‌اید

━━━━━━━━━━━━━━━━━━
📌 **برای تکمیل اطلاعات، روی دکمه زیر کلیک کنید:**

⏰ **مهلت:** 48 ساعت

❗ اگر اطلاعات خود را کامل نکنید، **حساب شما حذف خواهد شد**!"""
    
    complete_keyboard = {"inline_keyboard": [[{"text": "🎮 تکمیل اطلاعات", "callback_data": "complete_info"}]]}
    
    sent_count = 0
    for uid in incomplete_players:
        try:
            send_message(int(uid), warning_text, complete_keyboard)
            warning_sent_users[uid] = time.time()
            sent_count += 1
            time.sleep(0.05)
        except:
            pass
    
    send_message(chat_id, f"✅ **هشدار هوشمند به {sent_count} بازیکن ارسال شد!**")


# ==================== پنل ادمین ====================
def send_admin_panel(chat_id, user_id):
    if not is_admin(user_id):
        show_screen(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    if state.war_active:
        war_status = "🟢 جنگ فعال است!"
    elif state.war_start_time and state.war_end_time and state.war_start_time <= time.time() <= state.war_end_time:
        war_status = "🟢 جنگ فعال (زمان‌بندی شده)"
    elif state.war_start_time and state.war_end_time and time.time() < state.war_start_time:
        remaining = int((state.war_start_time - time.time()) / 60)
        war_status = f"🟡 شروع در {remaining} دقیقه"
    else:
        war_status = "🔴 جنگ غیرفعال"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "👥 مدیریت بازیکنان", "callback_data": "admin_manage_players"}],
            [{"text": "🔍 بررسی وضعیت کشورها", "callback_data": "admin_check_country_status"}],
            [{"text": "📢 هشدار هوشمند", "callback_data": "admin_smart_warning"}],
            [{"text": "📊 آمار حملات", "callback_data": "admin_attack_stats"}],
            [{"text": "🔥 شروع فوری جنگ", "callback_data": "admin_start_war"}],
            [{"text": "🔴 پایان جنگ", "callback_data": "admin_end_war"}],
            [{"text": "📊 گزارش کامل بازیکنان", "callback_data": "admin_complete_report"}],
            [{"text": "📢 بیانیه همگانی", "callback_data": "admin_broadcast"}],
            [{"text": "⚠️ بازیکنان با اطلاعات ناقص", "callback_data": "admin_incomplete_players"}],
            [{"text": "🗑 حذف همه بازیکنان ناقص", "callback_data": "admin_delete_incomplete_all"}],
            [{"text": "⚔️ تنظیم زمان جنگ", "callback_data": "admin_war_time"}],
            [{"text": "📋 لیست همه کشورها", "callback_data": "admin_list_countries"}],
            [{"text": "🦠 اعطای ویروس", "callback_data": "admin_give_virus"}],
            [{"text": "👥 مدیریت ادمین", "callback_data": "admin_manage_admins"}],
            [{"text": "🔒 بستن ثبت‌نام", "callback_data": "admin_close_registration"}],
            [{"text": "🔓 باز کردن ثبت‌نام", "callback_data": "admin_open_registration"}],
            [{"text": "📊 وضعیت ثبت‌نام", "callback_data": "admin_registration_status"}],
            [{"text": "🗑 حذف بازیکن", "callback_data": "admin_delete_player"}],
            [{"text": "🏭 بازیکنان بدون اقتصاد", "callback_data": "admin_no_economy"}],
            [{"text": "🌍 بررسی کشورهای تکراری", "callback_data": "admin_duplicate_countries"}],
            [{"text": "🔍 بازیکنان بدون کشور", "callback_data": "admin_no_country"}],
            [{"text": "📊 آمار", "callback_data": "admin_stats"}],
            [{"text": "🌐 سازمان ملل", "callback_data": "un_panel"}],
            [{"text": "🎁 جایزه همگانی", "callback_data": "admin_global_reward"}],
            [{"text": "🎲 اختصاص کشور تصادفی", "callback_data": "admin_random_country"}],
            [{"text": "🔍 دیباگ پایگاه‌ها", "callback_data": "debug_bases"}],
            [{"text": "🗑 پاک کردن همه پایگاه‌ها", "callback_data": "clear_bases"}],
            [{"text": "🔐 تغییر کدهای همه بازیکنان", "callback_data": "admin_change_all_codes"}],
            [{"text": "🔧 رفع اتحاد نامعتبر", "callback_data": "admin_fix_union_menu"}],
            [{"text": "🏁 پایان فصل", "callback_data": "admin_end_season"}],
            [{"text": "🏆 برندگان فصل قبل", "callback_data": "admin_show_last_winners"}],
            [{"text": "🔙 بازگشت", "callback_data": "dashboard"}]
        ]
    }
    total_credit = sum(p.get('credit', 0) for p in players_data.values())
    text = f"👑 **پنل مدیریت**\n━━━━━━━━━━━━━━━━━━\n⚔️ وضعیت جنگ: {war_status}\n👥 بازیکنان: {len(players_data)}\n💰 مجموع سکه: {total_credit:,}"
    show_screen(chat_id, text, keyboard)


def admin_start_war(chat_id, user_id):
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    state.war_active = True
    state.war_start_time = None
    state.war_end_time = None
    db.set_game_config('war_active', '1')
    for uid in players_data.keys():
        try:
            send_message(int(uid), "🔥 **جنگ جهانی آغاز شد!** 🔥\n\nهمه کشورها آماده نبرد باشند!\n⚔️ به کشورهای دشمن حمله کنید و غنیمت بگیرید!")
        except:
            pass
        time.sleep(0.05)
    send_message(chat_id, "✅ **جنگ جهانی آغاز شد!**")
    send_admin_panel(chat_id, user_id)


def admin_end_war(chat_id, user_id):
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    state.war_active = False
    state.war_start_time = None
    state.war_end_time = None
    db.set_game_config('war_active', '0')
    db.delete_game_config_key('war_start_time')
    db.delete_game_config_key('war_end_time')
    for uid in players_data.keys():
        try:
            send_message(int(uid), "🕊️ **جنگ جهانی به پایان رسید!** 🕊️\n\nحالت صلح برقرار شد.")
        except:
            pass
        time.sleep(0.05)
    send_message(chat_id, "✅ **جنگ جهانی پایان یافت!**")
    send_admin_panel(chat_id, user_id)


def admin_broadcast(chat_id, user_id):
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    send_message(chat_id, "📢 **متن بیانیه را ارسال کن:**")
    waiting_for_broadcast[user_id] = True


def send_broadcast_to_all(message):
    success = 0
    for uid in players_data.keys():
        try:
            send_message(int(uid), f"📢 **بیانیه همگانی**\n\n{message}")
            success += 1
        except:
            pass
        time.sleep(0.05)
    
    group_message = f"""📢 **بیانیه همگانی از طرف سازمان ملل**
━━━━━━━━━━━━━━━━━━
📝 {message}
━━━━━━━━━━━━━━━━━━
🕐 {time.strftime('%Y/%m/%d - %H:%M')}
👑 ارسال شده به {success} بازیکن"""
    
    send_to_group(group_message)
    
    return success


def admin_set_war_time(chat_id, user_id):
    if not is_admin(user_id):
        return
    keyboard = {"inline_keyboard": [[{"text": "🔴 بستن جنگ", "callback_data": "admin_war_close"}], [{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]]}
    send_message(chat_id, "⚔️ **ساعت شروع و پایان (مثال: 20-22):**", keyboard)
    waiting_for_war_time[user_id] = True


def admin_give_virus(chat_id, user_id):
    if not is_admin(user_id):
        return
    players_list = "\n".join([f"🆔 {uid} | {data.get('player_name')}" for uid, data in players_data.items() if data.get("player_name")][:20])
    viruses_list = "\n".join([f"• {v['icon']} {v['name']}" for v in VIRUSES.values()])
    text = f"🦠 **اعطای ویروس**\n━━━━━━━━━━━━━━━━━━\n{players_list}\n━━━━━━━━━━━━━━━━━━\n{viruses_list}\n\nآیدی و نام ویروس (مثال: 123456789 corona):"
    send_message(chat_id, text)
    waiting_for_add_virus[user_id] = True


def process_give_virus(chat_id, user_id, target_id, virus_key):
    if virus_key not in VIRUSES:
        send_message(chat_id, "❌ ویروس نامعتبر!")
        return
    if target_id not in players_data:
        send_message(chat_id, "❌ کاربر یافت نشد!")
        return
    if "active_viruses" not in players_data[target_id]:
        players_data[target_id]["active_viruses"] = {}
    players_data[target_id]["active_viruses"][virus_key] = {
        "remaining_days": 5, "daily_loss": VIRUSES[virus_key]["daily_loss"],
        "damage_base": VIRUSES[virus_key]["damage_base"], "start_date": time.time()
    }
    db.save_player(target_id, players_data[target_id])
    send_message(chat_id, f"✅ ویروس {VIRUSES[virus_key]['name']} اعطا شد!")
    send_message(int(target_id), f"⚠️ ویروس {VIRUSES[virus_key]['name']} در کشور شما منتشر شد!")


def admin_manage_admins(chat_id, user_id):
    """پنل مدیریت ادمین‌ها (فقط ادمین اصلی)"""
    if user_id != MAIN_ADMIN_ID:
        send_message(chat_id, "⛔ فقط ادمین اصلی دسترسی دارد!")
        return
    
    admins = db.get_all_admins()
    
    text = "👑 **مدیریت ادمین‌ها**\n━━━━━━━━━━━━━━━━━━\n"
    for uid in admins:
        if uid == MAIN_ADMIN_ID:
            text += f"\n🆔 `{uid}`\n⭐ ادمین اصلی\n━━━━━━━━━━━━━━━━━━\n"
        else:
            text += f"\n🆔 `{uid}`\n━━━━━━━━━━━━━━━━━━\n"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "➕ افزودن ادمین", "callback_data": "admin_add_admin"}],
            [{"text": "➖ حذف ادمین", "callback_data": "admin_remove_admin"}],
            [{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]
        ]
    }
    send_message(chat_id, text, keyboard)


def admin_complete_players_report(chat_id, user_id):
    """گزارش کامل از وضعیت بازیکنان"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    total_players = 0
    players_without_country = []
    players_without_cabinet = []
    players_without_economy = []
    players_complete = []
    
    for uid, data in players_data.items():
        total_players += 1
        
        player_name = data.get("player_name")
        if not player_name:
            player_name = f"کاربر ناشناس ({uid[:8]}...)"
        
        has_country = data.get("country") and data.get("country") != ""
        
        cabinet = data.get("cabinet", {})
        has_cabinet = len(cabinet) == 5
        
        has_mine = any(data.get(f"{mine_key}_count", 0) > 0 for mine_key in MINES.keys())
        has_economic = any(data.get(f"{eco_key}_count", 0) > 0 for eco_key in ECONOMIC_ITEMS.keys())
        has_economy = has_mine or has_economic
        
        player_info = {
            "user_id": uid,
            "name": player_name,
            "country": data.get("country", "❌ ندارد"),
            "credit": data.get("credit", 0),
            "score": data.get("score", 0),
            "daily_profit": data.get("daily_profit", 0)
        }
        
        if not has_country:
            players_without_country.append(player_info)
        elif not has_cabinet:
            players_without_cabinet.append(player_info)
        elif not has_economy:
            players_without_economy.append(player_info)
        else:
            players_complete.append(player_info)
    
    text = f"📊 **گزارش کامل وضعیت بازیکنان**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 **کل بازیکنان:** {total_players}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    text += f"🔴 **بدون کشور:** {len(players_without_country)} نفر\n"
    text += f"🟠 **بدون کابینه:** {len(players_without_cabinet)} نفر\n"
    text += f"🟡 **بدون تجهیزات اقتصادی:** {len(players_without_economy)} نفر\n"
    text += f"🟢 **کامل:** {len(players_complete)} نفر\n"
    text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    total_incomplete = len(players_without_country) + len(players_without_cabinet) + len(players_without_economy)
    if total_incomplete > total_players:
        text += f"⚠️ **توجه:** برخی بازیکنان در چند دسته قرار دارند!\n"
        text += f"📌 بازیکنان بدون کشور = حتماً بدون کابینه و بدون اقتصاد هستند\n"
        text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    keyboard = []
    
    if players_without_country:
        keyboard.append([{"text": f"🌍 حذف {len(players_without_country)} بازیکن بدون کشور", "callback_data": "admin_delete_no_country"}])
    
    if players_without_cabinet:
        keyboard.append([{"text": f"👑 حذف {len(players_without_cabinet)} بازیکن بدون کابینه", "callback_data": "admin_delete_no_cabinet"}])
    
    if players_without_economy:
        keyboard.append([{"text": f"💰 حذف {len(players_without_economy)} بازیکن بدون اقتصاد", "callback_data": "admin_delete_all_economy"}])
    
    if players_without_country or players_without_cabinet or players_without_economy:
        keyboard.append([{"text": "🗑 حذف همه بازیکنان ناقص", "callback_data": "admin_delete_all_incomplete"}])
        keyboard.append([{"text": "📢 ارسال هشدار به همه", "callback_data": "admin_warning_all_incomplete"}])
    
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "admin_panel"}])
    
    send_message(chat_id, text, {"inline_keyboard": keyboard})


def admin_assign_random_country_to_players(chat_id, admin_id):
    """اختصاص کشور تصادفی به بازیکنانی که کشور ندارند"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    send_message(chat_id, "🔄 در حال بررسی بازیکنان بدون کشور...")
    
    players_without_country = []
    players_with_country_but_not_in_used = []
    
    for uid, data in players_data.items():
        if not data.get("player_name"):
            continue
        
        has_country_field = data.get("country") and data.get("country") != ""
        
        if not has_country_field:
            players_without_country.append(uid)
        else:
            country = data.get("country")
            if country not in used_countries:
                players_with_country_but_not_in_used.append((uid, country))
    
    report = f"📊 **وضعیت کشورها**\n━━━━━━━━━━━━━━━━━━\n"
    report += f"👥 بازیکنان بدون فیلد کشور: {len(players_without_country)}\n"
    report += f"⚠️ بازیکنان با کشور اما در used_countries نیست: {len(players_with_country_but_not_in_used)}\n"
    send_message(chat_id, report)
    
    for uid, country in players_with_country_but_not_in_used:
        used_countries[country] = uid
        db.save_country(country, uid)
        send_message(chat_id, f"✅ {players_data[uid].get('player_name')}: کشور {country} به used_countries اضافه شد.")
    
    if not players_without_country:
        if not players_with_country_but_not_in_used:
            send_message(chat_id, "✅ **همه بازیکنان کشور دارند!**")
        else:
            send_message(chat_id, f"✅ {len(players_with_country_but_not_in_used)} بازیکن به used_countries اضافه شدند.")
        return
    
    all_countries = []
    for continent_key, continent_data in COUNTRIES_LIST.items():
        for country_name in continent_data.get("countries", {}).keys():
            all_countries.append((country_name, continent_key, continent_data["name"]))
    
    used_countries_set = set(used_countries.keys())
    free_countries = [(c, cont_key, cont_name) for c, cont_key, cont_name in all_countries if c not in used_countries_set]
    
    if not free_countries:
        send_message(chat_id, "❌ **هیچ کشور آزادی وجود ندارد!**\nلطفاً ابتدا کشورهای جدید اضافه کنید یا بازیکنانی را حذف کنید.")
        return
    
    assigned = 0
    assigned_list = []
    
    for uid in players_without_country:
        if not free_countries:
            break
        
        country_name, continent_key, continent_name = random.choice(free_countries)
        free_countries.remove((country_name, continent_key, continent_name))
        
        players_data[uid]["country"] = country_name
        players_data[uid]["continent"] = continent_key
        used_countries[country_name] = uid
        
        db.save_player(uid, players_data[uid])
        db.save_country(country_name, uid)
        
        assigned += 1
        assigned_list.append({
            "uid": uid,
            "name": players_data[uid].get("player_name", "نامشخص"),
            "country": country_name,
            "continent": continent_name
        })
        
        try:
            send_message(int(uid), 
                f"🌍 **کشور به شما اختصاص داده شد!**\n━━━━━━━━━━━━━━━━━━\n"
                f"📍 کشور: {country_name}\n"
                f"🗺️ قاره: {continent_name}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✅ اکنون می‌توانید بازی را ادامه دهید.\n"
                f"برای تکمیل کابینه خود، روی /start کلیک کنید.")
        except:
            pass
    
    text = f"✅ **اختصاص کشور تصادفی انجام شد!**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 بازیکنان بدون کشور: {len(players_without_country)}\n"
    text += f"✅ کشور اختصاص یافته: {assigned}\n"
    text += f"📭 کشورهای آزاد باقیمانده: {len(free_countries)}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    if assigned_list:
        text += f"**لیست بازیکنانی که کشور گرفتند:**\n"
        for p in assigned_list[:15]:
            text += f"• {p['name']} → {p['country']} ({p['continent']})\n"
        if len(assigned_list) > 15:
            text += f"... و {len(assigned_list) - 15} نفر دیگر\n"
    
    send_message(chat_id, text)
    
    if assigned > 0:
        send_to_group(f"🌍 **{assigned} بازیکن بدون کشور، کشور تصادفی دریافت کردند.**")


def admin_close_registration(chat_id, user_id):
    """بستن ثبت‌نام جدید"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    from .registration import set_registration_closed
    set_registration_closed(True)
    
    total = get_total_countries_count()
    used = len(used_countries)
    
    send_message(chat_id, f"🔒 **ثبت‌نام جدید بسته شد!**\n━━━━━━━━━━━━━━━━━━\n📊 کشورهای پر شده: {used}/{total}\n💡 دیگر کسی نمی‌تواند ثبت‌نام کند.")


def admin_open_registration(chat_id, user_id):
    """باز کردن ثبت‌نام جدید"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    from .registration import set_registration_closed
    set_registration_closed(False)
    
    total = get_total_countries_count()
    used = len(used_countries)
    remaining = total - used
    
    send_message(chat_id, f"🔓 **ثبت‌نام جدید باز شد!**\n━━━━━━━━━━━━━━━━━━\n📊 کشورهای خالی: {remaining}/{total}\n✅ کاربران جدید می‌توانند ثبت‌نام کنند.")


def admin_registration_status(chat_id, user_id):
    """نمایش وضعیت ثبت‌نام"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    from .registration import is_registration_closed
    total = get_total_countries_count()
    used = len(used_countries)
    remaining = total - used
    
    status = "🔒 بسته" if is_registration_closed() else "🔓 باز"
    
    text = f"📊 **وضعیت ثبت‌نام**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"🔘 وضعیت: {status}\n"
    text += f"🌍 کل کشورها: {total}\n"
    text += f"✅ کشورهای پر شده: {used}\n"
    text += f"📭 کشورهای خالی: {remaining}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    
    if remaining == 0:
        text += f"⚠️ **همه کشورها پر شده‌اند!**\nثبت‌نامه باید بسته شود."
    elif remaining < 10:
        text += f"⚠️ فقط {remaining} کشور خالی باقی مانده!"
    
    send_message(chat_id, text)


def admin_add_admin(chat_id, user_id):
    if user_id != MAIN_ADMIN_ID:
        send_message(chat_id, "⛔ فقط ادمین اصلی!")
        return
    send_message(chat_id, "➕ **آیدی عددی ادمین جدید را ارسال کن:**")
    waiting_for_add_admin[user_id] = True


def admin_remove_admin(chat_id, user_id):
    if user_id != MAIN_ADMIN_ID:
        send_message(chat_id, "⛔ فقط ادمین اصلی!")
        return
    send_message(chat_id, "➖ **آیدی عددی ادمین برای حذف را ارسال کن:**")
    waiting_for_remove_admin[user_id] = True


def get_admin_stats(chat_id):
    total_credit = sum(p.get('credit', 0) for p in players_data.values())
    text = f"📊 **آمار کلی**\n━━━━━━━━━━━━━━━━━━\n👥 بازیکنان: {len(players_data)}\n💰 مجموع سکه: {total_credit:,}"
    keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]]}
    send_message(chat_id, text, keyboard)


def admin_change_all_codes(chat_id, user_id):
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    for uid in cabinet_codes:
        old_codes = cabinet_codes[uid].copy()
        for key in old_codes.keys():
            new_code = generate_unique_code()
            cabinet_codes[uid][key] = new_code
            db.save_cabinet_code(uid, key, new_code)
    for uid in cabinet_codes:
        try:
            codes_text = "🔐 **کدهای امنیتی کابینه شما تغییر کرد!**\n━━━━━━━━━━━━━━━━━━\n"
            codes_text += "⚠️ کدهای جدید شما:\n━━━━━━━━━━━━━━━━━━\n"
            for key, code in cabinet_codes[uid].items():
                cabinet_name = CABINET_OPTIONS.get(key, {}).get("name", key)
                icon = CABINET_OPTIONS.get(key, {}).get("icon", "🔑")
                member_name = players_data.get(uid, {}).get("cabinet", {}).get(key, "نامشخص")
                codes_text += f"\n{icon} {cabinet_name}\n"
                codes_text += f"🔑 کد جدید: `{code}`\n"
                codes_text += f"👤 {member_name}\n━━━━━━━━━━━━━━━━━━\n"
            codes_text += "\n💡 کدهای قدیمی شما دیگر معتبر نیستند!"
            send_message(int(uid), codes_text)
        except:
            pass
    send_message(chat_id, f"✅ کدهای امنیتی {len(cabinet_codes)} بازیکن تغییر کرد!")


def admin_check_country_status(chat_id, admin_id):
    """بررسی کامل وضعیت کشورهای بازیکنان"""
    if not is_admin(admin_id):
        return
    
    players_without_country = 0
    players_with_country = 0
    country_in_used = 0
    country_not_in_used = 0
    
    for uid, data in players_data.items():
        if not data.get("player_name"):
            continue
        
        if data.get("country"):
            players_with_country += 1
            if data.get("country") in used_countries:
                country_in_used += 1
            else:
                country_not_in_used += 1
        else:
            players_without_country += 1
    
    text = f"📊 **وضعیت کشورها**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 بازیکنان با کشور: {players_with_country}\n"
    text += f"   ✅ در used_countries: {country_in_used}\n"
    text += f"   ❌ خارج از used_countries: {country_not_in_used}\n"
    text += f"👥 بازیکنان بدون کشور: {players_without_country}\n"
    text += f"🌍 کل کشورهای used_countries: {len(used_countries)}\n"
    
    send_message(chat_id, text)


def admin_delete_player(chat_id, admin_id, target_id):
    """حذف کامل یک بازیکن از بازی"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    if target_id not in players_data:
        send_message(chat_id, f"❌ بازیکن با آیدی {target_id} یافت نشد!")
        return
    
    player_data = players_data[target_id]
    player_name = player_data.get("player_name", "نامشخص")
    player_country = player_data.get("country")
    
    user_union = player_data.get("union")
    if user_union and user_union in unions_data:
        union_info = unions_data[user_union]
        if target_id in union_info.get("members", []):
            union_info["members"].remove(target_id)
            if union_info.get("owner") == target_id:
                if union_info.get("members"):
                    new_owner = union_info["members"][0]
                    union_info["owner"] = new_owner
                    union_info["owner_name"] = players_data[new_owner].get("player_name", "نامشخص")
                    send_message(int(new_owner), f"👑 شما لیدر جدید اتحاد {user_union} شدید!")
                else:
                    del unions_data[user_union]
                    db.delete_union(user_union)
            else:
                db.save_union(user_union, union_info)
    
    if player_country and player_country in used_countries:
        del used_countries[player_country]
        db.remove_country(player_country)
    
    if target_id in cabinet_codes:
        for key in list(cabinet_codes[target_id].keys()):
            db.delete_cabinet_code(target_id, key)
        del cabinet_codes[target_id]
    
    db.delete_player(target_id)
    del players_data[target_id]
    
    for dict_obj in [waiting_for_buy_count, waiting_for_donation_amount, waiting_for_attack_count,
                     waiting_for_assassination_code, waiting_for_hack_count, waiting_for_edit_player,
                     waiting_for_add_credit, waiting_for_remove_credit, waiting_for_edit_defense,
                     waiting_for_edit_attack, waiting_for_edit_score, waiting_for_edit_population,
                     waiting_for_edit_country, waiting_for_edit_name, waiting_for_give_item]:
        if target_id in dict_obj:
            del dict_obj[target_id]
    
    send_message(chat_id, f"✅ **بازیکن حذف شد!**\n━━━━━━━━━━━━━━━━━━\n👤 نام: {player_name}\n🌍 کشور: {player_country if player_country else 'ندارد'}\n🆔 آیدی: {target_id}")
    send_to_group(f"🗑 **حذف حساب کاربری**\n━━━━━━━━━━━━━━━━━━\n👤 {player_name} از بازی حذف شد.\n🌍 کشور {player_country if player_country else 'نامشخص'} آزاد شد.")


def show_delete_confirmation(chat_id, admin_id, player):
    """نمایش اطلاعات بازیکن و درخواست تایید حذف"""
    
    if not db.is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    created_at = player.get('created_at', 0)
    if created_at:
        days_old = int((time.time() - created_at) / 86400)
        age_text = f"{days_old} روز" if days_old > 0 else "کمتر از یک روز"
    else:
        age_text = "نامشخص"
    
    text = f"""⚠️ **تایید حذف بازیکن** ⚠️
━━━━━━━━━━━━━━━━━━
👤 **نام:** {player['name']}
🆔 **آیدی:** `{player['user_id']}`
🌍 **کشور:** {player['country']}
💰 **سکه:** {player['credit']:,}
🏆 **امتیاز:** {player['score']}
🤝 **اتحاد:** {player['union']}
📈 **سود روزانه:** {player['daily_profit']:,}
🛡 **استقامت:** {player['defense']:,}
💥 **قدرت تخریب:** {player['attack_power']:,}
📅 **سن حساب:** {age_text}
━━━━━━━━━━━━━━━━━━
❗ **آیا از حذف این بازیکن اطمینان دارید؟**

برای تایید عدد **۱** را وارد کنید:
برای انصراف هر عدد دیگری وارد کنید:"""
    
    waiting_for_confirm_delete[admin_id] = player['user_id']
    
    send_message(chat_id, text)


def execute_player_deletion(chat_id, admin_id, target_id):
    """اجرای عملیات حذف بازیکن"""
    
    player_data = players_data[target_id]
    player_name = player_data.get("player_name", "نامشخص")
    player_country = player_data.get("country")
    player_union = player_data.get("union")
    
    # ========== 1. حذف از اتحاد ==========
    if player_union and player_union in unions_data:
        union_info = unions_data[player_union]
        if target_id in union_info.get("members", []):
            union_info["members"].remove(target_id)
            
            if union_info.get("owner") == target_id:
                if union_info.get("members"):
                    new_owner = union_info["members"][0]
                    union_info["owner"] = new_owner
                    union_info["owner_name"] = players_data[new_owner].get("player_name", "نامشخص")
                    send_message(int(new_owner), f"👑 **شما لیدر جدید اتحاد {player_union} شدید!**")
                else:
                    del unions_data[player_union]
                    db.delete_union(player_union)
                    player_union = None
            
            if player_union and player_union in unions_data:
                db.save_union(player_union, unions_data[player_union])
    
    # ========== 2. آزاد کردن کشور ==========
    if player_country and player_country in used_countries:
        if used_countries.get(player_country) == target_id:
            del used_countries[player_country]
            db.remove_country(player_country)
    
    # ========== 3. حذف کدهای کابینه ==========
    if target_id in cabinet_codes:
        for key in list(cabinet_codes[target_id].keys()):
            db.delete_cabinet_code(target_id, key)
        del cabinet_codes[target_id]
    
    # ========== 4. حذف اطلاعات ترور و هک ==========
    if target_id in assassination_info:
        del assassination_info[target_id]
    
    for uid in list(assassination_info.keys()):
        keys_to_delete = []
        for key, info in assassination_info[uid].items():
            if info.get("target_id") == target_id:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del assassination_info[uid][key]
    
    # ========== 5. حذف از لیست‌های انتظار ==========
    waiting_dicts = [
        waiting_for_buy_count, waiting_for_donation_amount, waiting_for_attack_count,
        waiting_for_assassination_code, waiting_for_hack_count, waiting_for_edit_player,
        waiting_for_add_credit, waiting_for_remove_credit, waiting_for_edit_defense,
        waiting_for_edit_attack, waiting_for_edit_score, waiting_for_edit_population,
        waiting_for_edit_country, waiting_for_edit_name, waiting_for_give_item,
        waiting_for_item_count, waiting_for_global_reward_type, waiting_for_global_reward_amount,
        warning_sent_users, waiting_for_warning_response, donation_cooldown,
        waiting_for_base_permission, user_in_cabinet_setup, waiting_for_cabinet,
        waiting_for_cabinet_manual, waiting_for_union_join_request, waiting_for_delete_player,
        waiting_for_confirm_delete, waiting_for_delete_economy_confirm, waiting_for_delete_all_economy,
        waiting_for_fix_union_id, user_attacks
    ]
    
    for dict_obj in waiting_dicts:
        if target_id in dict_obj:
            del dict_obj[target_id]
    
    # ========== 6. حذف از دیتابیس ==========
    db.delete_player(target_id)
    
    # ========== 7. حذف از حافظه ==========
    del players_data[target_id]
    
    # ========== 8. ارسال گزارش ==========
    if admin_id == MAIN_ADMIN_ID:
        level_name = "اصلی"
    else:
        level_name = "ادمین"
    
    send_message(chat_id, 
        f"✅ **بازیکن حذف شد!**\n━━━━━━━━━━━━━━━━━━\n"
        f"👤 نام: {player_name}\n"
        f"🌍 کشور: {player_country if player_country else 'ندارد'}\n"
        f"🆔 آیدی: {target_id}\n"
        f"👑 حذف شده توسط: {level_name}\n"
        f"🕐 {time.strftime('%Y/%m/%d %H:%M:%S')}")
    
    send_to_group(f"🗑 **حذف حساب کاربری**\n━━━━━━━━━━━━━━━━━━\n"
                  f"👤 {player_name} از بازی حذف شد.\n"
                  f"🌍 کشور {player_country if player_country else 'نامشخص'} آزاد شد.\n"
                  f"👑 توسط: {level_name}")
    
    try:
        send_message(int(target_id), 
            f"⚠️ **حساب کاربری شما حذف شد!**\n━━━━━━━━━━━━━━━━━━\n"
            f"👤 {player_name}\n"
            f"🕐 {time.strftime('%Y/%m/%d %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📞 در صورت اعتراض با پشتیبانی تماس بگیرید.")
    except:
        pass
    
    send_admin_panel(chat_id, admin_id)


def admin_find_incomplete_players(chat_id, user_id):
    """نمایش بازیکنانی که اطلاعات ناقص دارند"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    incomplete_players = []
    
    for uid, data in players_data.items():
        if not data.get("player_name"):
            continue
        
        has_country = data.get("country") and data.get("country") != ""
        has_cabinet = data.get("cabinet") and len(data.get("cabinet", {})) == 5
        
        is_incomplete = not has_country or not has_cabinet
        
        if is_incomplete:
            incomplete_players.append({
                "user_id": uid,
                "name": data.get("player_name"),
                "country": data.get("country", "❌ ندارد"),
                "cabinet_status": "✅ کامل" if has_cabinet else "❌ ناقص",
                "credit": data.get("credit", 0),
                "warning_sent": uid in warning_sent_users
            })
    
    if not incomplete_players:
        send_message(chat_id, "✅ **همه بازیکنان اطلاعات کامل دارند!**")
        return
    
    total = len(incomplete_players)
    total_players = len([p for p in players_data.values() if p.get("player_name")])
    
    text = f"⚠️ **بازیکنان با اطلاعات ناقص**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 کل بازیکنان: {total_players}\n"
    text += f"📊 اطلاعات ناقص: {total}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    keyboard = []
    
    for i, p in enumerate(incomplete_players[:20], 1):
        text += f"{i}. 👤 **{p['name']}**\n"
        text += f"   🆔 `{p['user_id']}`\n"
        text += f"   🌍 کشور: {p['country']}\n"
        text += f"   📋 کابینه: {p['cabinet_status']}\n"
        text += f"   💰 {p['credit']:,} سکه\n"
        warning_icon = "⚠️" if p['warning_sent'] else "🔴"
        text += f"   {warning_icon} هشدار: {'ارسال شده' if p['warning_sent'] else 'ارسال نشده'}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        
        keyboard.append([{"text": f"🗑 حذف {p['name']}", "callback_data": f"admin_delete_incomplete_{p['user_id']}"}])
    
    if len(incomplete_players) > 20:
        text += f"\n... و {len(incomplete_players) - 20} بازیکن دیگر"
    
    keyboard.append([{"text": "📢 ارسال هشدار به همه", "callback_data": "admin_warning_all_incomplete"}])
    keyboard.append([{"text": "🗑 حذف همه اطلاعات ناقص", "callback_data": "admin_delete_all_incomplete"}])
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "admin_panel"}])
    
    send_message(chat_id, text, {"inline_keyboard": keyboard})


def admin_send_warning_to_all_incomplete(chat_id, admin_id):
    """ارسال هشدار به همه بازیکنانی که اطلاعات ناقص دارند"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    send_message(chat_id, "🔄 در حال ارسال هشدار به بازیکنان با اطلاعات ناقص...")
    
    incomplete_players = []
    for uid, data in players_data.items():
        if not data.get("player_name"):
            continue
        
        has_country = data.get("country") and data.get("country") != ""
        has_cabinet = data.get("cabinet") and len(data.get("cabinet", {})) == 5
        
        if not has_country or not has_cabinet:
            incomplete_players.append(uid)
    
    if not incomplete_players:
        send_message(chat_id, "✅ هیچ بازیکنی با اطلاعات ناقص وجود ندارد!")
        return
    
    warning_text = """⚠️ **هشدار مهم!** ⚠️
━━━━━━━━━━━━━━━━━━
اطلاعات کشور یا کابینه شما **کامل نیست**!

❌ شما یا:
• کشور خود را انتخاب نکرده‌اید
• کابینه خود را کامل نکرده‌اید

━━━━━━━━━━━━━━━━━━
📌 **برای تکمیل اطلاعات، مراحل زیر را انجام دهید:**

1️⃣ روی دکمه **/start** کلیک کنید
2️⃣ کشور خود را انتخاب کنید
3️⃣ کابینه خود را کامل کنید (5 مقام)

━━━━━━━━━━━━━━━━━━
⏰ **مهلت:** 48 ساعت

❗ اگر اطلاعات خود را کامل نکنید، **حساب شما حذف خواهد شد**!

برای شروع اینجا کلیک کنید 👇"""
    
    start_keyboard = {"inline_keyboard": [[{"text": "🎮 شروع و تکمیل اطلاعات", "callback_data": "start_game"}]]}
    
    sent_count = 0
    failed_count = 0
    
    for uid in incomplete_players:
        try:
            send_message(int(uid), warning_text, start_keyboard)
            warning_sent_users[uid] = time.time()
            sent_count += 1
            time.sleep(0.05)
        except Exception as e:
            print(f"ERROR sending to {uid}: {e}")
            failed_count += 1
    
    result = f"✅ **هشدار ارسال شد!**\n━━━━━━━━━━━━━━━━━━\n📨 ارسال شده: {sent_count} بازیکن\n❌ ناموفق: {failed_count} بازیکن\n⏰ مهلت تکمیل اطلاعات: 48 ساعت"
    send_message(chat_id, result)
    
    send_to_group(f"📢 **هشدار به بازیکنان با اطلاعات ناقص**\n━━━━━━━━━━━━━━━━━━\n📨 {sent_count} بازیکن هشدار دریافت کردند.\n⏰ 48 ساعت فرصت دارند اطلاعات خود را کامل کنند.")


def admin_delete_incomplete_player(chat_id, admin_id, target_id):
    """حذف یک بازیکن با اطلاعات ناقص"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    if target_id not in players_data:
        send_message(chat_id, "❌ بازیکن یافت نشد!")
        return
    
    player_data = players_data[target_id]
    player_name = player_data.get("player_name", "نامشخص")
    player_country = player_data.get("country")
    
    user_union = player_data.get("union")
    if user_union and user_union in unions_data:
        union_info = unions_data[user_union]
        if target_id in union_info.get("members", []):
            union_info["members"].remove(target_id)
            if union_info.get("owner") == target_id and union_info.get("members"):
                new_owner = union_info["members"][0]
                union_info["owner"] = new_owner
                union_info["owner_name"] = players_data[new_owner].get("player_name", "نامشخص")
            db.save_union(user_union, union_info)
    
    if player_country and player_country in used_countries:
        if used_countries.get(player_country) == target_id:
            del used_countries[player_country]
            db.remove_country(player_country)
    
    db.delete_player(target_id)
    del players_data[target_id]
    
    warning_sent_users.pop(target_id, None)
    
    send_message(chat_id, f"✅ **بازیکن {player_name} حذف شد!**")
    send_to_group(f"🗑 **بازیکن {player_name} به دلیل اطلاعات ناقص حذف شد.**")


def admin_delete_all_incomplete_players(chat_id, admin_id):
    """حذف همه بازیکنانی که اطلاعات ناقص دارند"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    to_delete = []
    for uid, data in players_data.items():
        if not data.get("player_name"):
            continue
        
        has_country = data.get("country") and data.get("country") != ""
        has_cabinet = data.get("cabinet") and len(data.get("cabinet", {})) == 5
        
        if not has_country or not has_cabinet:
            to_delete.append(uid)
    
    if not to_delete:
        send_message(chat_id, "✅ هیچ بازیکنی با اطلاعات ناقص وجود ندارد!")
        return
    
    confirm_id = str(random.randint(100000, 999999))
    pending_incomplete_deletions[confirm_id] = {
        "admin_id": admin_id,
        "chat_id": chat_id,
        "players": to_delete
    }
    
    text = f"⚠️ **هشدار!**\n━━━━━━━━━━━━━━━━━━\n🗑 تعداد بازیکنان با اطلاعات ناقص: {len(to_delete)}\n\n❗ آیا از حذف همه این بازیکنان اطمینان دارید؟\nاین عمل غیرقابل بازگشت است!"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": f"✅ بله، {len(to_delete)} بازیکن حذف شوند", "callback_data": f"confirm_incomplete_delete_{confirm_id}"}],
            [{"text": "❌ انصراف", "callback_data": "admin_panel"}]
        ]
    }
    
    send_message(chat_id, text, keyboard)


def process_incomplete_delete_callback(chat_id, admin_id, confirm_id):
    """پردازش تایید حذف بازیکنان ناقص"""
    if confirm_id not in pending_incomplete_deletions:
        send_message(chat_id, "❌ درخواست منقضی شده است!")
        return
    
    data = pending_incomplete_deletions.pop(confirm_id)
    
    if data["admin_id"] != admin_id:
        send_message(chat_id, "❌ دسترسی غیرمجاز!")
        return
    
    to_delete = data["players"]
    
    send_message(chat_id, f"🔄 در حال حذف {len(to_delete)} بازیکن...")
    
    deleted = 0
    for uid in to_delete:
        try:
            if uid not in players_data:
                continue
            
            player_data = players_data[uid]
            player_country = player_data.get("country")
            
            user_union = player_data.get("union")
            if user_union and user_union in unions_data:
                union_info = unions_data[user_union]
                if uid in union_info.get("members", []):
                    union_info["members"].remove(uid)
                    db.save_union(user_union, union_info)
            
            if player_country and player_country in used_countries:
                if used_countries.get(player_country) == uid:
                    del used_countries[player_country]
                    db.remove_country(player_country)
            
            db.delete_player(uid)
            del players_data[uid]
            warning_sent_users.pop(uid, None)
            deleted += 1
            
        except Exception as e:
            print(f"ERROR deleting {uid}: {e}")
    
    send_message(chat_id, f"✅ **{deleted} بازیکن با اطلاعات ناقص حذف شدند!**")
    
    if deleted > 0:
        send_to_group(f"🗑 **{deleted} بازیکن به دلیل اطلاعات ناقص حذف شدند.**")


def admin_search_delete_player(chat_id, admin_id, search_text):
    """جستجو و نمایش بازیکن برای حذف"""
    
    if not db.is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    search_text = search_text.strip()
    found_players = []
    
    if search_text.isdigit():
        if search_text in players_data:
            player_data = players_data[search_text]
            if player_data.get("player_name"):
                found_players.append({
                    "user_id": search_text,
                    "name": player_data.get("player_name"),
                    "country": player_data.get("country", "نامشخص"),
                    "credit": player_data.get("credit", 0),
                    "score": player_data.get("score", 0),
                    "union": player_data.get("union", "ندارد"),
                    "daily_profit": player_data.get("daily_profit", 0),
                    "defense": player_data.get("defense", 0),
                    "attack_power": player_data.get("attack_power", 0),
                    "created_at": player_data.get("created_at", 0)
                })
    
    if not found_players:
        for uid, data in players_data.items():
            if data.get("player_name"):
                country = data.get("country", "")
                if country and search_text.lower() == country.lower():
                    found_players.append({
                        "user_id": uid,
                        "name": data.get("player_name"),
                        "country": country,
                        "credit": data.get("credit", 0),
                        "score": data.get("score", 0),
                        "union": data.get("union", "ندارد"),
                        "daily_profit": data.get("daily_profit", 0),
                        "defense": data.get("defense", 0),
                        "attack_power": data.get("attack_power", 0),
                        "created_at": data.get("created_at", 0)
                    })
    
    if not found_players:
        for uid, data in players_data.items():
            if data.get("player_name"):
                player_name = data.get("player_name", "")
                if search_text.lower() in player_name.lower():
                    found_players.append({
                        "user_id": uid,
                        "name": player_name,
                        "country": data.get("country", "نامشخص"),
                        "credit": data.get("credit", 0),
                        "score": data.get("score", 0),
                        "union": data.get("union", "ندارد"),
                        "daily_profit": data.get("daily_profit", 0),
                        "defense": data.get("defense", 0),
                        "attack_power": data.get("attack_power", 0),
                        "created_at": data.get("created_at", 0)
                    })
    
    if not found_players:
        for uid, data in players_data.items():
            if data.get("player_name"):
                country = data.get("country", "")
                if country and search_text.lower() in country.lower():
                    found_players.append({
                        "user_id": uid,
                        "name": data.get("player_name"),
                        "country": country,
                        "credit": data.get("credit", 0),
                        "score": data.get("score", 0),
                        "union": data.get("union", "ندارد"),
                        "daily_profit": data.get("daily_profit", 0),
                        "defense": data.get("defense", 0),
                        "attack_power": data.get("attack_power", 0),
                        "created_at": data.get("created_at", 0)
                    })
    
    if not found_players:
        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت به پنل ادمین", "callback_data": "admin_panel"}]]}
        send_message(chat_id, f"❌ **بازیکنی با مشخصات '{search_text}' یافت نشد!**\n\n📌 لطفاً آیدی عددی، نام کشور یا نام بازیکن را دقیق‌تر وارد کنید.", keyboard)
        return
    
    if len(found_players) == 1:
        player = found_players[0]
        show_delete_confirmation(chat_id, admin_id, player)
    else:
        text = f"🔍 **نتایج جستجوی '{search_text}'**\n━━━━━━━━━━━━━━━━━━\n"
        text += f"📊 {len(found_players)} بازیکن یافت شد:\n━━━━━━━━━━━━━━━━━━\n\n"
        
        keyboard = []
        for player in found_players[:15]:
            status = "🟢" if player['daily_profit'] > 0 else "⚪"
            
            text += f"{status} 👤 **{player['name']}**\n"
            text += f"   🆔 `{player['user_id']}`\n"
            text += f"   🌍 {player['country']}\n"
            text += f"   💰 {player['credit']:,} سکه | 🏆 {player['score']} امتیاز\n"
            text += f"   🤝 اتحاد: {player['union']}\n"
            text += f"━━━━━━━━━━━━━━━━━━\n"
            
            keyboard.append([{"text": f"🗑 حذف {player['name']}", "callback_data": f"admin_delete_confirm_{player['user_id']}"}])
        
        if len(found_players) > 15:
            text += f"\n... و {len(found_players) - 15} بازیکن دیگر"
        
        keyboard.append([{"text": "🔍 جستجوی مجدد", "callback_data": "admin_delete_player"}])
        keyboard.append([{"text": "🔙 بازگشت به پنل ادمین", "callback_data": "admin_panel"}])
        
        send_message(chat_id, text, {"inline_keyboard": keyboard})


def process_delete_confirm(chat_id, admin_id, text):
    """تایید نهایی حذف بازیکن"""
    
    if not db.is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    if admin_id not in waiting_for_confirm_delete:
        send_message(chat_id, "❌ درخواست نامعتبر! لطفاً دوباره از منوی حذف بازیکن اقدام کنید.")
        return
    
    text_normalized = text.strip()
    persian_numbers = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
    for persian, latin in persian_numbers.items():
        text_normalized = text_normalized.replace(persian, latin)
    
    if text_normalized != "1":
        waiting_for_confirm_delete.pop(admin_id, None)
        send_message(chat_id, "❌ عملیات حذف لغو شد.")
        return
    
    target_id = waiting_for_confirm_delete.pop(admin_id)
    
    if target_id not in players_data:
        send_message(chat_id, "❌ بازیکن یافت نشد!")
        return
    
    if target_id == MAIN_ADMIN_ID:
        send_message(chat_id, "❌ نمی‌توانید ادمین اصلی را حذف کنید!")
        return
    
    execute_player_deletion(chat_id, admin_id, target_id)


# ==================== جایزه همگانی ====================
def admin_global_reward_menu(chat_id, user_id):
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    keyboard = {
        "inline_keyboard": [
            [{"text": "💰 سکه", "callback_data": "global_reward_credit"}],
            [{"text": "🛡 استقامت", "callback_data": "global_reward_defense"}],
            [{"text": "💥 قدرت تخریب", "callback_data": "global_reward_attack"}],
            [{"text": "🏆 امتیاز", "callback_data": "global_reward_score"}],
            [{"text": "👥 جمعیت", "callback_data": "global_reward_population"}],
            [{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]
        ]
    }
    send_message(chat_id, "🎁 **پنل جایزه همگانی**\n━━━━━━━━━━━━━━━━━━\nنوع جایزه را انتخاب کنید:", keyboard)


def process_global_reward(chat_id, user_id, reward_type, amount):
    if not is_admin(user_id):
        return
    try:
        amount = int(amount)
        if amount <= 0:
            send_message(chat_id, "❌ مقدار باید بیشتر از 0 باشد!")
            return
        success_count = 0
        fail_count = 0
        for uid, player_data in players_data.items():
            if not player_data.get("player_name"):
                continue
            try:
                if reward_type == "credit":
                    players_data[uid]["credit"] = player_data.get("credit", 0) + amount
                    reward_name = "سکه"
                elif reward_type == "defense":
                    players_data[uid]["defense"] = player_data.get("defense", 5000) + amount
                    reward_name = "استقامت"
                elif reward_type == "attack":
                    players_data[uid]["attack_power"] = player_data.get("attack_power", 0) + amount
                    reward_name = "قدرت تخریب"
                elif reward_type == "score":
                    players_data[uid]["score"] = player_data.get("score", 0) + amount
                    reward_name = "امتیاز"
                elif reward_type == "population":
                    players_data[uid]["population"] = player_data.get("population", 10000) + amount
                    reward_name = "جمعیت"
                else:
                    send_message(chat_id, "❌ نوع جایزه نامعتبر!")
                    return
                db.save_player(uid, players_data[uid])
                success_count += 1
                try:
                    send_message(int(uid), f"🎁 **جایزه همگانی!**\n━━━━━━━━━━━━━━━━━━\n🎉 {reward_name}: +{amount:,}\n👑 به همه بازیکنان اعطا شد!\n🕐 {time.strftime('%Y/%m/%d - %H:%M')}")
                except:
                    pass
                time.sleep(0.05)
            except Exception as e:
                fail_count += 1
                print(f"خطا در اعطا به {uid}: {e}")
        report = f"✅ **جایزه همگانی اعطا شد!**\n━━━━━━━━━━━━━━━━━━\n🎁 نوع: {reward_name}\n💰 مقدار: {amount:,}\n✅ موفق: {success_count} بازیکن\n❌ ناموفق: {fail_count} بازیکن\n━━━━━━━━━━━━━━━━━━\n👑 توسط ادمین: {user_id}"
        send_message(chat_id, report)
        group_msg = f"🎁 **جایزه همگانی از طرف ادمین!**\n━━━━━━━━━━━━━━━━━━\n🎉 {reward_name}: +{amount:,}\n👥 به همه {success_count} بازیکن فعال اعطا شد!"
        send_to_group(group_msg)
    except ValueError:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")


def admin_global_reward_amount(chat_id, user_id, reward_type):
    waiting_for_global_reward_type[user_id] = reward_type
    send_message(chat_id, f"💰 **مقدار جایزه را وارد کنید:**\n\n(عدد مثبت)")


# ==================== پنل مدیریت بازیکنان برای ادمین ====================
def admin_manage_players(chat_id, user_id):
    if not is_admin(user_id):
        show_screen(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    text = """👑 **مدیریت بازیکنان**
━━━━━━━━━━━━━━━━━━
🔍 **روش‌های جستجو:**

1️⃣ **آیدی عددی** (مثال: `1429674818`)
2️⃣ **نام کشور** (مثال: `ایران`، `آمریکا`)

━━━━━━━━━━━━━━━━━━
📝 لطفاً آیدی عددی یا نام کشور بازیکن را وارد کنید:

(مثال: 1429674818 یا ایران)"""
    
    show_screen(chat_id, text)
    waiting_for_edit_player[user_id] = True


def show_player_edit_menu(chat_id, user_id, target_id):
    if not is_admin(user_id):
        show_screen(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    target = players_data.get(target_id, {})
    if not target.get("player_name"):
        show_screen(chat_id, "❌ بازیکن یافت نشد!")
        return
    cabinet = target.get("cabinet", {})
    text = f"""👤 **ویرایش بازیکن**
━━━━━━━━━━━━━━━━━━
🆔 آیدی: `{target_id}`
👤 نام: {target.get('player_name')}
🌍 کشور: {target.get('country', 'نامشخص')}
🗺️ قاره: {target.get('continent', 'نامشخص')}

📊 **آمارها**
━━━━━━━━━━━━━━━━━━
💰 سکه: {target.get('credit', 0):,}
🛡 استقامت: {target.get('defense', 5000):,}
💥 قدرت تخریب: {target.get('attack_power', 0):,}
🏆 امتیاز: {target.get('score', 0)}
👥 جمعیت: {target.get('population', 10000):,}
📈 سود روزانه: {target.get('daily_profit', 0):,}

👑 **کابینه**
━━━━━━━━━━━━━━━━━━
🤝 دیپلمات: {cabinet.get('diplomat', '❌')}
👑 رهبر: {cabinet.get('leader', '❌')}
🛡️ دفاع: {cabinet.get('defense', '❌')}
💰 اقتصاد: {cabinet.get('economy', '❌')}
🕵️ اطلاعات: {cabinet.get('intelligence', '❌')}

🤝 **اتحاد**
━━━━━━━━━━━━━━━━━━
🎮 اتحاد: {target.get('union', '❌')}
📋 تعداد دعوت: {target.get('invite_count', 0)}"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "💰 افزایش سکه", "callback_data": f"admin_add_credit_{target_id}"}],
            [{"text": "💸 کاهش سکه", "callback_data": f"admin_remove_credit_{target_id}"}],
            [{"text": "🛡 تغییر استقامت", "callback_data": f"admin_edit_defense_{target_id}"}],
            [{"text": "💥 تغییر قدرت تخریب", "callback_data": f"admin_edit_attack_{target_id}"}],
            [{"text": "🏆 تغییر امتیاز", "callback_data": f"admin_edit_score_{target_id}"}],
            [{"text": "👥 تغییر جمعیت", "callback_data": f"admin_edit_population_{target_id}"}],
            [{"text": "🌍 تغییر کشور", "callback_data": f"admin_edit_country_{target_id}"}],
            [{"text": "✏️ تغییر نام", "callback_data": f"admin_edit_name_{target_id}"}],
            [{"text": "🎁 اعطای تجهیزات", "callback_data": f"admin_give_item_{target_id}"}],
            [{"text": "🔐 تغییر کدهای کابینه", "callback_data": f"admin_change_player_codes_{target_id}"}],
            [{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]
        ]
    }
    show_screen(chat_id, text, keyboard)


def admin_change_player_codes(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    if target_id not in cabinet_codes:
        send_message(chat_id, "❌ این بازیکن کد کابینه ندارد!")
        return
    old_codes = cabinet_codes[target_id].copy()
    for key in old_codes.keys():
        new_code = generate_unique_code()
        cabinet_codes[target_id][key] = new_code
        db.save_cabinet_code(target_id, key, new_code)
    codes_text = "🔐 **کدهای امنیتی کابینه شما توسط ادمین تغییر کرد!**\n━━━━━━━━━━━━━━━━━━\n"
    codes_text += "⚠️ کدهای جدید شما:\n━━━━━━━━━━━━━━━━━━\n"
    for key, code in cabinet_codes[target_id].items():
        cabinet_name = CABINET_OPTIONS.get(key, {}).get("name", key)
        icon = CABINET_OPTIONS.get(key, {}).get("icon", "🔑")
        member_name = players_data.get(target_id, {}).get("cabinet", {}).get(key, "نامشخص")
        codes_text += f"\n{icon} {cabinet_name}\n"
        codes_text += f"🔑 کد جدید: `{code}`\n"
        codes_text += f"👤 {member_name}\n━━━━━━━━━━━━━━━━━━\n"
    codes_text += "\n💡 کدهای قدیمی شما دیگر معتبر نیستند!"
    send_message(int(target_id), codes_text)
    send_message(chat_id, f"✅ کدهای کابینه {players_data[target_id].get('player_name')} تغییر کرد!")
    show_player_edit_menu(chat_id, admin_id, target_id)


def admin_add_credit(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    waiting_for_add_credit[admin_id] = target_id
    send_message(chat_id, f"💰 **مقدار سکه برای افزودن به {players_data[target_id].get('player_name')} را وارد کنید:**")


def process_add_credit(chat_id, admin_id, amount):
    target_id = waiting_for_add_credit.pop(admin_id, None)
    if not target_id:
        return
    try:
        amount = int(amount)
        if amount <= 0:
            send_message(chat_id, "❌ مقدار باید بیشتر از 0 باشد!")
            return
        old_credit = players_data[target_id].get("credit", 0)
        players_data[target_id]["credit"] = old_credit + amount
        db.save_player(target_id, players_data[target_id])
        send_message(chat_id, f"✅ {amount:,} سکه به {players_data[target_id].get('player_name')} اضافه شد!\n💰 موجودی جدید: {players_data[target_id]['credit']:,}")
        show_player_edit_menu(chat_id, admin_id, target_id)
        send_message(int(target_id), f"💰 **{amount:,} سکه** به حساب شما واریز شد!\n💰 موجودی جدید: {players_data[target_id]['credit']:,}")
    except:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")


def admin_remove_credit(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    waiting_for_remove_credit[admin_id] = target_id
    send_message(chat_id, f"💰 **مقدار سکه برای کاهش از {players_data[target_id].get('player_name')} را وارد کنید:**")


def process_remove_credit(chat_id, admin_id, amount):
    target_id = waiting_for_remove_credit.pop(admin_id, None)
    if not target_id:
        return
    try:
        amount = int(amount)
        if amount <= 0:
            send_message(chat_id, "❌ مقدار باید بیشتر از 0 باشد!")
            return
        old_credit = players_data[target_id].get("credit", 0)
        new_credit = max(0, old_credit - amount)
        players_data[target_id]["credit"] = new_credit
        db.save_player(target_id, players_data[target_id])
        send_message(chat_id, f"✅ {amount:,} سکه از {players_data[target_id].get('player_name')} کم شد!\n💰 موجودی جدید: {players_data[target_id]['credit']:,}")
        show_player_edit_menu(chat_id, admin_id, target_id)
        send_message(int(target_id), f"⚠️ **{amount:,} سکه** از حساب شما کسر شد!\n💰 موجودی جدید: {players_data[target_id]['credit']:,}")
    except:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")


def admin_edit_defense(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    waiting_for_edit_defense[admin_id] = target_id
    send_message(chat_id, f"🛡 **مقدار جدید استقامت برای {players_data[target_id].get('player_name')} را وارد کنید:**")


def process_edit_defense(chat_id, admin_id, value):
    target_id = waiting_for_edit_defense.pop(admin_id, None)
    if not target_id:
        return
    try:
        new_value = int(value)
        if new_value < 0:
            send_message(chat_id, "❌ مقدار نمی‌تواند منفی باشد!")
            return
        old_defense = players_data[target_id].get("defense", 5000)
        players_data[target_id]["defense"] = new_value
        db.save_player(target_id, players_data[target_id])
        send_message(chat_id, f"✅ استقامت {players_data[target_id].get('player_name')} از {old_defense:,} به {new_value:,} تغییر کرد!")
        show_player_edit_menu(chat_id, admin_id, target_id)
    except:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")


def admin_edit_attack(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    waiting_for_edit_attack[admin_id] = target_id
    send_message(chat_id, f"💥 **مقدار جدید قدرت تخریب برای {players_data[target_id].get('player_name')} را وارد کنید:**")


def process_edit_attack(chat_id, admin_id, value):
    target_id = waiting_for_edit_attack.pop(admin_id, None)
    if not target_id:
        return
    try:
        new_value = int(value)
        if new_value < 0:
            send_message(chat_id, "❌ مقدار نمی‌تواند منفی باشد!")
            return
        old_attack = players_data[target_id].get("attack_power", 0)
        players_data[target_id]["attack_power"] = new_value
        db.save_player(target_id, players_data[target_id])
        send_message(chat_id, f"✅ قدرت تخریب {players_data[target_id].get('player_name')} از {old_attack:,} به {new_value:,} تغییر کرد!")
        show_player_edit_menu(chat_id, admin_id, target_id)
    except:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")


def admin_edit_score(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    waiting_for_edit_score[admin_id] = target_id
    send_message(chat_id, f"🏆 **مقدار جدید امتیاز برای {players_data[target_id].get('player_name')} را وارد کنید:**")


def process_edit_score(chat_id, admin_id, value):
    target_id = waiting_for_edit_score.pop(admin_id, None)
    if not target_id:
        return
    try:
        new_value = int(value)
        if new_value < 0:
            send_message(chat_id, "❌ مقدار نمی‌تواند منفی باشد!")
            return
        old_score = players_data[target_id].get("score", 0)
        players_data[target_id]["score"] = new_value
        db.save_player(target_id, players_data[target_id])
        send_message(chat_id, f"✅ امتیاز {players_data[target_id].get('player_name')} از {old_score:,} به {new_value:,} تغییر کرد!")
        show_player_edit_menu(chat_id, admin_id, target_id)
    except:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")


def admin_edit_population(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    waiting_for_edit_population[admin_id] = target_id
    send_message(chat_id, f"👥 **مقدار جدید جمعیت برای {players_data[target_id].get('player_name')} را وارد کنید:**")


def process_edit_population(chat_id, admin_id, value):
    target_id = waiting_for_edit_population.pop(admin_id, None)
    if not target_id:
        return
    try:
        new_value = int(value)
        if new_value < 0:
            send_message(chat_id, "❌ مقدار نمی‌تواند منفی باشد!")
            return
        old_pop = players_data[target_id].get("population", 10000)
        players_data[target_id]["population"] = new_value
        db.save_player(target_id, players_data[target_id])
        send_message(chat_id, f"✅ جمعیت {players_data[target_id].get('player_name')} از {old_pop:,} به {new_value:,} تغییر کرد!")
        show_player_edit_menu(chat_id, admin_id, target_id)
    except:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")


def admin_edit_country(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    waiting_for_edit_country[admin_id] = target_id
    countries_list = ""
    for continent_key, continent_data in COUNTRIES_LIST.items():
        countries_list += f"\n🌍 **{continent_data['name']}**\n"
        for country_name in continent_data.get("countries", {}).keys():
            is_taken = "❌" if country_name in used_countries else "✅"
            countries_list += f"   {is_taken} {country_name}\n"
    send_message(chat_id, f"🌍 **کشور جدید برای {players_data[target_id].get('player_name')} را وارد کنید:**\n\n{countries_list}\n\n📌 نام کشور را دقیق وارد کنید:")


def process_edit_country(chat_id, admin_id, country_name):
    target_id = waiting_for_edit_country.pop(admin_id, None)
    if not target_id:
        return
    continent_key, continent_name = get_country_continent(country_name)
    if not continent_key:
        send_message(chat_id, "❌ کشور معتبر نیست!")
        return
    old_country = players_data[target_id].get("country")
    if old_country and old_country in used_countries:
        if used_countries[old_country] == target_id:
            del used_countries[old_country]
            db.remove_country(old_country)
    players_data[target_id]["country"] = country_name
    players_data[target_id]["continent"] = continent_key
    used_countries[country_name] = target_id
    db.save_player(target_id, players_data[target_id])
    db.save_country(country_name, target_id)
    send_message(chat_id, f"✅ کشور {players_data[target_id].get('player_name')} از {old_country} به {country_name} تغییر کرد!")
    show_player_edit_menu(chat_id, admin_id, target_id)


def admin_edit_name(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    waiting_for_edit_name[admin_id] = target_id
    send_message(chat_id, f"✏️ **نام جدید برای {players_data[target_id].get('player_name')} را وارد کنید (۳ تا ۳۰ کاراکتر):**")


def process_edit_name(chat_id, admin_id, new_name):
    target_id = waiting_for_edit_name.pop(admin_id, None)
    if not target_id:
        return
    if len(new_name) < 3 or len(new_name) > 30:
        send_message(chat_id, "❌ نام باید بین ۳ تا ۳۰ کاراکتر باشد!")
        return
    old_name = players_data[target_id].get("player_name")
    players_data[target_id]["player_name"] = new_name
    db.save_player(target_id, players_data[target_id])
    send_message(chat_id, f"✅ نام بازیکن از {old_name} به {new_name} تغییر کرد!")
    show_player_edit_menu(chat_id, admin_id, target_id)


def admin_give_item_menu(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        return
    keyboard = {
        "inline_keyboard": [
            [{"text": "💰 سکه", "callback_data": f"admin_give_credit_{target_id}"}],
            [{"text": "🛡 استقامت", "callback_data": f"admin_give_defense_{target_id}"}],
            [{"text": "💥 قدرت تخریب", "callback_data": f"admin_give_attack_{target_id}"}],
            [{"text": "🏆 امتیاز", "callback_data": f"admin_give_score_{target_id}"}],
            [{"text": "👥 جمعیت", "callback_data": f"admin_give_population_{target_id}"}],
            [{"text": "⛏️ معدن زمرد", "callback_data": f"admin_give_mine_emerald_{target_id}"}],
            [{"text": "⚪ معدن آهن", "callback_data": f"admin_give_mine_iron_{target_id}"}],
            [{"text": "⚫ معدن نقره", "callback_data": f"admin_give_mine_silver_{target_id}"}],
            [{"text": "🟢 معدن برنز", "callback_data": f"admin_give_mine_bronze_{target_id}"}],
            [{"text": "🔵 معدن الماس", "callback_data": f"admin_give_mine_diamond_{target_id}"}],
            [{"text": "🟡 معدن طلا", "callback_data": f"admin_give_mine_gold_{target_id}"}],
            [{"text": "🔙 بازگشت", "callback_data": f"admin_edit_player_{target_id}"}]
        ]
    }
    show_screen(chat_id, f"🎁 **اعطای تجهیزات به {players_data[target_id].get('player_name')}**\n\nنوع تجهیزات را انتخاب کنید:", keyboard)


def admin_give_item(chat_id, admin_id, target_id, item_type, item_key=None):
    if not is_admin(admin_id):
        return
    waiting_for_give_item[admin_id] = {"target_id": target_id, "item_type": item_type, "item_key": item_key}
    send_message(chat_id, f"🔢 **تعداد را وارد کنید:**")


def process_give_item(chat_id, admin_id, count):
    data = waiting_for_give_item.pop(admin_id, None)
    if not data:
        return
    try:
        count = int(count)
        if count <= 0:
            send_message(chat_id, "❌ تعداد باید بیشتر از 0 باشد!")
            return
        target_id = data["target_id"]
        item_type = data["item_type"]
        item_key = data.get("item_key")
        target = players_data[target_id]
        if item_type == "credit":
            target["credit"] = target.get("credit", 0) + count
            msg = f"✅ {count:,} سکه به {target.get('player_name')} اضافه شد!"
        elif item_type == "defense":
            target["defense"] = target.get("defense", 5000) + count
            msg = f"✅ {count} استقامت به {target.get('player_name')} اضافه شد!"
        elif item_type == "attack":
            target["attack_power"] = target.get("attack_power", 0) + count
            msg = f"✅ {count} قدرت تخریب به {target.get('player_name')} اضافه شد!"
        elif item_type == "score":
            target["score"] = target.get("score", 0) + count
            msg = f"✅ {count} امتیاز به {target.get('player_name')} اضافه شد!"
        elif item_type == "population":
            target["population"] = target.get("population", 10000) + count
            msg = f"✅ {count} نفر به جمعیت {target.get('player_name')} اضافه شد!"
        elif item_type == "mine" and item_key:
            current = target.get(f"{item_key}_count", 0)
            target[f"{item_key}_count"] = current + count
            mine_info = MINES.get(item_key, {})
            target["daily_profit"] = target.get("daily_profit", 0) + (mine_info.get("daily_profit", 0) * count)
            msg = f"✅ {count} عدد {mine_info.get('name', item_key)} به {target.get('player_name')} اضافه شد!"
        db.save_player(target_id, target)
        send_message(chat_id, msg)
        show_player_edit_menu(chat_id, admin_id, target_id)
    except:
        send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")


# ==================== رفع اتحاد نامعتبر ====================
def fix_user_union(chat_id, admin_id, target_id):
    """پاک کردن اتحاد نامعتبر برای یک کاربر خاص (فقط ادمین)"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ فقط ادمین!")
        return
    
    if target_id not in players_data:
        send_message(chat_id, "❌ کاربر یافت نشد!")
        return
    
    old_union = players_data[target_id].get("union", "ندارد")
    players_data[target_id]["union"] = None
    db.save_player(target_id, players_data[target_id])
    
    send_message(chat_id, f"✅ **اتحاد کاربر پاک شد!**\n━━━━━━━━━━━━━━━━━━\n👤 کاربر: {players_data[target_id].get('player_name')}\n🆔 آیدی: {target_id}\n🤝 اتحاد قبلی: {old_union}\n━━━━━━━━━━━━━━━━━━\n💡 کاربر اکنون عضو هیچ اتحادی نیست.")
    
    send_message(int(target_id), 
        f"✅ **وضعیت اتحاد شما تصحیح شد!**\n━━━━━━━━━━━━━━━━━━\n"
        f"🤝 اتحاد نامعتبر '{old_union}' از حساب شما حذف شد.\n"
        f"💡 اکنون می‌توانید عضو اتحاد دیگری شوید یا اتحاد جدید بسازید.")


def admin_fix_union_menu(chat_id, user_id):
    """نمایش لیست کاربران با اتحاد نامعتبر"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ فقط ادمین!")
        return
    
    invalid_users = []
    for uid, pdata in players_data.items():
        union = pdata.get("union")
        if union:
            if union not in unions_data:
                invalid_users.append((uid, pdata.get("player_name", "نامشخص"), union))
    
    if not invalid_users:
        send_message(chat_id, "✅ **هیچ کاربری با اتحاد نامعتبر یافت نشد!**\n━━━━━━━━━━━━━━━━━━\n💡 اگر کاربری مشکل دارد، از روش زیر استفاده کنید:\n1️⃣ آیدی عددی کاربر را پیدا کنید\n2️⃣ از دستور /admin_fix_union [آیدی] استفاده کنید")
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔧 رفع دستی با آیدی", "callback_data": "admin_fix_union_manual"}],
                [{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]
            ]
        }
        send_message(chat_id, "🔧 **رفع دستی اتحاد**\nآیدی کاربر را وارد کنید:", keyboard)
        return
    
    text = "🔧 **کاربران با اتحاد نامعتبر:**\n━━━━━━━━━━━━━━━━━━\n"
    keyboard = []
    for uid, name, union in invalid_users:
        text += f"\n👤 {name}\n🆔 `{uid}`\n🤝 اتحاد نامعتبر: {union}\n━━━━━━━━━━━━━━━━━━\n"
        keyboard.append([{"text": f"🔧 رفع {name}", "callback_data": f"admin_fix_union_{uid}"}])
    
    keyboard.append([{"text": "🔙 بازگشت به پنل ادمین", "callback_data": "admin_panel"}])
    send_message(chat_id, text, {"inline_keyboard": keyboard})


def admin_fix_union_manual(chat_id, user_id):
    """دریافت آیدی کاربر برای رفع دستی"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ فقط ادمین!")
        return
    
    waiting_for_fix_union_id[user_id] = True
    send_message(chat_id, "🔧 **لطفاً آیدی عددی کاربر را وارد کنید:**\n\n(مثال: 1429674818)")


def process_fix_union_by_id(chat_id, admin_id, target_id):
    """رفع اتحاد کاربر با آیدی وارد شده"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ فقط ادمین!")
        return
    
    if target_id not in players_data:
        send_message(chat_id, f"❌ کاربر با آیدی {target_id} یافت نشد!")
        return
    
    old_union = players_data[target_id].get("union", "ندارد")
    players_data[target_id]["union"] = None
    db.save_player(target_id, players_data[target_id])
    
    send_message(chat_id, f"✅ **اتحاد کاربر پاک شد!**\n━━━━━━━━━━━━━━━━━━\n👤 کاربر: {players_data[target_id].get('player_name')}\n🆔 آیدی: {target_id}\n🤝 اتحاد قبلی: {old_union}\n━━━━━━━━━━━━━━━━━━\n💡 کاربر اکنون عضو هیچ اتحادی نیست.")
    
    send_message(int(target_id), 
        f"✅ **وضعیت اتحاد شما تصحیح شد!**\n━━━━━━━━━━━━━━━━━━\n"
        f"🤝 اتحاد نامعتبر '{old_union}' از حساب شما حذف شد.\n"
        f"💡 اکنون می‌توانید عضو اتحاد دیگری شوید یا اتحاد جدید بسازید.")


# ==================== سازمان ملل (تحریم) ====================
def send_un_panel(chat_id, user_id):
    if not is_admin(user_id):
        show_screen(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    keyboard = []
    count = 0
    for uid, data in players_data.items():
        if data.get("player_name") and count < 10:
            keyboard.append([{"text": f"🌍 {data.get('player_name')} - {data.get('country', 'نامشخص')}", "callback_data": f"sanction_select_{uid}"}])
            count += 1
    
    search_keyboard = [
        [{"text": "🔍 جستجوی کشور", "callback_data": "un_search"}],
        [{"text": "📋 لیست کامل بازیکنان", "callback_data": "un_full_list"}]
    ]
    
    if len(keyboard) > 0:
        search_keyboard.extend(keyboard)
    
    search_keyboard.append([{"text": "🔙 بازگشت به پنل ادمین", "callback_data": "admin_panel"}])
    
    text = "🌐 **سازمان ملل - تحریم کشورها**\n━━━━━━━━━━━━━━━━━━\n"
    text += "🔍 می‌توانید با نام کشور جستجو کنید\n"
    text += "📋 یا از لیست زیر انتخاب کنید:\n━━━━━━━━━━━━━━━━━━\n"
    
    show_screen(chat_id, text, {"inline_keyboard": search_keyboard})


def un_full_player_list(chat_id, user_id):
    """نمایش لیست کامل بازیکنان برای تحریم"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    keyboard = []
    for uid, data in players_data.items():
        if data.get("player_name"):
            keyboard.append([{"text": f"🌍 {data.get('player_name')} - {data.get('country', 'نامشخص')}", "callback_data": f"sanction_select_{uid}"}])
    
    if not keyboard:
        send_message(chat_id, "❌ هیچ بازیکنی یافت نشد!")
        return
    
    pages = [keyboard[i:i+20] for i in range(0, len(keyboard), 20)]
    current_page = 0
    
    if pages:
        page_buttons = []
        if len(pages) > 1:
            page_buttons.append({"text": "⬅️ قبلی", "callback_data": f"un_page_{current_page-1}"})
            page_buttons.append({"text": f"{current_page+1}/{len(pages)}", "callback_data": "un_page_info"})
            page_buttons.append({"text": "بعدی ➡️", "callback_data": f"un_page_{current_page+1}"})
        
        pages[current_page].append(page_buttons)
        pages[current_page].append([{"text": "🔍 جستجوی کشور", "callback_data": "un_search"}])
        pages[current_page].append([{"text": "🔙 بازگشت", "callback_data": "un_panel"}])
        
        send_message(chat_id, "🌐 **لیست کامل بازیکنان**\n━━━━━━━━━━━━━━━━━━\nکشور مورد نظر را انتخاب کنید:", {"inline_keyboard": pages[current_page]})


def un_full_player_list_page(chat_id, user_id, current_page):
    """صفحه مشخصی از لیست بازیکنان سازمان ملل"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    keyboard = []
    for uid, pdata in players_data.items():
        if pdata.get("player_name"):
            keyboard.append([{"text": f"🌍 {pdata.get('player_name')} - {pdata.get('country', 'نامشخص')}",
                              "callback_data": f"un_select_{uid}"}])
    if not keyboard:
        send_message(chat_id, "❌ هیچ بازیکنی یافت نشد!")
        return
    pages = [keyboard[i:i + 20] for i in range(0, len(keyboard), 20)]
    current_page = max(0, min(current_page, len(pages) - 1))
    page_buttons = []
    if current_page > 0:
        page_buttons.append({"text": "⬅️ قبلی", "callback_data": f"un_page_{current_page - 1}"})
    page_buttons.append({"text": f"{current_page + 1}/{len(pages)}", "callback_data": "un_page_info"})
    if current_page + 1 < len(pages):
        page_buttons.append({"text": "بعدی ➡️", "callback_data": f"un_page_{current_page + 1}"})
    if page_buttons:
        pages[current_page].append(page_buttons)
    pages[current_page].append([{"text": "🔍 جستجوی کشور", "callback_data": "un_search"}])
    pages[current_page].append([{"text": "🔙 بازگشت", "callback_data": "un_panel"}])
    send_message(chat_id, f"🌐 **لیست بازیکنان — صفحه {current_page + 1} از {len(pages)}**",
                 {"inline_keyboard": pages[current_page]})


def select_sanction_type(chat_id, user_id, target_id):
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    target_name = players_data.get(target_id, {}).get("player_name", "نامشخص")
    keyboard = {
        "inline_keyboard": [
            [{"text": "⚖️ تحریم سبک (3 روز - 30٪ جریمه)", "callback_data": f"sanction_light_{target_id}"}],
            [{"text": "⛔ تحریم سنگین (7 روز - 60٪ جریمه)", "callback_data": f"sanction_heavy_{target_id}"}],
            [{"text": "🔙 بازگشت", "callback_data": "un_panel"}]
        ]
    }
    send_message(chat_id, f"🌐 **اعمال تحریم علیه {target_name}**\n━━━━━━━━━━━━━━━━━━\nنوع تحریم را انتخاب کنید:", keyboard)


def process_un_sanction(chat_id, user_id, target_id, sanction_type):
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    if target_id not in players_data:
        send_message(chat_id, "❌ کاربر یافت نشد!")
        return
    target_name = players_data[target_id].get("player_name", "نامشخص")
    if sanction_type == "light":
        duration = 3
        penalty = 0.3
        penalty_text = "۳۰٪"
        type_text = "سبک"
    elif sanction_type == "heavy":
        duration = 7
        penalty = 0.6
        penalty_text = "۶۰٪"
        type_text = "سنگین"
    else:
        send_message(chat_id, "❌ نوع تحریم نامعتبر!")
        return
    sanctions_data[target_id] = {
        "type": sanction_type,
        "sanctioner": user_id,
        "sanctioner_name": players_data[user_id].get("player_name", "ادمین"),
        "start_date": time.time(),
        "end_date": time.time() + (duration * 86400),
        "price_penalty": penalty
    }
    db.save_sanction(target_id, sanctions_data[target_id])
    send_message(chat_id, f"✅ **تحریم {type_text} علیه {target_name} اعمال شد!**\n━━━━━━━━━━━━━━━━━━\n📅 مدت: {duration} روز\n💰 جریمه فروش: {penalty_text}\n🕐 پایان تحریم: {time.strftime('%Y/%m/%d', time.localtime(time.time() + duration * 86400))}")
    send_message(int(target_id), f"⚠️ **هشدار! سازمان ملل کشور شما را تحریم کرد!**\n━━━━━━━━━━━━━━━━━━\n⚖️ نوع تحریم: {type_text}\n📅 مدت: {duration} روز\n💰 جریمه فروش: {penalty_text}\n👑 اعمال کننده: {players_data[user_id].get('player_name', 'ادمین')}\n━━━━━━━━━━━━━━━━━━\n💡 در این مدت تحریم برداشته نخواهد شد!!")
    send_to_group(f"🌐 **اخبار سازمان ملل**\n━━━━━━━━━━━━━━━━━━\n⚖️ کشور {target_name} به مدت {duration} روز تحریم {type_text} شد!\n💰 جریمه: {penalty_text}\n👑 توسط: {players_data[user_id].get('player_name', 'ادمین')}")


def remove_sanction(chat_id, admin_id, target_id):
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    if target_id not in sanctions_data:
        send_message(chat_id, "❌ این کشور تحریم نیست!")
        return
    target_name = players_data.get(target_id, {}).get("player_name", "نامشخص")
    del sanctions_data[target_id]
    db.remove_sanction(target_id)
    send_message(chat_id, f"✅ تحریم {target_name} لغو شد!")
    send_message(int(target_id), f"✅ **تحریم کشور شما لغو شد!**\nمی‌توانید دوباره از فروشگاه خرید کنید.")


def admin_auto_assign_country(chat_id, user_id):
    """تخصیص خودکار کشور به بازیکنانی که کشور ندارند"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    send_message(chat_id, "🔄 در حال تخصیص خودکار کشور به بازیکنان بدون کشور...")
    
    all_countries = []
    for continent_key, continent_data in COUNTRIES_LIST.items():
        for country_name in continent_data.get("countries", {}).keys():
            all_countries.append(country_name)
    
    used = set(used_countries.keys())
    free_countries = [c for c in all_countries if c not in used]
    
    players_fixed = 0
    no_country_left = 0
    
    for uid, data in players_data.items():
        if data.get("player_name") and not data.get("country"):
            if free_countries:
                new_country = free_countries.pop(0)
                continent_key, continent_name = get_country_continent(new_country)
                players_data[uid]["country"] = new_country
                players_data[uid]["continent"] = continent_key
                used_countries[new_country] = uid
                db.save_player(uid, players_data[uid])
                db.save_country(new_country, uid)
                players_fixed += 1
                try:
                    send_message(int(uid),
                        f"🌍 **کشور به شما تخصیص داده شد!**\n━━━━━━━━━━━━━━━━━━\n"
                        f"📍 کشور: {new_country}\n"
                        f"🗺️ قاره: {continent_name}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"✅ اکنون می‌توانید بازی را ادامه دهید.")
                except:
                    pass
            else:
                no_country_left += 1
    
    report = f"✅ **تخصیص خودکار کشور انجام شد!**\n━━━━━━━━━━━━━━━━━━\n"
    report += f"📊 بازیکنانی که کشور گرفتند: {players_fixed}\n"
    report += f"⚠️ بازیکنانی که کشور نگرفتند (کشور کافی نیست): {no_country_left}\n"
    
    if no_country_left > 0:
        report += f"\n💡 ابتدا کشورهای جدید به بازی اضافه کنید."
    
    send_message(chat_id, report)
    
    if no_country_left > 0:
        send_message(chat_id, f"⚠️ **{no_country_left} بازیکن بدون کشور ماندند!**\nلطفاً کشورهای جدید اضافه کنید.")


# ==================== توابع مدیریت بازیکنان بدون اقتصاد ====================
def admin_find_players_without_economy(chat_id, user_id):
    """نمایش بازیکنانی که هیچ تجهیزات اقتصادی ندارند"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    total_players = 0
    players_without_economy = []
    
    for uid, data in players_data.items():
        total_players += 1
        
        player_name = data.get("player_name")
        if not player_name:
            player_name = f"کاربر ناشناس ({uid[:8]}...)"
        
        has_mine = False
        for mine_key in MINES.keys():
            if data.get(f"{mine_key}_count", 0) > 0:
                has_mine = True
                break
        
        has_economic = False
        for eco_key in ECONOMIC_ITEMS.keys():
            if data.get(f"{eco_key}_count", 0) > 0:
                has_economic = True
                break
        
        has_building = False
        for building_key in BUILDINGS.keys():
            if data.get(f"{building_key}_count", 0) > 0:
                has_building = True
                break
        
        if not has_mine and not has_economic and not has_building:
            players_without_economy.append({
                "user_id": uid,
                "name": player_name,
                "country": data.get("country", "❌ ندارد"),
                "credit": data.get("credit", 0),
                "score": data.get("score", 0),
                "daily_profit": data.get("daily_profit", 0),
                "union": data.get("union", "ندارد"),
                "has_name": data.get("player_name") is not None
            })
    
    total_without = len(players_without_economy)
    percent = (total_without / total_players * 100) if total_players > 0 else 0
    
    text = f"📊 **آمار بازیکنان بدون تجهیزات اقتصادی**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 **کل بازیکنان دیتابیس:** {total_players}\n"
    text += f"📊 **بدون تجهیزات اقتصادی:** {total_without}\n"
    text += f"📈 **درصد:** {percent:.1f}%\n"
    text += f"✅ **دارای تجهیزات:** {total_players - total_without}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    no_name_count = sum(1 for p in players_without_economy if not p["has_name"])
    if no_name_count > 0:
        text += f"⚠️ **از این تعداد، {no_name_count} بازیکن حتی اسم هم ندارند!**\n"
        text += f"💡 این بازیکنان حتماً باید حذف شوند.\n━━━━━━━━━━━━━━━━━━\n\n"
    
    if not players_without_economy:
        text += "✅ **همه بازیکنان حداقل یک تجهیزات اقتصادی دارند!**"
        send_message(chat_id, text)
        return
    
    for i, p in enumerate(players_without_economy[:15], 1):
        name_display = p['name']
        if not p['has_name']:
            name_display = f"⚠️ {p['name']}"
        
        text += f"{i}. 👤 **{name_display}**\n"
        text += f"   🆔 `{p['user_id']}`\n"
        text += f"   🌍 کشور: {p['country']}\n"
        text += f"   💰 {p['credit']:,} سکه | 🏆 {p['score']} امتیاز\n"
        text += f"   📈 سود روزانه: {p['daily_profit']:,}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
    
    if len(players_without_economy) > 15:
        text += f"\n... و {len(players_without_economy) - 15} بازیکن دیگر"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": f"🗑 حذف همه {total_without} بازیکن بدون اقتصاد", "callback_data": "admin_delete_all_economy"}],
            [{"text": "🔙 بازگشت به پنل ادمین", "callback_data": "admin_panel"}]
        ]
    }
    
    send_message(chat_id, text, keyboard)


def admin_delete_economy_player(chat_id, admin_id, target_id):
    """حذف یک بازیکن بدون تجهیزات اقتصادی"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    if target_id not in players_data:
        send_message(chat_id, "❌ بازیکن یافت نشد!")
        return
    
    player_data = players_data[target_id]
    player_name = player_data.get("player_name", "نامشخص")
    
    send_message(chat_id, f"⚠️ **آیا از حذف بازیکن {player_name} اطمینان دارید؟**\nبرای تایید عدد **1** را وارد کنید:")
    waiting_for_delete_economy_confirm[admin_id] = target_id


def process_delete_economy_confirm(chat_id, admin_id, text):
    """تایید نهایی حذف بازیکن بدون اقتصاد"""
    
    if admin_id not in waiting_for_delete_economy_confirm:
        send_message(chat_id, "❌ درخواست نامعتبر! لطفاً دوباره اقدام کنید.")
        return
    
    text_normalized = text.strip()
    persian_numbers = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
    for persian, latin in persian_numbers.items():
        text_normalized = text_normalized.replace(persian, latin)
    
    if text_normalized != "1":
        waiting_for_delete_economy_confirm.pop(admin_id, None)
        send_message(chat_id, "❌ عملیات حذف لغو شد.")
        return
    
    target_id = waiting_for_delete_economy_confirm.pop(admin_id)
    
    if target_id not in players_data:
        send_message(chat_id, "❌ بازیکن یافت نشد!")
        return
    
    player_data = players_data[target_id]
    player_name = player_data.get("player_name", "نامشخص")
    player_country = player_data.get("country")
    
    user_union = player_data.get("union")
    if user_union and user_union in unions_data:
        union_info = unions_data[user_union]
        if target_id in union_info.get("members", []):
            union_info["members"].remove(target_id)
            if union_info.get("owner") == target_id and union_info.get("members"):
                new_owner = union_info["members"][0]
                union_info["owner"] = new_owner
                union_info["owner_name"] = players_data[new_owner].get("player_name", "نامشخص")
            db.save_union(user_union, union_info)
    
    if player_country and player_country in used_countries:
        if used_countries[player_country] == target_id:
            del used_countries[player_country]
            db.remove_country(player_country)
    
    db.delete_player(target_id)
    del players_data[target_id]
    
    send_message(chat_id, f"✅ **بازیکن {player_name} حذف شد!**")
    send_to_group(f"🗑 **بازیکن {player_name} به دلیل نداشتن تجهیزات اقتصادی حذف شد.**")


# ==================== توابع مدیریت بازیکنان بدون کشور ====================
def admin_find_players_without_country(chat_id, user_id):
    """نمایش بازیکنانی که کشور ندارند"""
    if not is_admin(user_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    players_without_country = []
    
    for uid, data in players_data.items():
        if data.get("player_name"):
            country = data.get("country")
            if not country or country == "" or country == "None":
                players_without_country.append({
                    "user_id": uid,
                    "name": data.get("player_name"),
                    "credit": data.get("credit", 0),
                    "score": data.get("score", 0),
                    "union": data.get("union", "ندارد")
                })
    
    if not players_without_country:
        send_message(chat_id, "✅ **هیچ بازیکنی بدون کشور وجود ندارد!**")
        return
    
    total = len(players_without_country)
    total_players = len([p for p in players_data.values() if p.get("player_name")])
    
    text = f"⚠️ **بازیکنان بدون کشور**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 آمار: {total} بازیکن از {total_players} بازیکن کشور ندارند!\n"
    text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, p in enumerate(players_without_country[:30], 1):
        text += f"{i}. 👤 **{p['name']}**\n"
        text += f"   🆔 `{p['user_id']}`\n"
        text += f"   💰 {p['credit']:,} سکه | 🏆 {p['score']} امتیاز\n"
        text += f"   🤝 اتحاد: {p['union']}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
    
    if len(players_without_country) > 30:
        text += f"\n... و {len(players_without_country) - 30} بازیکن دیگر"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔧 تخصیص کشور خودکار", "callback_data": "admin_auto_assign_country"}],
            [{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]
        ]
    }
    
    send_message(chat_id, text, keyboard)


def admin_delete_all_economy_players(chat_id, admin_id):
    """حذف همه بازیکنانی که هیچ تجهیزات اقتصادی ندارند"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    to_delete = []
    for uid, data in players_data.items():
        has_mine = any(data.get(f"{mine_key}_count", 0) > 0 for mine_key in MINES.keys())
        has_economic = any(data.get(f"{eco_key}_count", 0) > 0 for eco_key in ECONOMIC_ITEMS.keys())
        has_building = any(data.get(f"{building_key}_count", 0) > 0 for building_key in BUILDINGS.keys())
        
        if not has_mine and not has_economic and not has_building:
            to_delete.append(uid)
    
    if not to_delete:
        send_message(chat_id, "✅ هیچ بازیکنی برای حذف وجود ندارد!")
        return
    
    total_players = len(players_data)
    no_name_count = sum(1 for uid in to_delete if not players_data[uid].get("player_name"))
    
    players_list = []
    for uid in to_delete[:10]:
        data = players_data[uid]
        name = data.get("player_name")
        if not name:
            name = f"کاربر ناشناس (بدون اسم)"
        players_list.append(f"• {name} (🆔 {uid})")
    
    players_text = "\n".join(players_list)
    if len(to_delete) > 10:
        players_text += f"\n... و {len(to_delete) - 10} نفر دیگر"
    
    text = f"⚠️ **هشدار حذف گروهی!**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 **کل بازیکنان دیتابیس:** {total_players}\n"
    text += f"🗑 **بازیکنان برای حذف:** {len(to_delete)}\n"
    if no_name_count > 0:
        text += f"⚠️ **بدون اسم:** {no_name_count} بازیکن\n"
    text += f"━━━━━━━━━━━━━━━━━━\n\n"
    text += f"**لیست بازیکنانی که حذف می‌شوند (۱۰ نفر اول):**\n{players_text}\n━━━━━━━━━━━━━━━━━━\n\n"
    text += f"❗ آیا از حذف این {len(to_delete)} بازیکن اطمینان دارید؟\nاین عمل غیرقابل بازگشت است!"
    
    confirm_id = str(random.randint(100000, 999999))
    pending_deletions[confirm_id] = {
        "admin_id": admin_id,
        "chat_id": chat_id,
        "players": to_delete
    }
    
    keyboard = {
        "inline_keyboard": [
            [{"text": f"✅ بله، {len(to_delete)} بازیکن حذف شوند", "callback_data": f"confirm_delete_all_{confirm_id}"}],
            [{"text": "❌ انصراف", "callback_data": "admin_panel"}]
        ]
    }
    
    send_message(chat_id, text, keyboard)


def process_delete_all_economy_callback(chat_id, admin_id, confirm_id):
    """پردازش تایید حذف از طریق دکمه"""
    if confirm_id not in pending_deletions:
        send_message(chat_id, "❌ درخواست منقضی شده است! لطفاً دوباره اقدام کنید.")
        return
    
    data = pending_deletions.pop(confirm_id)
    
    if data["admin_id"] != admin_id:
        send_message(chat_id, "❌ دسترسی غیرمجاز!")
        return
    
    to_delete = data["players"]
    
    if not to_delete:
        send_message(chat_id, "✅ هیچ بازیکنی برای حذف وجود ندارد!")
        return
    
    send_message(chat_id, f"🔄 در حال حذف {len(to_delete)} بازیکن...")
    
    deleted = 0
    failed = 0
    
    for uid in to_delete:
        try:
            if uid not in players_data:
                continue
                
            player_data = players_data[uid]
            player_country = player_data.get("country")
            
            user_union = player_data.get("union")
            if user_union and user_union in unions_data:
                union_info = unions_data[user_union]
                if uid in union_info.get("members", []):
                    union_info["members"].remove(uid)
                    if union_info.get("owner") == uid and union_info.get("members"):
                        new_owner = union_info["members"][0]
                        union_info["owner"] = new_owner
                        union_info["owner_name"] = players_data[new_owner].get("player_name", "نامشخص")
                    db.save_union(user_union, union_info)
            
            if player_country and player_country in used_countries:
                if used_countries[player_country] == uid:
                    del used_countries[player_country]
                    db.remove_country(player_country)
            
            db.delete_player(uid)
            del players_data[uid]
            deleted += 1
            
        except Exception as e:
            print(f"ERROR deleting {uid}: {e}")
            failed += 1
    
    result_text = f"✅ **عملیات حذف انجام شد!**\n━━━━━━━━━━━━━━━━━━\n✅ حذف شده: {deleted} بازیکن\n❌ ناموفق: {failed} بازیکن"
    send_message(chat_id, result_text)
    
    if deleted > 0:
        send_to_group(f"🗑 **{deleted} بازیکن بدون تجهیزات اقتصادی از بازی حذف شدند.**")


def process_delete_all_economy_confirm(chat_id, admin_id, text):
    """تایید حذف همه بازیکنان بدون اقتصاد"""
    
    if admin_id not in waiting_for_delete_all_economy:
        send_message(chat_id, "❌ درخواست نامعتبر! لطفاً دوباره از منوی ادمین اقدام کنید.")
        return
    
    text_normalized = text.strip()
    persian_numbers = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
    for persian, latin in persian_numbers.items():
        text_normalized = text_normalized.replace(persian, latin)
    
    if text_normalized != "1":
        waiting_for_delete_all_economy.pop(admin_id, None)
        send_message(chat_id, "❌ عملیات حذف لغو شد.")
        return
    
    to_delete = waiting_for_delete_all_economy.pop(admin_id)
    
    if not to_delete:
        send_message(chat_id, "✅ هیچ بازیکنی برای حذف وجود ندارد!")
        return
    
    deleted = 0
    failed = 0
    failed_list = []
    
    for uid in to_delete:
        try:
            if uid not in players_data:
                continue
                
            player_data = players_data[uid]
            player_country = player_data.get("country")
            
            user_union = player_data.get("union")
            if user_union and user_union in unions_data:
                union_info = unions_data[user_union]
                if uid in union_info.get("members", []):
                    union_info["members"].remove(uid)
                    if union_info.get("owner") == uid and union_info.get("members"):
                        new_owner = union_info["members"][0]
                        union_info["owner"] = new_owner
                        union_info["owner_name"] = players_data[new_owner].get("player_name", "نامشخص")
                    db.save_union(user_union, union_info)
            
            if player_country and player_country in used_countries:
                if used_countries[player_country] == uid:
                    del used_countries[player_country]
                    db.remove_country(player_country)
            
            db.delete_player(uid)
            del players_data[uid]
            deleted += 1
            
        except Exception as e:
            print(f"ERROR deleting {uid}: {e}")
            failed += 1
            failed_list.append(uid)
    
    result_text = f"✅ **عملیات حذف انجام شد!**\n━━━━━━━━━━━━━━━━━━\n✅ حذف شده: {deleted} بازیکن\n❌ ناموفق: {failed} بازیکن"
    
    if failed_list:
        result_text += f"\n\n❌ بازیکنان ناموفق:\n" + "\n".join([f"• {uid}" for uid in failed_list[:5]])
    
    send_message(chat_id, result_text)
    
    if deleted > 0:
        send_to_group(f"🗑 **{deleted} بازیکن بدون تجهیزات اقتصادی از بازی حذف شدند.**")


# ==================== توابع بررسی کشورهای تکراری ====================
def admin_show_duplicate_countries(chat_id, admin_id):
    """نمایش بازیکنانی که کشور تکراری دارند"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    country_count = {}
    for uid, data in players_data.items():
        if data.get("player_name") and data.get("country"):
            country = data.get("country")
            if country not in country_count:
                country_count[country] = []
            country_count[country].append({
                "user_id": uid,
                "name": data.get("player_name"),
                "credit": data.get("credit", 0)
            })
    
    duplicates = {k: v for k, v in country_count.items() if len(v) > 1}
    
    if not duplicates:
        send_message(chat_id, "✅ **هیچ کشور تکراری یافت نشد!**\nهمه بازیکنان کشور یکتا دارند.")
        return
    
    text = f"⚠️ **کشورهای تکراری**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 تعداد کشورهای تکراری: {len(duplicates)}\n"
    text += f"👥 تعداد بازیکنان درگیر: {sum(len(v) for v in duplicates.values())}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n\n"
    
    for country, players in list(duplicates.items())[:15]:
        text += f"🌍 **{country}** - {len(players)} نفر\n"
        for p in players:
            text += f"   👤 {p['name']} | 🆔 `{p['user_id']}` | 💰 {p['credit']:,}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔧 رفع تکراری‌ها", "callback_data": "admin_fix_duplicate_countries"}],
            [{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]
        ]
    }
    
    send_message(chat_id, text, keyboard)


def admin_fix_duplicate_countries(chat_id, admin_id):
    """رفع مشکل کشورهای تکراری"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    send_message(chat_id, "🔄 در حال رفع کشورهای تکراری...")
    
    country_count = {}
    for uid, data in players_data.items():
        if data.get("player_name") and data.get("country"):
            country = data.get("country")
            if country not in country_count:
                country_count[country] = []
            country_count[country].append(uid)
    
    all_countries = []
    for continent in COUNTRIES_LIST.values():
        all_countries.extend(continent.get("countries", {}).keys())
    
    used = set(used_countries.keys())
    free_countries = [c for c in all_countries if c not in used]
    
    fixed_count = 0
    changes = []
    
    for country, user_ids in country_count.items():
        if len(user_ids) > 1:
            keep_user = user_ids[0]
            
            for uid in user_ids[1:]:
                if free_countries:
                    new_country = free_countries.pop(0)
                    old_country = players_data[uid].get("country")
                    
                    players_data[uid]["country"] = new_country
                    players_data[uid]["continent"] = get_country_continent_key(new_country)
                    
                    db.save_player(uid, players_data[uid])
                    db.save_country(new_country, uid)
                    
                    if country in used_countries and used_countries[country] == uid:
                        used_countries.pop(country, None)
                    
                    fixed_count += 1
                    changes.append(f"{players_data[uid].get('player_name')}: {old_country} → {new_country}")
                    
                    try:
                        send_message(int(uid), 
                            f"🌍 **تغییر کشور**\n━━━━━━━━━━━━━━━━━━\n"
                            f"⚠️ کشور شما تکراری بود و به {new_country} تغییر یافت.\n"
                            f"📍 قاره: {CONTINENT_NAMES.get(get_country_continent_key(new_country), 'نامشخص')}")
                    except:
                        pass
    
    if fixed_count > 0:
        report = f"✅ **رفع کشورهای تکراری**\n━━━━━━━━━━━━━━━━━━\n"
        report += f"📊 تعداد رفع شده: {fixed_count}\n"
        report += f"📋 تغییرات:\n"
        for ch in changes[:10]:
            report += f"   • {ch}\n"
        if len(changes) > 10:
            report += f"   • ... و {len(changes) - 10} نفر دیگر\n"
        send_message(chat_id, report)
    else:
        send_message(chat_id, "✅ همه کشورها یکتا هستند!")
    
    for uid, data in players_data.items():
        country = data.get("country")
        if country:
            used_countries[country] = uid
            db.save_country(country, uid)


# ==================== 🏁 سیستم پایان فصل ====================
def admin_end_season_menu(chat_id, admin_id):
    """نمایش منوی پایان فصل (فقط ادمین اصلی)"""
    if admin_id != MAIN_ADMIN_ID:
        send_message(chat_id, "⛔ فقط ادمین اصلی می‌تواند فصل را پایان دهد!")
        return
    
    if not players_data:
        send_message(chat_id, "❌ هیچ بازیکنی وجود ندارد!")
        return
    
    active_players = [p for p in players_data.values() if p.get("player_name")]
    total_players = len(active_players)
    seasons_count = db.get_all_seasons_count()
    
    text = f"""🏁 **پایان فصل** ⚠️
━━━━━━━━━━━━━━━━━━
📊 **آمار فعلی:**
• تعداد بازیکنان فعال: {total_players}
• تعداد فصل‌های انجام‌شده: {seasons_count}
• فصل فعلی: #{seasons_count + 1}

━━━━━━━━━━━━━━━━━━
⚠️ **هشدار مهم!**

با تایید پایان فصل:
✅ ۱۰ برنده برتر در تاریخچه ذخیره میشن
✅ به برندگان پاداش ویژه داده میشه
✅ همه بازیکنان، اتحادها، پایگاه‌ها ریست میشن
✅ همه کشورها آزاد میشن
✅ بازی از صفر شروع میشه

⚠️ **این عمل غیرقابل بازگشت است!**

آیا از پایان فصل اطمینان دارید؟"""
    
    keyboard = {"inline_keyboard": [
        [{"text": "🏁 بله، فصل رو تموم کن", "callback_data": "admin_end_season_confirm"}],
        [{"text": "🏆 مشاهده برندگان فصل قبل", "callback_data": "admin_show_last_winners"}],
        [{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]
    ]}
    send_message(chat_id, text, keyboard)


def admin_end_season_confirm(chat_id, admin_id):
    """تایید نهایی و اجرای پایان فصل"""
    if admin_id != MAIN_ADMIN_ID:
        send_message(chat_id, "⛔ فقط ادمین اصلی!")
        return
    
    send_message(chat_id, "🔄 **در حال پایان فصل...**\nلطفاً صبر کنید...")
    
    # 📌 ذخیره لیست همه بازیکنان قبل از ریست
    all_player_ids = list(players_data.keys())
    
    # ۱. مرتب‌سازی بازیکنان بر اساس امتیاز
    active_players = [
        {**p, "user_id": uid}
        for uid, p in players_data.items()
        if p.get("player_name")
    ]
    active_players.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    top_10 = active_players[:10]
    
    # ۲. ذخیره برندگان در دیتابیس
    try:
        db.save_season_winners(top_10)
    except Exception as e:
        print(f"⚠️ خطا در ذخیره برندگان: {e}")
    
    # ۳. اعلام برندگان در گروه
    season_num = db.get_all_seasons_count()
    
    winners_msg = f"🏆 **پایان فصل #{season_num}** 🏆\n"
    winners_msg += "━━━━━━━━━━━━━━━━━━\n"
    winners_msg += "🎉 **برندگان این فصل:**\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, p in enumerate(top_10[:3], 1):
        medal = medals[i - 1]
        winners_msg += f"{medal} **{p.get('player_name')}**\n"
        winners_msg += f"   🌍 {p.get('country')}\n"
        winners_msg += f"   🏆 {p.get('score', 0)} امتیاز\n"
        winners_msg += f"   💰 {p.get('credit', 0):,} سکه\n\n"
    
    if len(top_10) > 3:
        winners_msg += "📋 **رتبه‌های ۴ تا ۱۰:**\n"
        for i, p in enumerate(top_10[3:], 4):
            winners_msg += f"{i}. {p.get('player_name')} — {p.get('score', 0)} امتیاز\n"
    
    winners_msg += "━━━━━━━━━━━━━━━━━━\n"
    winners_msg += "🎊 **تبریک به همه برندگان!**\n"
    winners_msg += "🔄 **فصل جدید در حال شروع...**"
    
    send_to_group(winners_msg)
    
    # ۴. 📌 ارسال پیام تبریک به برندگان + پاداش
    rewards = {1: 500000, 2: 300000, 3: 200000}
    
    for i, p in enumerate(top_10, 1):
        uid = p.get("user_id")
        try:
            if i <= 3:
                reward = rewards.get(i, 0)
                send_message(int(uid),
                    f"🏆 **تبریک! شما برنده فصل شدید!**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🥇 **رتبه شما: {i}**\n"
                    f"🏆 امتیاز نهایی: {p.get('score', 0)}\n"
                    f"💰 غنیمت فصل: {p.get('credit', 0):,} سکه\n"
                    f"🎁 **پاداش ویژه: {reward:,} سکه**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🎊 شما یکی از قهرمانان این فصل هستید!")
            else:
                send_message(int(uid),
                    f"🎉 **تبریک!**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"شما در رتبه **{i}** این فصل قرار گرفتید!\n"
                    f"🏆 امتیاز نهایی: {p.get('score', 0)}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🔄 فصل جدید به زودی شروع میشه!")
        except:
            pass
    
    # ۵. 📌 ارسال پیام «فصل تمام شد» به همه بازیکنان + اضافه به force_restart
    notified = 0
    for uid in all_player_ids:
        try:
            # پیام «فصل تمام شد» + حذف Reply Keyboard
            send_season_ended_notification(int(uid))
            notified += 1
            
            # 📌 پاک کردن کش منو برای این کاربر
            state.menu_message.pop(str(uid), None)
            state.menu_message.pop(f"reply_kb_sent_{uid}", None)
            
            # 📌 اضافه کردن به لیست اجبار به restart
            state.add_force_restart_user(uid)
            
            time.sleep(0.05)  # جلوگیری از rate limit
        except Exception as e:
            print(f"⚠️ خطا در ارسال به {uid}: {e}")
    
    # ۶. 📌 ریست دیتابیس
    try:
        db.reset_all_players()
        db.reset_game_config_for_new_season()
    except Exception as e:
        print(f"⚠️ خطا در ریست دیتابیس: {e}")
        send_message(chat_id, f"❌ خطا در ریست: {e}")
        return
    
    # ۷. 📌 ریست کامل state
    state.reset_for_new_season()
    
    # 📌 بعد از ریست state، دوباره کاربران رو به force_restart اضافه کن
    # چون reset_for_new_season فقط dictها رو پاک می‌کنه نه force_restart رو
    for uid in all_player_ids:
        state.add_force_restart_user(uid)
    
    # ۸. 📌 اعلام شروع فصل جدید در گروه
    send_to_group(
        f"🎊 **فصل جدید شروع شد!** 🎊\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"فصل جدید آماده است!\n"
        f"🌍 همه کشورها آزاد شدن\n"
        f"👥 همه بازیکنان حذف شدن\n"
        f"💰 سکه و تجهیزات ریست شدن\n\n"
        f"🚀 **برای شروع، دستور /start را بزنید!**"
    )
    
    # ۹. گزارش نهایی به ادمین
    send_message(chat_id,
        f"✅ **پایان فصل با موفقیت انجام شد!**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 تعداد برندگان ذخیره‌شده: {len(top_10)}\n"
        f"👥 بازیکنان حذف‌شده: {len(active_players)}\n"
        f"📩 پیام «فصل تمام شد» ارسال‌شده: {notified}\n"
        f"🔄 فصل جدید شروع شد!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 همه بازیکنان باید با /start مجدداً ثبت‌نام کنن.")


def admin_show_last_winners(chat_id, admin_id):
    """نمایش برندگان آخرین فصل"""
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ دسترسی غیرمجاز!")
        return
    
    winners = db.get_last_season_winners(10)
    seasons_count = db.get_all_seasons_count()
    
    if not winners:
        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت به پنل ادمین", "callback_data": "admin_panel"}]]}
        send_message(chat_id, "📋 **هیچ فصلی پایان نیافته!**", keyboard)
        return
    
    text = f"🏆 **برندگان فصل #{seasons_count}**\n"
    text += "━━━━━━━━━━━━━━━━━━\n\n"
    
    for uid, name, country, score, credit, defense, attack, population, rank, ended_at in winners:
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
        text += f"{medal} **{name}**\n"
        text += f"   🌍 {country}\n"
        text += f"   🏆 {score:,} امتیاز\n"
        text += f"   💰 {credit:,} سکه\n"
        text += f"   🛡 {defense:,} | 💥 {attack:,}\n"
        text += f"   👥 {population:,} جمعیت\n"
        text += "━━━━━━━━━━━━━━━━━━\n"
    
    keyboard = {"inline_keyboard": [
        [{"text": "🔙 بازگشت به پنل ادمین", "callback_data": "admin_panel"}]
    ]}
    send_message(chat_id, text, keyboard)