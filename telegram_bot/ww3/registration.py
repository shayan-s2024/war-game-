# -*- coding: utf-8 -*-
"""سیستم ثبت‌نام، ظرفیت بازی و گیت ضد اکانت بی‌نام.

فلو جدید ثبت‌نام:
  /start → دکمه شروع → دریافت «نام بازیکن» (پیام تغییر نمی‌کند)
       → انتخاب کشور (پیام جدید)
       → کابینه (همه در یک پیام، با editMessageText)
       → دریافت کدهای امنیتی (پیام جدید)
       → پیام خوش‌آمد (پیام جدید)
       → داشبورد (پیام جدید)
       → Reply Keyboard با «🚀 شروع» و «🔄 بروزرسانی»

قوانین سخت‌گیرانه:
  ۱) هیچ کدی نباید مستقیم players_data[user_id] بسازد؛ رکورد فقط با نام ساخته می‌شود.
  ۲) بعد از پر شدن ظرفیت (یا بسته شدن دستی)، هیچ کاربر جدیدی نمی‌تواند
     اکانت بسازد — حتی با دکمه‌های قدیمی یا لینک دعوت.
  ۳) وضعیت باز/بسته بودن ثبت‌نام در دیتابیس ذخیره می‌شود و با ری‌استارت بات نمی‌پرد.
"""
import time

from . import state
from .config import (REQUIRED_CHANNELS, TG, BASE_URL)
from .state import (db, players_data, used_countries, waiting_for_name,
                    waiting_for_country_selection, waiting_for_cabinet,
                    user_in_cabinet_setup)
from .static_data import (MINES, BUILDINGS, AIR_DEFENSES, TANKS, FIGHTERS,
                          HELICOPTERS, MISSILES, HACKERS, BOMBS, PILOTS, DRONES,
                          NAVAL_VESSELS, AIRCRAFT_CARRIERS, SUBMARINES,
                          GROUND_FORCES, ARTILLERY, COUNTRIES_LIST, CONTINENT_NAMES)
from .helpers import (send_message, show_screen, edit_message, get_total_countries_count,
                      get_country_continent, generate_all_cabinet_codes, is_admin,
                      get_missing_channels, send_reply_keyboard)

# ==================== وضعیت ظرفیت و ثبت‌نام ====================
REG_CLOSED_KEY = "registration_closed"


def is_registration_closed():
    """آیا ادمین ثبت‌نام را دستی بسته است؟"""
    return db.get_game_config(REG_CLOSED_KEY, "0") == "1"


def set_registration_closed(closed):
    """بستن/باز کردن ثبت‌نام به صورت ماندگار"""
    db.set_game_config(REG_CLOSED_KEY, "1" if closed else "0")


def is_registered_player(user_id):
    """آیا کاربر یک بازیکن کامل (با نام) است؟"""
    p = players_data.get(user_id)
    return bool(p and p.get("player_name"))


def is_registration_available():
    """بررسی آیا ظرفیت ثبت‌نام وجود دارد → (available, message)"""
    if is_registration_closed():
        return False, "🔒 **ثبت‌نام جدید بسته شده است!**\nتمام کشورهای جهان پر شده‌اند."

    total_countries = get_total_countries_count()
    used_countries_count = len(used_countries)

    if used_countries_count >= total_countries:
        return False, "🌍 **تمام کشورهای جهان پر شده‌اند!**\nدیگر نمی‌توانید ثبت‌نام کنید."

    remaining = total_countries - used_countries_count
    return True, f"✅ {remaining} کشور باقی‌مانده است."


def purge_junk_players():
    """پاکسازی استارت: حذف اکانت‌های بی‌نام + آزادسازی کشورهای بدون صاحب معتبر"""
    junk = [uid for uid, p in players_data.items()
            if not p.get("player_name") and not p.get("country")]
    for uid in junk:
        db.delete_player(uid)
        db.delete_pending_referral(uid)
        players_data.pop(uid, None)
        waiting_for_name.pop(uid, None)
        waiting_for_country_selection.pop(uid, None)
        waiting_for_cabinet.pop(uid, None)
        user_in_cabinet_setup.pop(uid, None)
    # 🔒 کشورهای رزروشده‌ای که صاحب معتبر ندارند آزاد می‌شوند
    orphans = [c for c, uid in used_countries.items()
               if uid not in players_data or players_data[uid].get("country") != c]
    for c in orphans:
        used_countries.pop(c, None)
        db.remove_country(c)
    if orphans:
        print(f"🌍 {len(orphans)} کشور بدون صاحب معتبر آزاد شد")
    return len(junk)


# ==================== معرفی دوستان (بدون ساخت اکانت) ====================
def process_referral(user_id, referrer_id):
    """ثبت معرفی — هیچ اکانتی ساخته نمی‌شود!"""
    if not referrer_id or referrer_id == user_id:
        return
    referrer = players_data.get(referrer_id)
    if not referrer or not referrer.get("player_name"):
        return
    existing = players_data.get(user_id)
    if existing and existing.get("referred_by"):
        return
    if existing and existing.get("player_name"):
        # کاربر قبلاً ثبت‌نام کامل کرده — جایزه فوری
        _award_referral(user_id, referrer_id)
        return
    # کاربر هنوز ثبت‌نام نکرده → بعد از ثبت نام پرداخت می‌شود
    db.set_pending_referral(user_id, referrer_id)


def _award_referral(user_id, referrer_id):
    """پرداخت جایزه معرفی"""
    players_data[referrer_id]["credit"] = players_data[referrer_id].get("credit", 0) + 10000
    players_data[referrer_id]["invite_count"] = players_data[referrer_id].get("invite_count", 0) + 1
    players_data[user_id]["referred_by"] = referrer_id
    db.save_player(referrer_id, players_data[referrer_id])
    db.save_player(user_id, players_data[user_id])
    db.delete_pending_referral(user_id)
    try:
        send_message(int(referrer_id), "🎉 تبریک! یکی از دوستان شما وارد بازی شد!\n💰 10,000 سکه به حساب شما اضافه شد.")
    except Exception:
        pass


def award_pending_referral(user_id):
    """پرداخت جایزه معرفی — فقط پس از ثبت نام بازیکن"""
    referrer_id = db.get_pending_referral(user_id)
    if not referrer_id:
        return
    referrer = players_data.get(referrer_id)
    if not referrer or not referrer.get("player_name"):
        return
    _award_referral(user_id, referrer_id)


# ==================== مرحله ۱: نام بازیکن (اجباری) ====================
def start_name_input(chat_id, user_id):
    """شروع مرحله دریافت نام — اولین و اجباری‌ترین مرحله ثبت‌نام"""
    waiting_for_name[user_id] = True
    existing = players_data.get(user_id, {})
    if existing.get("country"):
        send_message(chat_id,
            "👤 **نام بازیکن شما ثبت نشده است!**\n\n"
            "برای ادامه بازی، نام خود را وارد کنید (۳ تا ۳۰ کاراکتر):")
    else:
        send_message(chat_id,
            "👤 **خوش آمدید!** ⚔️\n\n"
            "برای شروع ثبت‌نام، نام بازیکن خود را وارد کنید (۳ تا ۳۰ کاراکتر):\n"
            "💡 این نام به عنوان نام رسمی کشور شما ثبت می‌شود.")


def process_name_input(chat_id, user_id, text):
    """ثبت نام بازیکن و ادامه فلو ثبت‌نام (نام → کشور → کابینه)"""
    from .dashboard import send_dashboard
    from .cabinet import send_cabinet_question

    text = (text or "").strip()
    if not (3 <= len(text) <= 30):
        send_message(chat_id, "❌ اسم باید ۳ تا ۳۰ کاراکتر باشد!")
        return

    # نام تکراری ممنوع
    for uid, p in players_data.items():
        if uid != user_id and (p.get("player_name") or "").strip() == text:
            send_message(chat_id, "❌ این نام قبلاً توسط بازیکن دیگری انتخاب شده! نام دیگری وارد کنید.")
            return

    existing = players_data.get(user_id)
    is_new = not existing

    if is_new:
        # رکورد فقط همین‌جا و فقط با نام ساخته می‌شود
        players_data[user_id] = {}
        players_data[user_id]["credit"] = 10000
        players_data[user_id]["score"] = 0
        players_data[user_id]["defense"] = 5000
        players_data[user_id]["attack_power"] = 0
        players_data[user_id]["daily_profit"] = 0
        players_data[user_id]["population"] = 10000

        # مقداردهی اولیه همه تجهیزات
        for key in MINES.keys():
            players_data[user_id][f"{key}_count"] = 0
        for key in BUILDINGS.keys():
            players_data[user_id][f"{key}_count"] = 0
        for key in AIR_DEFENSES.keys():
            players_data[user_id][f"{key}_air_defense_count"] = 0
        for key in TANKS.keys():
            players_data[user_id][f"{key}_tank_count"] = 0
        for key in FIGHTERS.keys():
            players_data[user_id][f"{key}_fighter_count"] = 0
        for key in HELICOPTERS.keys():
            players_data[user_id][f"{key}_helicopter_count"] = 0
        for key in MISSILES.keys():
            players_data[user_id][f"{key}_missile_count"] = 0
        for key in HACKERS.keys():
            players_data[user_id][f"{key}_hacker_count"] = 0
        for key in BOMBS.keys():
            players_data[user_id][f"{key}_bomb_count"] = 0
        for key in PILOTS.keys():
            players_data[user_id][f"{key}_pilot_count"] = 0
        for key in DRONES.keys():
            players_data[user_id][f"{key}_drone_count"] = 0
        for key in NAVAL_VESSELS.keys():
            players_data[user_id][f"{key}_naval_count"] = 0
        for key in AIRCRAFT_CARRIERS.keys():
            players_data[user_id][f"{key}_carrier_count"] = 0
        for key in SUBMARINES.keys():
            players_data[user_id][f"{key}_submarine_count"] = 0
        for key in GROUND_FORCES.keys():
            players_data[user_id][f"{key}_ground_count"] = 0
        for key in ARTILLERY.keys():
            players_data[user_id][f"{key}_artillery_count"] = 0

    players_data[user_id]["player_name"] = text
    db.save_player(user_id, players_data[user_id])
    waiting_for_name.pop(user_id, None)

    # جایزه معرفی فقط حالا پرداخت می‌شود
    award_pending_referral(user_id)

    user = players_data[user_id]

    # 🔑 فلو جدید: نام → کشور → کابینه
    if user.get("country"):
        # کاربر قبلاً کشور داشت (مثلاً فلو نیمه‌کاره)
        cabinet = user.get("cabinet", {})
        if len(cabinet) >= 5:
            send_message(chat_id, f"✅ نام شما ثبت شد: **{text}**")
            state.menu_message.pop(str(chat_id), None)
            # 📌 ارسال Reply Keyboard
            send_reply_keyboard(chat_id, user_id)
            send_dashboard(chat_id, user_id)
        else:
            waiting_for_cabinet[user_id] = {"step": 0, "answers": cabinet}
            user_in_cabinet_setup[user_id] = True
            send_message(chat_id, f"✅ نام شما ثبت شد: **{text}**\n\n👥 اکنون کابینه خود را تکمیل کنید:")
            state.menu_message.pop(str(chat_id), None)
            send_cabinet_question(chat_id, user_id)
    else:
        # کشور نداره → انتخاب کشور
        available, msg = is_registration_available()
        if not available:
            send_start_button_closed(chat_id, msg)
            return
        waiting_for_country_selection[user_id] = True
        send_message(chat_id, f"✅ نام شما ثبت شد: **{text}**\n\n🌍 اکنون کشور خود را انتخاب کنید:")
        state.menu_message.pop(str(chat_id), None)
        send_country_selection_menu(chat_id, user_id)


# ==================== مرحله ۲: انتخاب کشور ====================
def process_country_selection(chat_id, user_id, country_name):
    """پردازش انتخاب کشور و ادامه به کابینه"""
    from .dashboard import send_dashboard
    from .cabinet import send_cabinet_question

    # 🔒 کاربر بدون نام هیچ کشوری نمی‌تواند بگیرد
    if not (players_data.get(user_id, {}).get("player_name")):
        start_name_input(chat_id, user_id)
        return

    # 🔒 بازیکنی که قبلاً کشور دارد، کشور دوم نمی‌گیرد
    if players_data.get(user_id, {}).get("country"):
        send_message(chat_id, "⚠️ **شما قبلاً کشور دارید!** هر بازیکن فقط یک کشور.")
        state.menu_message.pop(str(chat_id), None)
        send_dashboard(chat_id, user_id)
        return

    # بررسی ظرفیت ثبت‌نام
    available, message = is_registration_available()
    if not available:
        send_message(chat_id, message)
        return

    # بررسی تکراری نبودن کشور
    if country_name in used_countries:
        owner_id = used_countries[country_name]
        owner_name = players_data.get(owner_id, {}).get("player_name", "کس دیگری")
        send_message(chat_id, f"❌ کشور '{country_name}' قبلاً توسط {owner_name} انتخاب شده است!")
        return

    # پیدا کردن قاره کشور
    continent_key, continent_name = get_country_continent(country_name)
    if not continent_key:
        send_message(chat_id, f"❌ کشور '{country_name}' معتبر نیست!")
        return

    # 🔒 چک مجدد ظرفیت درست قبل از رزرو
    if len(used_countries) >= get_total_countries_count():
        send_message(chat_id, "🌍 متأسفانه ظرفیت همین الان پر شد! دیگر نمی‌توانید ثبت‌نام کنید.")
        return

    # ذخیره کشور
    if user_id not in players_data:
        players_data[user_id] = {}

    players_data[user_id]["country"] = country_name
    players_data[user_id]["continent"] = continent_key
    used_countries[country_name] = user_id

    db.save_player(user_id, players_data[user_id])
    db.save_country(country_name, user_id)

    waiting_for_country_selection.pop(user_id, None)

    # بررسی آیا قبلاً کابینه داشته؟
    existing_cabinet = players_data[user_id].get("cabinet", {})

    # 🔑 فلو جدید: بعد از کشور → کابینه (یا داشبورد اگر کابینه کامله)
    if existing_cabinet and len(existing_cabinet) >= 5:
        # کابینه کامله → داشبورد (پیام جدید)
        send_message(chat_id, f"✅ کشور '{country_name}' در {continent_name} ثبت شد!")
        state.menu_message.pop(str(chat_id), None)
        # 📌 ارسال Reply Keyboard
        send_reply_keyboard(chat_id, user_id)
        send_dashboard(chat_id, user_id)
    else:
        # کابینه ناقص یا خالی → کابینه (پیام جدید)
        if existing_cabinet:
            waiting_for_cabinet[user_id] = {"step": 0, "answers": existing_cabinet}
            send_message(chat_id, f"✅ کشور '{country_name}' در {continent_name} ثبت شد!\n\n🔄 ادامه کابینه از جایی که مانده بود...")
        else:
            waiting_for_cabinet[user_id] = {"step": 0, "answers": {}}
            send_message(chat_id, f"✅ کشور '{country_name}' در {continent_name} ثبت شد!\n\n👥 اکنون کابینه خود را تکمیل کنید:")
        user_in_cabinet_setup[user_id] = True
        state.menu_message.pop(str(chat_id), None)
        send_cabinet_question(chat_id, user_id)


# ==================== تکمیل اطلاعات بازیکن‌های قدیمی ====================
def complete_player_info(chat_id, user_id):
    """تکمیل اطلاعات بازیکن (بر اساس وضعیت فعلی)"""
    from .dashboard import send_dashboard, send_admin_home
    from .cabinet import send_cabinet_question

    if user_id not in players_data:
        # 👑 ادمین بدون رکورد بازیکن → صفحه ادمین
        if is_admin(user_id):
            send_admin_home(chat_id, user_id)
            return
        available, msg = is_registration_available()
        if not available:
            send_start_button_closed(chat_id, msg)
        else:
            start_name_input(chat_id, user_id)
        return

    user = players_data.get(user_id, {})

    # اگر کاربر در حال حاضر در حالت کابینه است، از همانجا ادامه بده
    if user_in_cabinet_setup.get(user_id):
        send_cabinet_question(chat_id, user_id)
        return

    # 🔒 بدون نام هیچ مرحله‌ای ادامه پیدا نمی‌کند
    if not user.get("player_name"):
        start_name_input(chat_id, user_id)
        return

    has_country = user.get("country") and user.get("country") != ""
    existing_cabinet = user.get("cabinet", {})

    if has_country:
        # اگر کشور دارد، مستقیماً برو به کابینه
        cabinet_complete_count = len(existing_cabinet)

        if cabinet_complete_count >= 5:
            # کابینه کامله → داشبورد (پیام جدید)
            state.menu_message.pop(str(chat_id), None)
            # 📌 ارسال Reply Keyboard
            send_reply_keyboard(chat_id, user_id)
            send_dashboard(chat_id, user_id)
        else:
            # کابینه ناقصه → کابینه (پیام جدید)
            waiting_for_cabinet[user_id] = {"step": 0, "answers": existing_cabinet}
            user_in_cabinet_setup[user_id] = True
            send_message(chat_id, f"✅ کشور شما {user.get('country')} است.\n\n🔄 ادامه کابینه از جایی که مانده بود...")
            state.menu_message.pop(str(chat_id), None)
            send_cabinet_question(chat_id, user_id)
    else:
        # اگر کشور ندارد، ظرفیت چک شود و بعد برو به مرحله انتخاب کشور (پیام جدید)
        available, msg = is_registration_available()
        if not available:
            send_start_button_closed(chat_id, msg)
            return
        waiting_for_country_selection[user_id] = True
        state.menu_message.pop(str(chat_id), None)
        send_country_selection_menu(chat_id, user_id)


# ==================== جوین اجباری کانال ====================
def send_join_required(chat_id, user_id):
    """پیام عضویت اجباری + دکمه‌های کانال و دکمه بررسی مجدد"""
    missing = get_missing_channels(user_id)
    if not missing:
        return False
    buttons = [[{"text": f"📢 عضویت در {ch}",
                 "url": f"https://t.me/{ch.lstrip('@')}"}] for ch in missing]
    buttons.append([{"text": "✅ عضو شدم — بررسی کن", "callback_data": "check_join"}])
    send_message(chat_id,
        "🔒 **برای استفاده از ربات باید عضو کانال‌های زیر شوید:**\n\n"
        "1️⃣ روی دکمه‌های کانال بزنید و عضو شوید\n"
        "2️⃣ برگردید و دکمه «✅ عضو شدم» را بزنید\n\n"
        "⚠️ **تا عضو نشوید نمی‌توانید از ربات استفاده کنید** — حتی اگر قبلاً ثبت‌نام کرده باشید.",
        {"inline_keyboard": buttons})
    return True


def handle_check_join(chat_id, user_id):
    """دکمه «عضو شدم» — بررسی مجدد و ادامه مسیر عادی"""
    from .dashboard import send_dashboard, send_admin_home

    missing = get_missing_channels(user_id, force=True)
    if missing:
        send_message(chat_id,
            "❌ **هنوز عضو همه کانال‌ها نشده‌اید!**\n"
            "لطفاً ابتدا عضو کانال‌های بالا شوید و دوباره دکمه را بزنید.")
        send_join_required(chat_id, user_id)
        return
    state.join_check_cache[user_id] = ([], time.time())
    send_message(chat_id, "✅ **عضویت شما تایید شد! خوش آمدید.**")
    # ادامه مسیر عادی بر اساس وضعیت کاربر
    if is_registered_player(user_id):
        state.menu_message.pop(str(chat_id), None)
        # 📌 ارسال Reply Keyboard
        send_reply_keyboard(chat_id, user_id)
        send_dashboard(chat_id, user_id)
    elif is_admin(user_id):
        # 👑 ادمین بدون رکورد بازیکن → صفحه ادمین
        send_admin_home(chat_id, user_id)
    else:
        send_start_button(chat_id, user_id)


# ==================== دکمه‌های شروع ====================
def send_start_button(chat_id, user_id, is_existing_player=False):
    """ارسال دکمه شروع با توجه به وضعیت بازیکن"""
    
    if is_existing_player:
        # بازیکنی که قبلاً ثبت‌نام کرده ولی اطلاعاتش ناقص است
        keyboard = {"inline_keyboard": [[{"text": "🎮 تکمیل اطلاعات", "callback_data": "complete_info"}]]}
        text = """⚠️ **اطلاعات شما ناقص است!** ⚠️

برای ادامه بازی، باید اطلاعات خود را تکمیل کنید.

🔘 روی دکمه زیر کلیک کنید:
🎮 **تکمیل اطلاعات**"""
    else:
        # بازیکن جدید
        keyboard = {"inline_keyboard": [[{"text": "🎮 شروع بازی", "callback_data": "start_game"}]]}
        text = """🔥 **به بازی جنگ جهانی خوش اومدی!** 🌍

⚔️ یک بازی استراتژیک جنگی در مقیاس جهانی!

🎁 **جوایز شروع بازی:**
💰 10,000 سکه طلا
🛡 5,000 استقامت اولیه
👥 10,000 جمعیت
🏆 0 امتیاز

🌍 از بین 450 کشور جهان، کشورت رو انتخاب کن!
👑 کابینه خودت رو تشکیل بده!
⚔️ در جنگ‌های جهانی شرکت کن و غنیمت بگیر!
🤝 با دوستانت اتحاد تشکیل بده!

برای شروع کلیک کن 👇"""
    
    send_message(chat_id, text, keyboard)


def send_start_button_closed(chat_id, message):
    """دکمه شروع وقتی ظرفیت پر است یا ثبت‌نام بسته شده"""
    keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "dashboard"}]]}
    text = f"""🔥 **به بازی جنگ جهانی خوش اومدی!** 🌍

⚠️ **{message}**

📊 **آمار فعلی:**
• کل کشورهای جهان: {get_total_countries_count()}
• کشورهای پر شده: {len(used_countries)}
• کشورهای خالی: {get_total_countries_count() - len(used_countries)}

🔜 در صورت آزاد شدن کشورها، می‌توانید ثبت‌نام کنید."""
    send_message(chat_id, text, keyboard)


# ==================== انتخاب کشور (با پیام جدید — نه edit) ====================
def send_country_selection_menu(chat_id, user_id):
    """نمایش منوی انتخاب قاره — 📌 پیام جدید"""
    keyboard = [[{"text": f"{data['flag']} {data['name']}", "callback_data": f"continent_{key}"}] for key, data in COUNTRIES_LIST.items()]
    keyboard.append([{"text": "🔙 بازگشت", "callback_data": "dashboard"}])
    # 📌 از send_message استفاده می‌کنیم نه show_screen — پیام جدید
    send_message(chat_id, "🌍 **انتخاب کشور**\n\nابتدا قاره خود را انتخاب کنید:", {"inline_keyboard": keyboard})


def send_countries_of_continent(chat_id, continent_key):
    """نمایش کشورهای یک قاره — 📌 پیام جدید"""
    continent_data = COUNTRIES_LIST.get(continent_key, {})
    countries = continent_data.get("countries", {})
    keyboard = []
    row = []
    for country_name, country_info in countries.items():
        is_taken = country_name in used_countries
        display = f"{country_info['emoji']} {country_name} {'❌' if is_taken else '✅'}"
        row.append({"text": display, "callback_data": f"select_country_{country_name}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    total = len(countries)
    taken = sum(1 for c in countries if c in used_countries)
    header = (f"{continent_data['flag']} **{continent_data['name']}**\n"
              f"📊 {taken}/{total} کشور پر شده\n"
              f"🌍 مجموع کشورهای جهان: {get_total_countries_count()}")
    # تلگرام حداکثر ۱۰۰ دکمه در هر پیام قبول می‌کند — تکه‌تکه ارسال می‌شود
    chunks = [keyboard[i:i + 45] for i in range(0, len(keyboard), 45)]
    for ci, part in enumerate(chunks):
        kb = list(part)
        if ci == len(chunks) - 1:
            kb.append([{"text": "🔙 بازگشت", "callback_data": "back_to_continents"}])
        text = header if ci == 0 else f"{continent_data['flag']} {continent_data['name']} — ادامه ({ci + 1})"
        # 📌 پیام جدید (نه edit)
        send_message(chat_id, text, {"inline_keyboard": kb})