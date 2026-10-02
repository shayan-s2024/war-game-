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
from .helpers import generate_all_cabinet_codes, send_message, send_to_group, edit_message, send_reply_keyboard
from .state import db, players_data, user_in_cabinet_setup, waiting_for_cabinet, waiting_for_cabinet_manual
from .static_data import CABINET_KEYS, CABINET_OPTIONS

# ==================== ماژول cabinet ====================


def start_cabinet_selection(chat_id, user_id):
    """شروع فرآیند کابینه"""
    user_in_cabinet_setup[user_id] = True
    waiting_for_cabinet[user_id] = {"step": 0, "answers": {}}
    send_cabinet_question(chat_id, user_id)


def send_cabinet_question(chat_id, user_id, message_id=None):
    """نمایش لیست اصلی کابینه — با editMessageText اگر message_id داده شده"""
    from .dashboard import send_dashboard

    if user_id not in waiting_for_cabinet:
        send_dashboard(chat_id, user_id)
        return

    answers = waiting_for_cabinet[user_id].get("answers", {})

    # ساخت دکمه‌ها برای همه ۵ مقام
    keyboard = []
    for key in CABINET_KEYS:
        option = CABINET_OPTIONS[key]
        icon = option["icon"]
        name = option["name"]
        chosen = answers.get(key)

        if chosen:
            keyboard.append([{
                "text": f"✅ {icon} {name}: {chosen}",
                "callback_data": f"cabinet_pick_{key}"
            }])
        else:
            keyboard.append([{
                "text": f"{icon} {name} — انتخاب کنید",
                "callback_data": f"cabinet_pick_{key}"
            }])

    # بررسی تکمیل بودن همه ۵ مقام
    all_chosen = all(answers.get(k) for k in CABINET_KEYS)

    # دکمه تایید نهایی
    if all_chosen:
        keyboard.append([{
            "text": "🎯 تایید نهایی و دریافت کدها",
            "callback_data": "cabinet_finish"
        }])

    # ساخت متن
    text = "👥 **تشکیل کابینه**\n━━━━━━━━━━━━━━━━━━\n"
    text += "برای هر یک از ۵ مقام، یک نفر را انتخاب کنید.\n\n"

    for key in CABINET_KEYS:
        option = CABINET_OPTIONS[key]
        icon = option["icon"]
        name = option["name"]
        chosen = answers.get(key, "❌ هنوز انتخاب نشده")
        text += f"{icon} **{name}**: {chosen}\n"

    text += "━━━━━━━━━━━━━━━━━━\n"
    if all_chosen:
        text += "✅ همه مقام‌ها انتخاب شدند! روی «تایید نهایی» بزنید."
    else:
        remaining = 5 - sum(1 for k in CABINET_KEYS if answers.get(k))
        text += f"📌 لطفاً {remaining} مقام دیگر را انتخاب کنید."

    inline_keyboard = {"inline_keyboard": keyboard}

    # 🔄 اگر message_id داشتیم، ویرایش کن. وگرنه پیام جدید بفرست.
    if message_id:
        result = edit_message(chat_id, message_id, text, inline_keyboard)
        if result:
            return
    # در غیر این صورت پیام جدید بفرست
    send_message(chat_id, text, inline_keyboard)


def show_cabinet_options(chat_id, user_id, key, message_id=None):
    """نمایش گزینه‌های یک مقام — با editMessageText"""
    option = CABINET_OPTIONS.get(key)
    if not option:
        send_message(chat_id, "❌ مقام نامعتبر!")
        return

    keyboard = []
    row = []
    for opt_idx, opt in enumerate(option["options"]):
        row.append({"text": opt, "callback_data": f"cabinet_set_{key}_{opt_idx}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([{"text": "✏️ نوشتن دستی", "callback_data": f"cabinet_manual_{key}"}])
    keyboard.append([{"text": "🔙 بازگشت به لیست مقام‌ها", "callback_data": "cabinet_back"}])

    text = f"{option['icon']} **{option['name']}**\n━━━━━━━━━━━━━━━━━━\n"
    text += "یکی از گزینه‌های زیر را انتخاب کنید یا خودتان بنویسید:"

    inline_keyboard = {"inline_keyboard": keyboard}

    # 🔄 ویرایش یا ارسال جدید
    if message_id:
        result = edit_message(chat_id, message_id, text, inline_keyboard)
        if result:
            return
    send_message(chat_id, text, inline_keyboard)


def process_cabinet_answer(chat_id, user_id, key, value, message_id=None):
    """ثبت انتخاب یک مقام و بازگشت به لیست اصلی (editMessageText)"""
    from .dashboard import send_dashboard

    if user_id not in waiting_for_cabinet:
        send_dashboard(chat_id, user_id)
        return

    if not value or str(value).strip() == "":
        send_message(chat_id, "❌ **لطفاً یک گزینه معتبر انتخاب کنید!**")
        return

    # تبدیل ایندکس به نام واقعی
    if isinstance(value, str) and value.isdigit():
        opts = CABINET_OPTIONS.get(key, {}).get("options", [])
        idx = int(value)
        if 0 <= idx < len(opts):
            value = opts[idx]
        else:
            send_message(chat_id, "❌ گزینه نامعتبر!")
            return

    waiting_for_cabinet[user_id]["answers"][key] = value

    # بازگشت به لیست اصلی کابینه (ویرایش همون پیام)
    send_cabinet_question(chat_id, user_id, message_id=message_id)


def start_manual_cabinet_input(chat_id, user_id, key, message_id=None):
    """شروع ورود دستی برای یک مقام — با ویرایش پیام"""
    from .dashboard import send_dashboard

    if user_id not in waiting_for_cabinet:
        send_dashboard(chat_id, user_id)
        return

    option = CABINET_OPTIONS.get(key, {})
    waiting_for_cabinet_manual[user_id] = {"key": key, "menu_message_id": message_id}
    text = f"✏️ **{option.get('name', key)}** خود را وارد کنید:\n\n📏 حداقل 2 و حداکثر 40 کاراکتر\n\n⚠️ نمی‌توانید این قسمت را خالی بگذارید!\n\n📝 لطفاً نام را همین‌جا بفرستید."

    # کیبورد با دکمه بازگشت به لیست کابینه
    keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت به لیست مقام‌ها", "callback_data": "cabinet_back"}]]}

    # اگه message_id داشتیم، ویرایش کن
    if message_id:
        result = edit_message(chat_id, message_id, text, keyboard)
        if result:
            return
    send_message(chat_id, text, keyboard)


def process_manual_cabinet_input(chat_id, user_id, text_input):
    """پردازش ورود دستی نام مقام"""
    if user_id not in waiting_for_cabinet_manual:
        return False

    manual_data = waiting_for_cabinet_manual.pop(user_id)
    key = manual_data["key"]
    menu_message_id = manual_data.get("menu_message_id")

    if not text_input or text_input.strip() == "":
        send_message(chat_id, "❌ **نمی‌توانید این قسمت را خالی بگذارید!**\nلطفاً یک نام معتبر وارد کنید:")
        waiting_for_cabinet_manual[user_id] = manual_data
        return True

    if len(text_input) < 2 or len(text_input) > 40:
        send_message(chat_id, "❌ نام باید بین 2 تا 40 کاراکتر باشد!\nلطفاً دوباره وارد کنید:")
        waiting_for_cabinet_manual[user_id] = manual_data
        return True

    if user_id not in waiting_for_cabinet:
        from .dashboard import send_dashboard
        send_dashboard(chat_id, user_id)
        return True

    waiting_for_cabinet[user_id]["answers"][key] = text_input

    # بازگشت به لیست اصلی کابینه (ویرایش پیام منو)
    send_cabinet_question(chat_id, user_id, message_id=menu_message_id)
    return True


def finish_cabinet_selection(chat_id, user_id, message_id=None):
    """اتمام کابینه: ذخیره، ارسال کدها (پیام جدید)، سپس خوش‌آمد + داشبورد (پیام جدید + Reply Keyboard)"""
    from .dashboard import send_dashboard
    from .registration import start_name_input

    if user_id not in waiting_for_cabinet:
        send_dashboard(chat_id, user_id)
        return

    answers = waiting_for_cabinet[user_id].get("answers", {})

    # بررسی تکمیل بودن همه ۵ مقام
    missing = [k for k in CABINET_KEYS if not answers.get(k)]
    if missing:
        names = [CABINET_OPTIONS[k]['name'] for k in missing]
        send_message(chat_id, "❌ **هنوز این مقام‌ها انتخاب نشدند:**\n" + "\n".join(f"• {n}" for n in names))
        send_cabinet_question(chat_id, user_id, message_id=message_id)
        return

    # ذخیره کابینه
    if user_id not in players_data:
        players_data[user_id] = {}
    players_data[user_id]["cabinet"] = answers
    db.save_player(user_id, players_data[user_id])

    # پاک کردن وضعیت انتظار
    waiting_for_cabinet.pop(user_id, None)
    user_in_cabinet_setup.pop(user_id, None)

    # تولید کدهای امنیتی
    codes = generate_all_cabinet_codes(user_id, answers)

    # 📌 پیام ۱: کدهای امنیتی (پیام جدید)
    codes_text = "🔐 **کدهای امنیتی کابینه شما**\n━━━━━━━━━━━━━━━━━━\n"
    codes_text += "⚠️ این کدها محرمانه هستند!\n"
    codes_text += "🔒 هر کد مخصوص یک مقام است.\n"
    codes_text += "━━━━━━━━━━━━━━━━━━\n"

    for key, code in codes.items():
        cabinet_name = CABINET_OPTIONS.get(key, {}).get("name", key)
        icon = CABINET_OPTIONS.get(key, {}).get("icon", "🔑")
        member_name = answers.get(key, "نامشخص")
        codes_text += f"\n{icon} **{cabinet_name}**\n"
        codes_text += f"🔑 کد: `{code}`\n"
        codes_text += f"👤 {member_name}\n"
        codes_text += f"━━━━━━━━━━━━━━━━━━\n"

    codes_text += "\n💡 **نکته امنیتی:**\n"
    codes_text += "• این کدها فقط به شما نشان داده می‌شود!\n"
    codes_text += "• اگر کدها لو برود، دشمن می‌تواند مقام شما را ترور کند!\n"
    codes_text += "• کدها را در جای امنی نگه دارید."

    send_message(chat_id, codes_text)

    user = players_data.get(user_id, {})

    # اگر نام نداشت (حالت نیمه‌کاره)
    if not user.get("player_name"):
        send_message(chat_id, "🎉 **کابینه شما کامل شد!**\nفقط ثبت نام بازیکن باقی مانده است.")
        start_name_input(chat_id, user_id)
        return

    # اعلام به گروه
    welcome_msg = (
        f"🎉 **کاربر جدید وارد شد!**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 نام: {user.get('player_name')}\n"
        f"🌍 کشور: {user.get('country', 'نامشخص')}\n"
        f"👑 رهبر: {answers.get('leader', 'نامشخص')}\n"
        f"💰 سکه شروع: 10,000"
    )
    send_to_group(welcome_msg)

    # 📌 پیام ۲: پیام خوش‌آمد به پلیر (پیام جدید)
    welcome_player_msg = (
        f"🎉 **تبریک {user.get('player_name')}!**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ ثبت‌نام شما با موفقیت کامل شد!\n"
        f"🌍 کشور: {user.get('country', 'نامشخص')}\n"
        f"👑 رهبر: {answers.get('leader', 'نامشخص')}\n"
        f"💰 سکه شروع: 10,000\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ اکنون می‌توانید وارد بازی شوید.\n"
        f"🌍 داشبورد شما در پیام بعدی ارسال می‌شود..."
    )
    send_message(chat_id, welcome_player_msg)

    # 📌 پیام ۳: Reply Keyboard + داشبورد (پیام جدید)
    # پاک کردن menu_message تا send_dashboard پیام جدید بفرسته
    state.menu_message.pop(str(chat_id), None)
    
    # 📌 ارسال Reply Keyboard با دکمه‌های «🚀 شروع» و «🔄 بروزرسانی»
    send_reply_keyboard(chat_id, user_id)
    
    send_dashboard(chat_id, user_id)