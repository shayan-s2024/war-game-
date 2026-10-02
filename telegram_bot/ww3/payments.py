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
from .config import BASE_URL, TG, MAIN_ADMIN_ID, TG
from .helpers import is_admin, send_message
from .state import db, pending_payments, players_data, waiting_for_payment_screenshot
from .static_data import TOMAN_SHOP_ITEMS

# ==================== ماژول payments ====================


# ==================== اینجا توابع فروشگاه تومان را اضافه کنید ====================

def send_shop_toman(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "💰 60,000 سکه | 60,000 تومان", "callback_data": "buy_toman_60000"}],
            [{"text": "💰 100,000 سکه | 100,000 تومان", "callback_data": "buy_toman_100000"}],
            [{"text": "💰 130,000 سکه | 130,000 تومان", "callback_data": "buy_toman_130000"}],
            [{"text": "💰 180,000 سکه | 175,000 تومان", "callback_data": "buy_toman_180000"}],
            [{"text": "🔙 بازگشت", "callback_data": "dashboard"}]
        ]
    }
    
    text = f"""🛍️ **فروشگاه (تومان)**
━━━━━━━━━━━━━━━━━━
💰 خرید سکه با پول واقعی

📦 **پکیج‌های موجود:**
━━━━━━━━━━━━━━━━━━
• 60,000 سکه → 60,000 تومان
• 100,000 سکه → 100,000 تومان
• 130,000 سکه → 130,000 تومان
• 180,000 سکه → 175,000 تومان
━━━━━━━━━━━━━━━━━━

💡 **راهنمای خرید:**
1️⃣ گزینه مورد نظر را انتخاب کنید
2️⃣ رسید واریزی را ارسال کنید
3️⃣ پس از تایید ادمین، سکه به حسابتان اضافه می‌شود

📞 پشتیبانی: @shayan_s2024
━━━━━━━━━━━━━━━━━━
⚠️ لطفاً پس از واریز، حتماً رسید را ارسال کنید."""
    
    send_message(chat_id, text, keyboard)




def toman_purchase_callback(chat_id, user_id, coins_key):
    """کال بک خرید از فروشگاه تومان"""
    
    if coins_key not in TOMAN_SHOP_ITEMS:
        send_message(chat_id, "❌ گزینه نامعتبر!")
        return
    
    # 🔒 فقط بازیکنان ثبت‌نام‌شده می‌توانند خرید کنند
    if not is_registered_player(user_id):
        send_message(chat_id, "🔒 **ابتدا باید در بازی ثبت‌نام کنید!**\nدستور /start را بفرستید.")
        return

    item = TOMAN_SHOP_ITEMS[coins_key]
    
    # اطلاعات کارت بانکی (این مقادیر را با اطلاعات واقعی خود جایگزین کنید)
    CARD_NUMBER = "6219-8618-3450-7500"  # شماره کارت خود را وارد کنید
    CARD_HOLDER = "نام صاحب کارت : مهرپویان"  # نام صاحب کارت
    BANK_NAME = "بانک سامان"  # نام بانک
    
    payment_text = f"""💳 **اطلاعات واریز**
━━━━━━━━━━━━━━━━━━
💰 سکه: {item['coins']:,} سکه
💸 مبلغ: {item['price_text']}
━━━━━━━━━━━━━━━━━━

🏦 **اطلاعات بانکی:**
شماره کارت: `{CARD_NUMBER}`
به نام: {CARD_HOLDER}
بانک: {BANK_NAME}
━━━━━━━━━━━━━━━━━━

📌 **مراحل خرید:**
1️⃣ مبلغ را به کارت فوق واریز کنید
2️⃣ از رسید واریز عکس بگیرید
3️⃣ عکس را برای ربات ارسال کنید
━━━━━━━━━━━━━━━━━━

✅ پس از ارسال عکس، درخواست شما برای ادمین ارسال می‌شود.

⚠️ لطفاً فقط **یک بار** عکس را ارسال کنید!"""

    # ذخیره اطلاعات درخواست
    waiting_for_payment_screenshot[user_id] = {
        "coins": item['coins'],
        "amount": item['price_toman'],
        "price_text": item['price_text'],
        "coins_key": coins_key
    }
    
    send_message(chat_id, payment_text)




def process_payment_screenshot(chat_id, user_id, file_id, caption=None):
    """پردازش عکس رسید واریزی"""
    
    if user_id not in waiting_for_payment_screenshot:
        send_message(chat_id, "❌ شما هیچ درخواست خرید فعالی ندارید!\nلطفاً ابتدا از فروشگاه تومان خرید کنید.")
        return
    
    payment_info = waiting_for_payment_screenshot.pop(user_id)
    
    # تولید شناسه یکتا برای این درخواست
    import random
    payment_id = str(random.randint(100000, 999999))
    
    # دریافت نام کاربر
    user_name = players_data.get(user_id, {}).get("player_name", "نامشخص")
    
    pending_payments[payment_id] = {
        "user_id": user_id,
        "user_name": user_name,
        "coins": payment_info["coins"],
        "amount": payment_info["amount"],
        "price_text": payment_info["price_text"],
        "screenshot_file_id": file_id,
        "status": "pending",
        "timestamp": time.time()
    }
    
    # ارسال پیام تایید به کاربر
    send_message(chat_id, f"✅ **رسید شما دریافت شد!**\n━━━━━━━━━━━━━━━━━━\n💰 سکه: {payment_info['coins']:,} سکه\n💸 مبلغ: {payment_info['price_text']}\n━━━━━━━━━━━━━━━━━━\n⏳ درخواست شما برای ادمین ارسال شد.\nلطفاً منتظر تایید باشید...")
    
    # ارسال درخواست به ادمین
    admin_message = f"""🆕 **درخواست خرید جدید!**
━━━━━━━━━━━━━━━━━━
🆔 کد درخواست: `{payment_id}`
👤 کاربر: {user_name}
🆔 آیدی کاربر: `{user_id}`
💰 سکه: {payment_info['coins']:,} سکه
💸 مبلغ: {payment_info['price_text']}
🕐 زمان: {time.strftime('%Y/%m/%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━

📸 لطفاً عکس رسید را بررسی کنید."""

    # ارسال پیام به ادمین (فقط به ادمین، نه به گروه)
    send_message(MAIN_ADMIN_ID, admin_message)
    
    # ارسال عکس به ادمین
    send_photo_to_admin(MAIN_ADMIN_ID, file_id, payment_id, user_id, payment_info, user_name)


    




def send_photo_to_admin(admin_id, file_id, payment_id, user_id, payment_info, user_name):
    """ارسال عکس به ادمین با کیبورد تایید/رد"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ تایید واریز", "callback_data": f"approve_payment_{payment_id}"}],
            [{"text": "❌ رد درخواست", "callback_data": f"reject_payment_{payment_id}"}]
        ]
    }
    
    caption = f"📸 **رسید واریز - کد {payment_id}**\n👤 کاربر: {user_name}\n💰 سکه: {payment_info['coins']:,}\n💸 مبلغ: {payment_info['price_text']}"
    
    # روش اول: ارسال عکس با sendPhoto
    url = f"{BASE_URL}/sendPhoto"
    payload = {
        "chat_id": admin_id,
        "photo": file_id,
        "caption": caption,
        "reply_markup": keyboard
    }
    try:
        response = TG.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            # اگر خطا داد، به روش دوم امتحان کن
            send_photo_as_document(admin_id, file_id, payment_id, user_name, payment_info, keyboard)
    except Exception as e:
        print(f"خطا در ارسال عکس: {e}")
        # اگر خطا داد، به روش دوم امتحان کن
        send_photo_as_document(admin_id, file_id, payment_id, user_name, payment_info, keyboard)




def send_photo_as_document(admin_id, file_id, payment_id, user_name, payment_info, keyboard):
    """ارسال عکس به عنوان سند (روش جایگزین)"""
    
    url = f"{BASE_URL}/sendDocument"
    payload = {
        "chat_id": admin_id,
        "document": file_id,
        "caption": f"📸 رسید واریز - کد {payment_id}\n👤 کاربر: {user_name}\n💰 سکه: {payment_info['coins']:,}\n💸 مبلغ: {payment_info['price_text']}",
        "reply_markup": keyboard
    }
    try:
        TG.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطا در ارسال سند: {e}")
        # اگر باز هم خطا داد، فقط پیام متنی بفرست
        send_message(admin_id, 
            f"📸 **رسید واریز - کد {payment_id}**\n"
            f"👤 کاربر: {user_name}\n"
            f"💰 سکه: {payment_info['coins']:,}\n"
            f"💸 مبلغ: {payment_info['price_text']}\n"
            f"⚠️ عکس دریافت شد اما نمایش داده نمی‌شود.\n"
            f"🆔 file_id: `{file_id}`", 
            keyboard)



def approve_payment(chat_id, admin_id, payment_id):
    """تایید واریز توسط ادمین و افزودن سکه به کاربر"""
    
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ فقط ادمین می‌تواند تایید کند!")
        return
    
    if payment_id not in pending_payments:
        send_message(chat_id, "❌ درخواست یافت نشد!")
        return
    
    payment = pending_payments[payment_id]
    
    if payment["status"] != "pending":
        send_message(chat_id, f"❌ این درخواست قبلاً { 'تایید' if payment['status'] == 'approved' else 'رد' } شده است!")
        return
    
    user_id = payment["user_id"]
    coins_amount = payment["coins"]

    # 🔒 اکانت بی‌نام ساخته نمی‌شود؛ فقط بازیکنان ثبت‌نام‌شده سکه دریافت می‌کنند
    target_player = players_data.get(user_id)
    if not target_player or not target_player.get("player_name"):
        send_message(chat_id,
            f"⛔ **تایید نشد!** کاربر `{user_id}` هنوز در بازی ثبت‌نام نکرده است.\n"
            f"💡 ابتدا باید با /start ثبت‌نام کند، سپس این درخواست قابل تایید است.")
        return
    
    players_data[user_id]["credit"] = players_data[user_id].get("credit", 0) + coins_amount
    db.save_player(user_id, players_data[user_id])
    
    # به‌روزرسانی وضعیت درخواست
    payment["status"] = "approved"
    payment["approved_by"] = admin_id
    payment["approved_at"] = time.time()
    
    # ارسال پیام موفقیت به کاربر
    send_message(int(user_id), 
        f"✅ **پرداخت شما تایید شد!**\n━━━━━━━━━━━━━━━━━━\n"
        f"💰 {coins_amount:,} سکه به حساب شما اضافه شد!\n"
        f"💎 موجودی جدید: {players_data[user_id]['credit']:,} سکه\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {time.strftime('%Y/%m/%d %H:%M:%S')}\n"
        f"🙏 از خرید شما متشکریم!")
    
    # ارسال پیام تایید به ادمین
    send_message(chat_id, f"✅ تایید شد! {coins_amount:,} سکه به {payment['user_name']} اضافه شد.")


    
    # ==================== حذف یا کامنت کردن این خط ====================
    # send_to_group(f"✅ **واریز تایید شد!**\n👤 {payment['user_name']}\n💰 {coins_amount:,} سکه به حساب کاربر اضافه شد.")



def reject_payment(chat_id, admin_id, payment_id):
    """رد درخواست واریز توسط ادمین"""
    
    if not is_admin(admin_id):
        send_message(chat_id, "⛔ فقط ادمین می‌تواند رد کند!")
        return
    
    if payment_id not in pending_payments:
        send_message(chat_id, "❌ درخواست یافت نشد!")
        return
    
    payment = pending_payments[payment_id]
    
    if payment["status"] != "pending":
        send_message(chat_id, f"❌ این درخواست قبلاً { 'تایید' if payment['status'] == 'approved' else 'رد' } شده است!")
        return
    
    user_id = payment["user_id"]
    
    # به‌روزرسانی وضعیت
    payment["status"] = "rejected"
    payment["rejected_by"] = admin_id
    payment["rejected_at"] = time.time()
    
    # ارسال پیام به کاربر
    send_message(int(user_id), 
        f"❌ **متاسفانه پرداخت شما تایید نشد!**\n━━━━━━━━━━━━━━━━━━\n"
        f"💰 سکه: {payment['coins']:,} سکه\n"
        f"💸 مبلغ: {payment['price_text']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📞 لطفاً با پشتیبانی تماس بگیرید.\n"
        f"🕐 {time.strftime('%Y/%m/%d %H:%M:%S')}")
    
    send_message(chat_id, f"❌ درخواست {payment_id} رد شد!")


    
    # ==================== حذف یا کامنت کردن این خط ====================
    # send_to_group(f"❌ درخواست خرید {payment['user_name']} رد شد.")

def clean_old_payment_requests():
    """پاک کردن درخواست‌های قدیمی (بیشتر از 24 ساعت)"""
    current_time = time.time()
    expired = []
    for pid, payment in pending_payments.items():
        if payment["status"] == "pending" and current_time - payment["timestamp"] > 86400:
            expired.append(pid)
    
    for pid in expired:
        del pending_payments[pid]
