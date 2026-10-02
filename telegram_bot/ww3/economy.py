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
from .helpers import get_game_day, is_virus_active, metro_shelter_factor, send_message, send_to_group
from .state import db, players_data
from .static_data import ECONOMIC_ITEMS, GROUND_FORCES, MINES, VIRUSES

# ==================== ماژول economy ====================


def fix_industrial_company_profit():
    """محاسبه مجدد سود همه بازیکنان بر اساس تجهیزات فعلی"""
    
    print("🔄 در حال محاسبه مجدد سود همه بازیکنان...")
    
    corrected_count = 0
    total_old_profit = 0
    total_new_profit = 0
    
    for user_id, player_data in players_data.items():
        if not player_data.get("player_name"):
            continue
        
        old_profit = player_data.get("daily_profit", 0)
        total_old_profit += old_profit
        
        # ========== محاسبه مجدد سود از صفر ==========
        new_profit = 0
        
        # 1. معادن
        for mine_key, mine_info in MINES.items():
            count = player_data.get(f"{mine_key}_count", 0)
            new_profit += count * mine_info["daily_profit"]
        
        # 2. تجهیزات اقتصادی
        for eco_key, eco_info in ECONOMIC_ITEMS.items():
            count = player_data.get(f"{eco_key}_count", 0)
            new_profit += count * eco_info["profit"]
        
        players_data[user_id]["daily_profit"] = new_profit
        total_new_profit += new_profit
        
        db.save_player(user_id, players_data[user_id])
        
        if old_profit != new_profit:
            corrected_count += 1
            print(f"  ✅ {player_data.get('player_name')}: {old_profit:,} → {new_profit:,} سکه/روز")
        
        if old_profit != new_profit and new_profit > 0:
            try:
                industrial_count = player_data.get("industrial_company_count", 0)
                
                message = f"🔧 **تصحیح سود روزانه**\n━━━━━━━━━━━━━━━━━━\n"
                message += f"📈 سود قبلی: {old_profit:,} سکه\n"
                message += f"📈 سود جدید: {new_profit:,} سکه\n"
                message += f"━━━━━━━━━━━━━━━━━━\n"
                
                if industrial_count > 0:
                    message += f"🏭 کارخانه صنعتی: {industrial_count} عدد × 70,000 = {industrial_count * 70000:,} سکه\n"
                
                message += f"\n✅ سود شما بر اساس تجهیزاتتان محاسبه شد."
                
                send_message(int(user_id), message)
            except:
                pass
    
    print(f"\n{'='*50}")
    print(f"✅ تصحیح سود کامل شد!")
    print(f"📊 تعداد بازیکنان تصحیح شده: {corrected_count}")
    print(f"💰 مجموع سود قبلی: {total_old_profit:,} سکه/روز")
    print(f"💰 مجموع سود جدید: {total_new_profit:,} سکه/روز")
    print(f"{'='*50}")
    
    return corrected_count


def spread_random_virus():
    if not is_virus_active():
        return
    current_time = time.time()
    if current_time - state.last_virus_spread < 21600:
        return
    if random.random() < 0.15:
        active_players = [uid for uid in players_data if players_data[uid].get("player_name")]
        if active_players:
            target = random.choice(active_players)
            virus = random.choice(list(VIRUSES.keys()))
            if "active_viruses" not in players_data[target]:
                players_data[target]["active_viruses"] = {}
            players_data[target]["active_viruses"][virus] = {
                "remaining_days": 5,
                "daily_loss": VIRUSES[virus]["daily_loss"],
                "damage_base": VIRUSES[virus]["damage_base"],
                "start_date": current_time
            }
            db.save_player(target, players_data[target])
            current_day = get_game_day()
            send_message(int(target), f"⚠️ **هشدار!**\n\n{VIRUSES[virus]['icon']} ویروس {VIRUSES[virus]['name']} در کشور شما شناسایی شد!\n📅 روز {current_day} بازی\n💀 ضرر روزانه: {VIRUSES[virus]['daily_loss']} سرباز\n🕐 مدت: 5 روز\n🏥 برای درمان به بیمارستان مراجعه کنید!")
            virus_msg = f"🦠 **اخبار جهانی**\n━━━━━━━━━━━━━━━━━━\nویروس {VIRUSES[virus]['name']} در کشور {players_data[target].get('country', 'نامشخص')} منتشر شد!\n📅 روز {current_day} بازی"
            send_to_group(virus_msg)
            state.last_virus_spread = current_time


def apply_virus_damage():
    if not is_virus_active():
        return
    # 🔒 فقط یک بار در هر روزِ بازی اجرا شود
    current_day = get_game_day()
    if state.last_virus_damage_day == current_day:
        return
    state.last_virus_damage_day = current_day
    db.set_game_config('last_virus_damage_day', str(current_day))
    for user_id in players_data:
        active_viruses = players_data[user_id].get("active_viruses", {})
        if not active_viruses:
            continue
        for virus_key, virus_data in list(active_viruses.items()):
            virus_data["remaining_days"] -= 1
            if virus_data["remaining_days"] <= 0:
                del players_data[user_id]["active_viruses"][virus_key]
                send_message(int(user_id), f"✅ **خبر خوب!**\n\nویروس {VIRUSES[virus_key]['name']} در کشور شما مهار شد!\n🕐 مدت ابتلا: 5 روز")
            else:
                if virus_data.get("damage_base", False):
                    players_data[user_id]["defense"] = max(0, players_data[user_id].get("defense", 5000) - 50)
                # 🚉 مترو پناهگاه است: تلفات جمعیت کم می‌شود
                _pop_loss = int(virus_data.get("daily_loss", 0) * metro_shelter_factor(user_id))
                if _pop_loss > 0:
                    players_data[user_id]["population"] = max(0, players_data[user_id].get("population", 10000) - _pop_loss)
                if random.random() < 0.3:
                    send_message(int(user_id), f"🦠 **گزارش ویروس**\n━━━━━━━━━━━━━━━━━━\nویروس: {VIRUSES[virus_key]['name']}\n📅 روز {current_day} بازی\n💀 روزهای باقیمانده: {virus_data['remaining_days']}\n👥 تلفات امروز: {virus_data.get('daily_loss', 0)} نفر")
        db.save_player(user_id, players_data[user_id])


def check_and_add_daily_profit():
    current_time = time.localtime()
    current_hour = current_time.tm_hour
    current_day = current_time.tm_yday
    if state.last_profit_date == current_day:
        return False
    if current_hour == 22:
        current_game_day = get_game_day()
        for user_id in players_data:
            daily_profit = players_data[user_id].get("daily_profit", 0)
            if daily_profit > 0:
                players_data[user_id]["credit"] = players_data[user_id].get("credit", 0) + daily_profit
                normal_hospital = players_data[user_id].get("normal_hospital_count", 0)
                professional_hospital = players_data[user_id].get("professional_hospital_count", 0)
                if normal_hospital > 0 or professional_hospital > 0:
                    active_viruses = players_data[user_id].get("active_viruses", {})
                    for virus_key in list(active_viruses.keys()):
                        virus_needed_hospital = VIRUSES[virus_key].get("hospital_needed", "normal")
                        if virus_needed_hospital == "normal" and normal_hospital > 0:
                            if random.random() < 0.5:
                                del players_data[user_id]["active_viruses"][virus_key]
                                send_message(int(user_id), f"🏥 **بیمارستان شما ویروس {VIRUSES[virus_key]['name']} را درمان کرد!**")
                        elif virus_needed_hospital == "professional" and professional_hospital > 0:
                            if random.random() < 0.7:
                                del players_data[user_id]["active_viruses"][virus_key]
                                send_message(int(user_id), f"🏥 **بیمارستان حرفه‌ای شما ویروس {VIRUSES[virus_key]['name']} را درمان کرد!**")
                db.save_player(user_id, players_data[user_id])
            # 🛕 پادگان: هر شب سرباز تربیت می‌کند (هر پادگان ۵ سرباز، سقف ۱۰۰۰)
            barracks_count = players_data[user_id].get("barracks_count", 0)
            if barracks_count > 0:
                _cap = GROUND_FORCES["normal_soldier"]["count"]
                produced = min(5 * barracks_count, max(0, _cap - players_data[user_id].get("normal_soldier_ground_count", 0)))
                if produced > 0:
                    players_data[user_id]["normal_soldier_ground_count"] = players_data[user_id].get("normal_soldier_ground_count", 0) + produced
                    send_message(int(user_id), f"🛕 **پادگان‌های شما امروز {produced} سرباز تربیت کردند!**")
                    db.save_player(user_id, players_data[user_id])
            # 🔥 آتش‌سوزی بمب آتش‌زا: تا ۳ روز تلفات جمعی (مترو محافظ است)
            if players_data[user_id].get("on_fire_until", 0) > time.time():
                burn = int(players_data[user_id].get("population", 10000) * 0.03 * metro_shelter_factor(user_id))
                if burn > 0:
                    players_data[user_id]["population"] = max(0, players_data[user_id].get("population", 10000) - burn)
                    send_message(int(user_id), f"🔥 **شهر شما هنوز در آتش می‌سوزد!** امروز {burn:,} نفر جان باختند.")
                    db.save_player(user_id, players_data[user_id])
        current_game_day = get_game_day()
        active_viruses_count = sum(1 for p in players_data.values() if p.get("active_viruses"))
        report = f"📊 **گزارش روزانه**\n━━━━━━━━━━━━━━━━━━\n📅 روز {current_game_day} بازی\n👥 بازیکنان: {len(players_data)}\n🦠 کشورهای آلوده: {active_viruses_count}\n{'🟢 ویروس‌ها فعال هستند' if is_virus_active() else '🔴 ویروس‌ها هنوز فعال نشده‌اند'}"
        send_to_group(report)
        state.last_profit_date = current_day
        db.set_game_config('last_profit_date', str(current_day))
        return True
    return False


def load_game_config():
    game_start_date_str = db.get_game_config("game_start_date")
    if game_start_date_str:
        state.game_start_date = float(game_start_date_str)
    else:
        state.game_start_date = time.time()
        db.set_game_config("game_start_date", state.game_start_date)
    virus_start_day_str = db.get_game_config("virus_start_day")
    if virus_start_day_str:
        state.virus_start_day = int(virus_start_day_str)
    else:
        state.virus_start_day = 5
        db.set_game_config("virus_start_day", state.virus_start_day)
    # 🔒 وضعیت جنگ ماندگار (با ری‌استارت نمی‌پرد)
    state.war_active = db.get_game_config("war_active", "0") == "1"
    _ws = db.get_game_config("war_start_time")
    state.war_start_time = float(_ws) if _ws else None
    _we = db.get_game_config("war_end_time")
    state.war_end_time = float(_we) if _we else None
    _lp = db.get_game_config("last_profit_date")
    state.last_profit_date = int(_lp) if _lp else None
    _lv = db.get_game_config("last_virus_damage_day")
    state.last_virus_damage_day = int(_lv) if _lv else None
