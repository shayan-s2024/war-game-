# -*- coding: utf-8 -*-
# ==================== تنظیمات اصلی ربات ====================
import os

# توکن ربات (قابل تغییر با متغیر محیطی BOT_TOKEN)
TOKEN = os.environ.get("BOT_TOKEN", "")
# 👑 آیدی عددی ادمین اصلی — برای تغییر، فقط همین خط را عوض کنید
MAIN_ADMIN_ID = "6254295276"

# 🔒 جوین اجباری: کانال‌هایی که کاربر باید عضوشان باشد تا بتواند از ربات استفاده کند
# نام کانال‌های عمومی خودت را اینجا بنویس (مثال: ["@mychannel1", "@mychannel2"])
# ⚠️ مهم: ربات باید در این کانال‌ها ادمین باشد تا بتواند عضویت را بررسی کند
REQUIRED_CHANNELS = []

GROUP_ID = ""
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# اتصال HTTPS دائم به تلگرام — به جای ساخت اتصال جدید برای هر پیام (سرعت خیلی بالاتر)
import requests
TG = requests.Session()

ATTACK_LIMIT = 4

ATTACK_WINDOW = 86400  # 24 ساعت به ثانیه

STATEMENT_LIMIT = 4

STATEMENT_WINDOW = 86400  # 24 ساعت به ثانیه


# سقف اهدا بر اساس لول اتحاد
UNION_DONATION_LIMITS = {
    1: 20000,
    2: 50000,
    3: 70000,
    4: 90000,
    5: 110000
}


MAX_ITEM_DONATION = 100

SPAM_LIMIT = 12  # حداکثر 5 کامند در دقیقه

SPAM_WINDOW = 60  # بازه زمانی 60 ثانیه

COMMAND_COOLDOWN = 5  # فاصله زمانی بین هر کامند (ثانیه)

PAYMENT_REQUEST_TIMEOUT = 3600  # یک ساعت زمان برای ارسال رسید
