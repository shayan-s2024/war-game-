# -*- coding: utf-8 -*-
"""نقطه ورود ربات جنگ جهانی — نسخه ماژولار.

ساختار پروژه در پوشه ww3/:
  config.py        تنظیمات (توکن، محدودیت‌ها)
  static_data.py   داده‌های ثابت (کشورها، تجهیزات، ویروس‌ها و ...)
  database.py      کلاس دیتابیس SQLite
  state.py         حالت سراسری (بازیکنان، اتحادها، متغیرهای وضعیت)
  helpers.py       توابع کمکی (ارسال پیام، اسپم، ظرفیت و ...)
  registration.py  ثبت‌نام، ظرفیت و گیت ضد اکانت بی‌نام
  cabinet.py       کابینه
  dashboard.py     داشبورد و اطلاعات بازیکن
  shop.py          فروشگاه سکه‌ای
  payments.py      فروشگاه تومانی و تایید پرداخت
  bases.py         پایگاه‌ها
  attack.py        حمله نظامی
  hacks.py         هک و ترور
  unions.py        اتحادها
  economy.py       اقتصاد، سود روزانه و ویروس‌ها
  admin.py         پنل ادمین
  dispatcher.py    دیسپچ پیام/کال‌بک و حلقه اصلی
"""
from ww3.dispatcher import main

if __name__ == "__main__":
    main()
