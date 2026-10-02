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
from .config import STATEMENT_LIMIT
from .helpers import (add_statement_record, can_send_statement, get_country_continent_key,
                      is_admin, send_message, send_to_group, show_screen, send_reply_keyboard)
from .state import db, players_data, user_in_cabinet_setup
from .static_data import CONTINENT_NAMES

# ==================== ماژول dashboard ====================


def send_admin_home(chat_id, user_id):
    """صفحه ورود ادمینی که رکورد بازیکن ندارد — بدون داشبورد قلابی «نامشخص»"""
    keyboard = {"inline_keyboard": [
        [{"text": "👑 پنل ادمین", "callback_data": "admin_panel"}],
        [{"text": "🌐 سازمان ملل", "callback_data": "un_panel"}],
        [{"text": "🎮 ثبت‌نام به عنوان بازیکن", "callback_data": "start_game"}],
    ]}
    send_message(chat_id,
        "👑 **پنل مدیریت ربات**\n━━━━━━━━━━━━━━━━━━\n"
        "شما به عنوان **ادمین** وارد شده‌اید.\n\n"
        "• 👑 **پنل ادمین** — مدیریت کامل ربات\n"
        "• 🎮 **ثبت‌نام به عنوان بازیکن** — اگر می‌خواهید خودتان هم بازی کنید",
        keyboard)


def show_battle_log(chat_id, user_id):
    """📜 تاریخچه ۱۰ نبرد آخر بازیکن — با editMessageText"""
    rows = db.get_battle_log(user_id, 10)
    if not rows:
        text = "📜 **تاریخچه نبردها**\n━━━━━━━━━━━━━━━━━━\nهنوز نبرده‌ای ثبت نشده!"
    else:
        text = "📜 **تاریخچه نبردهای شما**\n━━━━━━━━━━━━━━━━━━\n" + "\n".join(f"• {t}" for _, t in rows)
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔄 بروزرسانی", "callback_data": "my_battles"}],
            [{"text": "🔙 بازگشت به داشبورد", "callback_data": "dashboard"}]
        ]
    }
    show_screen(chat_id, text, keyboard)


def get_dashboard_text(user_id):
    """ساخت متن داشبورد اصلی"""
    user = players_data.get(user_id, {})
    cabinet = user.get("cabinet", {})
    return f"""📌 **داشبورد کشور شما**
━━━━━━━━━━━━━━━━━━
👤 پلیر: {user.get('player_name', 'نامشخص')}
🌍 کشور: {user.get('country', 'نامشخص')}
🏆 امتیاز: {user.get('score', 0)}

👥 **کابینه**
━━━━━━━━━━━━━━━━━━
🤝 دیپلمات: {cabinet.get('diplomat', '❌')}
👑 رهبر: {cabinet.get('leader', '❌')}
🛡️ دفاع: {cabinet.get('defense', '❌')}
💰 اقتصاد: {cabinet.get('economy', '❌')}
🕵️ اطلاعات: {cabinet.get('intelligence', '❌')}
━━━━━━━━━━━━━━━━━━

💰 **اقتصاد**
━━━━━━━━━━━━━━━━━━
💰 خزانه: {user.get('credit', 50000):,} سکه
📈 سود روزانه: {user.get('daily_profit', 0):,}

🛡 **قدرت نظامی**
━━━━━━━━━━━━━━━━━━
🛡 استقامت: {user.get('defense', 5000):,}
💥 قدرت تخریب: {user.get('attack_power', 0):,}"""


def send_dashboard(chat_id, user_id):
    """نمایش داشبورد اصلی — با editMessageText + Reply Keyboard
    
    چیدمان دکمه‌های Inline:
    [🏆 لیدربرد] [🤝 اتحاد]
    [💰 فروشگاه تومان] [💵 فروشگاه سکه]
    [📦 تجهیزات من] [📊 اطلاعات من]
    [📢 بیانیه] [🏗️ پایگاه‌ها]
    [⚔️ حمله]                       ← پایین‌ترین
    """
    # 🔄 lazy import برای جلوگیری از حلقه import
    from .cabinet import send_cabinet_question

    # 🔒 گارد کابینه: اگر کابینه ناقص است، اول کابینه
    if user_in_cabinet_setup.get(user_id):
        state.menu_message.pop(str(chat_id), None)
        send_message(chat_id, "⚠️ **لطفاً ابتدا کابینه خود را تکمیل کنید!**")
        send_cabinet_question(chat_id, user_id)
        return

    # 📌 ارسال Reply Keyboard (فقط یک بار برای هر کاربر)
    send_reply_keyboard(chat_id, user_id)

    dashboard = get_dashboard_text(user_id)
    keyboard = {
        "inline_keyboard": [
            [{"text": "🏆 لیدربرد", "callback_data": "leaderboard"}, {"text": "🤝 اتحاد", "callback_data": "alliance"}],
            [{"text": "💰 فروشگاه (تومان)", "callback_data": "shop_toman"}, {"text": "💵 فروشگاه (سکه)", "callback_data": "shop_menu"}],
            [{"text": "📦 تجهیزات من", "callback_data": "my_equipment"}, {"text": "📊 اطلاعات من", "callback_data": "my_info"}],
            [{"text": "📢 بیانیه", "callback_data": "statement_menu"}, {"text": "🏗️ پایگاه‌ها", "callback_data": "bases_menu"}],
            [{"text": "⚔️ حمله", "callback_data": "attack_menu"}]
        ]
    }
    if is_admin(user_id):
        keyboard["inline_keyboard"].append([{"text": "👑 پنل ادمین", "callback_data": "admin_panel"}])
        keyboard["inline_keyboard"].append([{"text": "🌐 سازمان ملل", "callback_data": "un_panel"}])
        keyboard["inline_keyboard"].append([{"text": "🔐 تغییر کدهای همه بازیکنان", "callback_data": "admin_change_all_codes"}])
    show_screen(chat_id, dashboard, keyboard)


def show_my_info(chat_id, user_id):
    """نمایش اطلاعات کامل بازیکن — با دکمه بازگشت (editMessageText)"""
    user = players_data.get(user_id, {})
    country = user.get("country", "نامشخص")
    continent = get_country_continent_key(country)
    text = f"""📊 **اطلاعات شما:**
━━━━━━━━━━━━━━━━━━
🌍 کشور: {country}
🗺️ قاره: {CONTINENT_NAMES.get(continent, 'نامشخص')}
🆔 آیدی: {user_id}
💰 سکه: {user.get('credit', 0):,}
🛡 استقامت: {user.get('defense', 0):,}
💥 قدرت تخریب: {user.get('attack_power', 0):,}
📈 سود روزانه: {user.get('daily_profit', 0):,}
👥 جمعیت: {user.get('population', 10000):,}"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔄 بروزرسانی", "callback_data": "my_info"}],
            [{"text": "🔙 بازگشت به داشبورد", "callback_data": "dashboard"}]
        ]
    }
    show_screen(chat_id, text, keyboard)


def send_my_equipment(chat_id, user_id):
    """📦 نمایش کامل تجهیزات بازیکن — با editMessageText"""
    user = players_data.get(user_id, {})
    
    credit = user.get('credit', 0)
    daily_profit = user.get('daily_profit', 0)
    defense = user.get('defense', 5000)
    attack_power = user.get('attack_power', 0)
    score = user.get('score', 0)
    population = user.get('population', 10000)
    
    # معادن
    emerald = user.get('emerald_count', 0)
    iron = user.get('iron_count', 0)
    silver = user.get('silver_count', 0)
    bronze = user.get('bronze_count', 0)
    diamond = user.get('diamond_count', 0)
    gold = user.get('gold_count', 0)
    
    # ساختمان‌ها
    normal_hospital = user.get('normal_hospital_count', 0)
    professional_hospital = user.get('professional_hospital_count', 0)
    barracks = user.get('barracks_count', 0)
    metro = user.get('metro_count', 0)
    airport = user.get('airport_count', 0)
    dock = user.get('dock_count', 0)
    
    # پدافندها
    normal_defense = user.get('normal_air_defense_count', 0)
    sling_defense = user.get('sling_air_defense_count', 0)
    patriot_defense = user.get('patriot_air_defense_count', 0)
    s400_defense = user.get('s400_air_defense_count', 0)
    iron_dome_defense = user.get('iron_dome_air_defense_count', 0)
    
    # تانک‌ها
    simple_tank = user.get('simple_tank_count', 0)
    zolfaghar_tank = user.get('zolfaghar_tank_count', 0)
    karrar_tank = user.get('karrar_tank_count', 0)
    merkava_tank = user.get('merkava_tank_count', 0)
    challenger_tank = user.get('challenger_tank_count', 0)
    leclerc_tank = user.get('leclerc_tank_count', 0)
    torpedo_tank = user.get('torpedo_tank_count', 0)
    black_panther_tank = user.get('black_panther_tank_count', 0)
    leopard_tank = user.get('leopard_tank_count', 0)
    abrams_tank = user.get('abrams_tank_count', 0)
    
    # جنگنده‌ها
    f4_fighter = user.get('f4_fighter_count', 0)
    f18_fighter = user.get('f18_fighter_count', 0)
    j10_fighter = user.get('j10_fighter_count', 0)
    j16_fighter = user.get('j16_fighter_count', 0)
    f16_fighter = user.get('f16_fighter_count', 0)
    su27_fighter = user.get('su27_fighter_count', 0)
    eurofighter = user.get('eurofighter_fighter_count', 0)
    j17_fighter = user.get('j17_fighter_count', 0)
    golden_eagle = user.get('golden_eagle_fighter_count', 0)
    j20_fighter = user.get('j20_fighter_count', 0)
    su35_fighter = user.get('su35_fighter_count', 0)
    su57_fighter = user.get('su57_fighter_count', 0)
    f35_fighter = user.get('f35_fighter_count', 0)
    su75_fighter = user.get('su75_fighter_count', 0)
    f22_fighter = user.get('f22_fighter_count', 0)
    
    # هلیکوپترها
    normal_heli = user.get('normal_helicopter_count', 0)
    cobra_heli = user.get('cobra_helicopter_count', 0)
    littlebird_heli = user.get('littlebird_helicopter_count', 0)
    tiger_heli = user.get('tiger_helicopter_count', 0)
    crocodile_heli = user.get('crocodile_helicopter_count', 0)
    shamook_heli = user.get('shamook_helicopter_count', 0)
    kamov52_heli = user.get('kamov52_helicopter_count', 0)
    ah47_heli = user.get('ah47_helicopter_count', 0)
    apache_heli = user.get('apache_helicopter_count', 0)
    
    # موشک‌ها
    point_missile = user.get('point_missile_count', 0)
    cruise_missile = user.get('cruise_missile_count', 0)
    ghadir_missile = user.get('ghadir_missile_count', 0)
    khorramshahr_missile = user.get('khorramshahr_missile_count', 0)
    sejil_missile = user.get('sejil_missile_count', 0)
    fatah_missile = user.get('fatah_missile_count', 0)
    tomahawk_missile = user.get('tomahawk_missile_count', 0)
    iskander_missile = user.get('iskander_missile_count', 0)
    dongfeng_missile = user.get('dongfeng_missile_count', 0)
    kinzhal_missile = user.get('kinzhal_missile_count', 0)
    hypersonic_missile = user.get('hypersonic_missile_count', 0)
    
    # هکرها
    weak_hacker = user.get('weak_hacker_count', 0)
    medium_hacker = user.get('medium_hacker_count', 0)
    strong_hacker = user.get('strong_hacker_count', 0)
    
    # نیروی دریایی
    simple_warship = user.get('simple_warship_naval_count', 0)
    
    # ناوهای هواپیمابر
    washington_carrier = user.get('washington_carrier_count', 0)
    queen_carrier = user.get('queen_elizabeth_carrier_count', 0)
    kuznetsov_carrier = user.get('kuznetsov_carrier_count', 0)
    lincoln_carrier = user.get('abraham_lincoln_carrier_count', 0)
    ford_carrier = user.get('gerald_ford_carrier_count', 0)
    
    # زیردریایی
    combat_sub = user.get('combat_sub_submarine_count', 0)
    
    # نیروی زمینی
    normal_soldier = user.get('normal_soldier_ground_count', 0)
    professional_soldier = user.get('professional_soldier_ground_count', 0)
    border_guard = user.get('border_guard_ground_count', 0)
    commando = user.get('commando_ground_count', 0)
    bodyguard = user.get('bodyguard_ground_count', 0)
    
    # توپخانه
    anti_ground_art = user.get('anti_ground_artillery_count', 0)
    towed_art = user.get('towed_artillery_count', 0)
    braveheart_art = user.get('braveheart_artillery_count', 0)
    defense_art = user.get('defense_artillery_count', 0)
    
    # بمب‌ها
    fire_bomb = user.get('fire_bomb_count', 0)
    space_bomb = user.get('space_bomb_count', 0)
    continental_bomb = user.get('continental_bomb_count', 0)
    
    # پهپادها
    ghaza_drone = user.get('ghaza_drone_count', 0)
    surveillance_drone = user.get('surveillance_drone_count', 0)
    suicide_drone = user.get('suicide_drone_count', 0)
    hermes_drone = user.get('hermes_drone_count', 0)
    shahed_drone = user.get('shahed_drone_count', 0)
    mk1_drone = user.get('mk1_drone_count', 0)
    mk9_drone = user.get('mk9_drone_count', 0)
    jetx147_drone = user.get('jetx147_drone_count', 0)
    rq170_drone = user.get('rq170_drone_count', 0)
    
    # خلبان‌ها
    helicopter_pilot = user.get('helicopter_pilot_count', 0)
    normal_pilot = user.get('normal_pilot_count', 0)
    strong_pilot = user.get('strong_pilot_count', 0)
    professional_pilot = user.get('professional_pilot_count', 0)
    
    # محاسبه جنگنده‌ها و هلیکوپترهای آماده
    ready_fighters = 0
    ready_fighters += min(f4_fighter, normal_pilot)
    ready_fighters += min(f18_fighter, normal_pilot)
    ready_fighters += min(j10_fighter, normal_pilot)
    ready_fighters += min(j16_fighter, normal_pilot)
    ready_fighters += min(f16_fighter, normal_pilot)
    ready_fighters += min(su27_fighter, normal_pilot)
    ready_fighters += min(eurofighter, strong_pilot)
    ready_fighters += min(j17_fighter, strong_pilot)
    ready_fighters += min(golden_eagle, strong_pilot)
    ready_fighters += min(j20_fighter, strong_pilot)
    ready_fighters += min(su35_fighter, strong_pilot)
    ready_fighters += min(su57_fighter, professional_pilot)
    ready_fighters += min(f35_fighter, professional_pilot)
    ready_fighters += min(su75_fighter, professional_pilot)
    ready_fighters += min(f22_fighter, professional_pilot)
    
    total_helicopters = (normal_heli + cobra_heli + littlebird_heli + tiger_heli + 
                         crocodile_heli + shamook_heli + kamov52_heli + ah47_heli + apache_heli)
    ready_helicopters = min(total_helicopters, helicopter_pilot)
    
    text = f"""📦 **تجهیزات من** ━━━━━━━━━━━━━━━━━━

📊 **آمار کلی**
━━━━━━━━━━━━━━━━━━
💰 سکه: {credit:,}
📈 سود روزانه: {daily_profit:,}
🛡 استقامت: {defense:,}
💥 قدرت تخریب: {attack_power:,}
🏆 امتیاز: {score}
👥 جمعیت: {population:,}

✈️ **وضعیت پرواز**
━━━━━━━━━━━━━━━━━━
🟢 جنگنده آماده: {ready_fighters} عدد
🚁 هلیکوپتر آماده: {ready_helicopters} عدد

━━━━━━━━━━━━━━━━━━
⚙️ **تانک‌ها**
━━━━━━━━━━━━━━━━━━
🟢 ساده: {simple_tank} | 🟢 ذوالفقار: {zolfaghar_tank}
🟢 کرار: {karrar_tank} | 🟢 مرکاوا: {merkava_tank}
🟢 چلنجر: {challenger_tank} | 🟢 لکرک: {leclerc_tank}
🟢 اژدر: {torpedo_tank} | 🟢 بلک پنتر: {black_panther_tank}
🟢 لئوپارد: {leopard_tank} | 🟢 ابرامز: {abrams_tank}

━━━━━━━━━━━━━━━━━━
✈️ **جنگنده‌ها**
━━━━━━━━━━━━━━━━━━
🟡 اف4: {f4_fighter} | 🟡 اف18: {f18_fighter}
🟡 جی10: {j10_fighter} | 🟡 جی16: {j16_fighter}
🟡 اف16: {f16_fighter} | 🟡 سوخو27: {su27_fighter}
🟡 یوروفایتر: {eurofighter} | 🟡 جی17: {j17_fighter}
🟡 گلدن ایگل: {golden_eagle} | 🟡 جی20: {j20_fighter}
🟡 سوخو35: {su35_fighter} | 🟡 سوخو57: {su57_fighter}
🟡 اف35: {f35_fighter} | 🟡 سوخو75: {su75_fighter}
🟡 اف22: {f22_fighter}

━━━━━━━━━━━━━━━━━━
🚁 **هلیکوپترها**
━━━━━━━━━━━━━━━━━━
⚫ عادی: {normal_heli} | ⚫ کبری: {cobra_heli}
⚫ لیتل برد: {littlebird_heli} | ⚫ تایگر: {tiger_heli}
⚫ تمساح: {crocodile_heli} | ⚫ شاموک: {shamook_heli}
⚫ کاموف52: {kamov52_heli} | ⚫ ای اچ47: {ah47_heli}
⚫ آپاچی: {apache_heli}

━━━━━━━━━━━━━━━━━━
🚀 **موشک‌ها**
━━━━━━━━━━━━━━━━━━
🔴 نقطه زن: {point_missile} | 🔴 کروز: {cruise_missile}
🔴 قدر: {ghadir_missile} | 🔴 خرمشهر: {khorramshahr_missile}
🔴 سجیل: {sejil_missile} | 🔴 فتاح: {fatah_missile}
🔴 تاماهاوک: {tomahawk_missile} | 🔴 اسکندر: {iskander_missile}
🔴 دانگ فنگ: {dongfeng_missile} | 🔴 کینژال: {kinzhal_missile}
🔴 هایپرسونیک: {hypersonic_missile}

━━━━━━━━━━━━━━━━━━
🚢 **نیروی دریایی**
━━━━━━━━━━━━━━━━━━
🚢 ناو جنگی: {simple_warship}

🐋 **زیردریایی‌ها**
━━━━━━━━━━━━━━━━━━
🐋 زیردریایی: {combat_sub}

🚢 **ناو هواپیمابر**
━━━━━━━━━━━━━━━━━━
🔴 واشنگتن: {washington_carrier} | 🔴 ملکه الیزابت: {queen_carrier}
🔴 کوزنتسوف: {kuznetsov_carrier} | 🔴 لینکلن: {lincoln_carrier}
🔴 جرالد فورد: {ford_carrier}

━━━━━━━━━━━━━━━━━━
🛡️ **پدافندها**
━━━━━━━━━━━━━━━━━━
🔴 عادی: {normal_defense} | 🔴 فلاخن: {sling_defense}
🔴 پاتریوت: {patriot_defense} | 🔴 اس400: {s400_defense}
🔴 گنبد آهنین: {iron_dome_defense}

━━━━━━━━━━━━━━━━━━
🥷🏻 **نیروی زمینی**
━━━━━━━━━━━━━━━━━━
⚫ سرباز عادی: {normal_soldier} | ⚫ حرفه‌ای: {professional_soldier}
⚫ مرزبان: {border_guard} | ⚫ تکاور: {commando}
⚫ بادیگارد: {bodyguard}

━━━━━━━━━━━━━━━━━━
⚔️ **توپخانه**
━━━━━━━━━━━━━━━━━━
⚪ ضد زمینی: {anti_ground_art} | ⚪ یدک کش: {towed_art}
⚪ بریوهارت: {braveheart_art} | ⚪ پدافند دار: {defense_art}

━━━━━━━━━━━━━━━━━━
💣 **بمب‌ها**
━━━━━━━━━━━━━━━━━━
⚫ آتش زا: {fire_bomb} | ⚫ فضاپیل: {space_bomb}
⚫ قاره‌ای: {continental_bomb}

━━━━━━━━━━━━━━━━━━
👨‍💻 **هکرها**
━━━━━━━━━━━━━━━━━━
🟡 ضعیف: {weak_hacker} | 🟠 متوسط: {medium_hacker} | 🔴 قوی: {strong_hacker}

━━━━━━━━━━━━━━━━━━
👨‍✈️ **خلبان‌ها**
━━━━━━━━━━━━━━━━━━
🚁 هلیکوپتر: {helicopter_pilot}
🟠 عادی (اف4 تا سوخو27): {normal_pilot}
🔴 قوی (یوروفایتر تا سوخو35): {strong_pilot}
⭐ حرفه‌ای (سوخو57 تا اف22): {professional_pilot}

━━━━━━━━━━━━━━━━━━
🛸 **پهبادها**
━━━━━━━━━━━━━━━━━━
🔵 غزه: {ghaza_drone} | 🔵 نظارتی: {surveillance_drone}
🔵 انتحاری: {suicide_drone} | 🔵 هرمس: {hermes_drone}
🔵 شاهد136: {shahed_drone} | 🔵 ام کی1: {mk1_drone}
🔵 ام کی9: {mk9_drone} | 🔵 جت ایکس147: {jetx147_drone}
🔵 ار کیو170: {rq170_drone}

━━━━━━━━━━━━━━━━━━
🏗️ **ساختمان‌ها**
━━━━━━━━━━━━━━━━━━
🏥 بیمارستان عادی: {normal_hospital}
🏥 بیمارستان حرفه‌ای: {professional_hospital}
🛕 پادگان: {barracks}
🚉 مترو: {metro}
🛬 فرودگاه: {airport}
⛴️ اسکله: {dock}

━━━━━━━━━━━━━━━━━━
⛏️ **معادن**
━━━━━━━━━━━━━━━━━━
🟢 زمرد: {emerald} | ⚪ آهن: {iron}
⚫ نقره: {silver} | 🟠 برنز: {bronze}
🔵 الماس: {diamond} | 🟡 طلا: {gold}
━━━━━━━━━━━━━━━━━━"""

    keyboard = {
        "inline_keyboard": [
            [{"text": "🔄 بروزرسانی", "callback_data": "my_equipment"}],
            [{"text": "🔙 بازگشت به داشبورد", "callback_data": "dashboard"}]
        ]
    }
    show_screen(chat_id, text, keyboard)


# ==================== بیانیه و توییت ====================
def send_statement_menu(chat_id, user_id):
    """منوی بیانیه با نمایش محدودیت — با editMessageText"""
    can_send, remaining, wait_time = can_send_statement(user_id)
    
    if not can_send:
        hours, minutes = wait_time
        keyboard = {
            "inline_keyboard": [
                [{"text": "🐦 توییت", "callback_data": "new_tweet"}],
                [{"text": "🔙 بازگشت به داشبورد", "callback_data": "dashboard"}]
            ]
        }
        text = f"📢 **ارسال بیانیه**\n━━━━━━━━━━━━━━━━━━\n"
        text += f"⛔ **شما به محدودیت بیانیه رسیده‌اید!**\n"
        text += f"📊 حداکثر {STATEMENT_LIMIT} بیانیه در 24 ساعت\n"
        text += f"⏳ زمان تا آزاد شدن: {hours} ساعت {minutes} دقیقه\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"✅ اما می‌توانید توییت ارسال کنید (محدودیت ندارد):"
        show_screen(chat_id, text, keyboard)
        return
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📝 بیانیه", "callback_data": "new_statement"}, 
             {"text": "🐦 توییت", "callback_data": "new_tweet"}],
            [{"text": "🔙 بازگشت به داشبورد", "callback_data": "dashboard"}]
        ]
    }
    
    text = f"📢 **ارسال بیانیه**\n━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 بیانیه‌های باقیمانده امروز: {remaining}/{STATEMENT_LIMIT}\n"
    text += f"🕐 محدودیت: هر 24 ساعت، {STATEMENT_LIMIT} بیانیه\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    text += f"✅ توییت محدودیت ندارد!\n\n"
    text += f"نوع مطلب را انتخاب کن:"
    
    show_screen(chat_id, text, keyboard)


def send_statement_to_group(chat_id, user_id, text):
    """ارسال بیانیه به گروه با بررسی محدودیت"""
    can_send, remaining, wait_time = can_send_statement(user_id)
    
    if not can_send:
        hours, minutes = wait_time
        send_message(chat_id, 
            f"❌ **شما به محدودیت بیانیه رسیده‌اید!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 حداکثر {STATEMENT_LIMIT} بیانیه در 24 ساعت\n"
            f"⏳ زمان تا آزاد شدن: {hours} ساعت {minutes} دقیقه\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 اما می‌توانید توییت ارسال کنید (محدودیت ندارد)")
        return
    
    user = players_data.get(user_id, {})
    msg = f"""📢 **بیانیه رسمی**
━━━━━━━━━━━━━━━━━━
🇮🇷 کشور: {user.get('country', 'نامشخص')}
👤 فرمانده: {user.get('player_name', 'نامشخص')}

📝 {text}

🕐 {time.strftime('%Y/%m/%d - %H:%M')}"""
    
    send_to_group(msg)
    add_statement_record(user_id)
    _, remaining_after, _ = can_send_statement(user_id)
    
    send_message(chat_id, 
        f"✅ **بیانیه ارسال شد!**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 بیانیه‌های باقیمانده امروز: {remaining_after}/{STATEMENT_LIMIT}")


def send_tweet_to_group(chat_id, user_id, text):
    """ارسال توییت به گروه (بدون محدودیت)"""
    user = players_data.get(user_id, {})
    msg = f"""🐦 **توییت رسمی**
━━━━━━━━━━━━━━━━━━
🇮🇷 {user.get('country', 'نامشخص')} | 👤 {user.get('player_name', 'نامشخص')}

{text}

🕐 {time.strftime('%Y/%m/%d - %H:%M')}
❤️ {random.randint(0, 100)} لایک - 🔄 {random.randint(0, 20)} ری‌توییت"""
    send_to_group(msg)
    send_message(chat_id, "✅ توییت ارسال شد!")


# ==================== دعوت دوستان ====================
def send_invite_message(chat_id, user_id):
    """ارسال پیام و لینک دعوت به دوستان (برای تلگرام)"""
    # 🔧 یوزرنیم ربات رو اینجا بذار (بدون @)
    BOT_USERNAME = "WWar3_bot"  # ← یوزرنیم ربات خودت
    
    message1 = "🎁 این بنر را برای دوستانتان ارسال کنید و 10,000 سکه جایزه بگیرید🎁🎁"
    send_message(chat_id, message1)
    
    invite_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    
    message2 = f"""سلام دوست من 👋

⭐ **بهترین بازی جنگ جهانی بالاخره از راه رسید!** ⚔️

🚀 همین الان از لینک زیر شروع کن:
🔗 {invite_link}

🎁 با وارد شدن شما، دوستتان 10,000 سکه جایزه می‌گیرد!"""
    
    send_message(chat_id, message2)
    keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت به داشبورد", "callback_data": "dashboard"}]]}
    show_screen(chat_id, "━━━━━━━━━━━━━━━━━━\nبرای بازگشت کلیک کن:", keyboard)