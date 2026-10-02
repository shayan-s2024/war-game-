# -*- coding: utf-8 -*-
"""داده‌های ثابت بازی — پورت کامل از ww3/static_data.py نسخه تلگرام.

قانون پروژه: هیچ قلم داده‌ای حذف یا ساده نشده است.
"""

# ==================== لیست کامل کشورها (۴۵۰ کشور/جزیره/سرزمین افسانه‌ای) ====================
COUNTRIES_LIST = {
    "asia": {"name": "آسیا", "flag": "🌏", "neighbors": ["europe", "africa"], "countries": {
        "افغانستان": {"emoji": "🇦🇫", "population": 38},
        "ارمنستان": {"emoji": "🇦🇲", "population": 3},
        "آذربایجان": {"emoji": "🇦🇿", "population": 10},
        "بحرین": {"emoji": "🇧🇭", "population": 1.7},
        "بنگلادش": {"emoji": "🇧🇩", "population": 166},
        "بوتان": {"emoji": "🇧🇹", "population": 0.8},
        "برونئی": {"emoji": "🇧🇳", "population": 0.4},
        "کامبوج": {"emoji": "🇰🇭", "population": 16},
        "چین": {"emoji": "🇨🇳", "population": 1400},
        "تیمور شرقی": {"emoji": "🇹🇱", "population": 1.3},
        "گرجستان": {"emoji": "🇬🇪", "population": 4},
        "هند": {"emoji": "🇮🇳", "population": 1380},
        "اندونزی": {"emoji": "🇮🇩", "population": 273},
        "ایران": {"emoji": "🇮🇷", "population": 85},
        "عراق": {"emoji": "🇮🇶", "population": 40},
        "اسرائیل": {"emoji": "🇮🇱", "population": 9},
        "ژاپن": {"emoji": "🇯🇵", "population": 126},
        "اردن": {"emoji": "🇯🇴", "population": 10},
        "قزاقستان": {"emoji": "🇰🇿", "population": 18},
        "کویت": {"emoji": "🇰🇼", "population": 4.2},
        "قرقیزستان": {"emoji": "🇰🇬", "population": 6.5},
        "لائوس": {"emoji": "🇱🇦", "population": 7.2},
        "لبنان": {"emoji": "🇱🇧", "population": 6.8},
        "مالزی": {"emoji": "🇲🇾", "population": 32},
        "مالدیو": {"emoji": "🇲🇻", "population": 0.5},
        "مغولستان": {"emoji": "🇲🇳", "population": 3.3},
        "میانمار": {"emoji": "🇲🇲", "population": 54},
        "نپال": {"emoji": "🇳🇵", "population": 29},
        "کره شمالی": {"emoji": "🇰🇵", "population": 25},
        "عمان": {"emoji": "🇴🇲", "population": 5},
        "پاکستان": {"emoji": "🇵🇰", "population": 220},
        "فیلیپین": {"emoji": "🇵🇭", "population": 109},
        "قطر": {"emoji": "🇶🇦", "population": 2.8},
        "عربستان سعودی": {"emoji": "🇸🇦", "population": 35},
        "سنگاپور": {"emoji": "🇸🇬", "population": 5.8},
        "کره جنوبی": {"emoji": "🇰🇷", "population": 51},
        "سریلانکا": {"emoji": "🇱🇰", "population": 21},
        "سوریه": {"emoji": "🇸🇾", "population": 17},
        "تایوان": {"emoji": "🇹🇼", "population": 23},
        "تاجیکستان": {"emoji": "🇹🇯", "population": 9.5},
        "تایلند": {"emoji": "🇹🇭", "population": 69},
        "ترکیه": {"emoji": "🇹🇷", "population": 84},
        "ترکمنستان": {"emoji": "🇹🇲", "population": 6},
        "امارات متحده عربی": {"emoji": "🇦🇪", "population": 9.8},
        "ازبکستان": {"emoji": "🇺🇿", "population": 33},
        "ویتنام": {"emoji": "🇻🇳", "population": 97},
        "یمن": {"emoji": "🇾🇪", "population": 29},
        "روسیه": {"emoji": "🇷🇺", "population": 144},
        "قبرس": {"emoji": "🇨🇾", "population": 1.2},
        "قشم": {"emoji": "🇮🇷", "population": 0.15},
        "کیش": {"emoji": "🇮🇷", "population": 0.04},
        "هرمز": {"emoji": "🇮🇷", "population": 0.006},
        "لاوان": {"emoji": "🇮🇷", "population": 0.01},
        "هنگام": {"emoji": "🇮🇷", "population": 0.005},
        "ابوموسی": {"emoji": "🇮🇷", "population": 0.002},
        "تنب بزرگ": {"emoji": "🇮🇷", "population": 0.0005},
        "تنب کوچک": {"emoji": "🇮🇷", "population": 0.0002},
        "هنگ کنگ": {"emoji": "🇭🇰", "population": 7.5},
        "ماکائو": {"emoji": "🇲🇴", "population": 0.68},
        "اوکیناوا": {"emoji": "🇯🇵", "population": 1.45},
        "سادو": {"emoji": "🇯🇵", "population": 0.055},
        "تسوشیما": {"emoji": "🇯🇵", "population": 0.032},
        "پنانگ": {"emoji": "🇲🇾", "population": 1.7},
        "لانگکاوی": {"emoji": "🇲🇾", "population": 0.065},
        "بوراکای": {"emoji": "🇵🇭", "population": 0.03},
        "پالاوان": {"emoji": "🇵🇭", "population": 0.9},
        "سبو": {"emoji": "🇵🇭", "population": 2.9},
        "لوزون": {"emoji": "🇵🇭", "population": 46},
        "میندانائو": {"emoji": "🇵🇭", "population": 22},
        "سامار": {"emoji": "🇵🇭", "population": 1.8},
        "نگروس": {"emoji": "🇵🇭", "population": 4.4},
        "پانای": {"emoji": "🇵🇭", "population": 4.5},
        "سولاوسی": {"emoji": "🇮🇩", "population": 19},
        "جاوه": {"emoji": "🇮🇩", "population": 145},
        "سوماترا": {"emoji": "🇮🇩", "population": 50},
        "بورنئو": {"emoji": "🌴", "population": 21},
        "بالی": {"emoji": "🏝️", "population": 4.2},
        "لومبوک": {"emoji": "🇮🇩", "population": 3.2},
        "فلورس": {"emoji": "🇮🇩", "population": 1.8},
        "هوکایدو": {"emoji": "🇯🇵", "population": 5.3},
        "هونشو": {"emoji": "🇯🇵", "population": 104},
        "شیکوکو": {"emoji": "🇯🇵", "population": 3.8},
        "کیوشو": {"emoji": "🇯🇵", "population": 13},
        # ----- سرزمین‌های افسانه‌ای (آسیا) -----
        "دیل": {"emoji": "🏔️", "population": 0.4},
        "اربور": {"emoji": "🐐", "population": 0.05},
        "رووانیون": {"emoji": "🛶", "population": 0.1},
        "اسوس": {"emoji": "🏙️", "population": 8},
        "براووس": {"emoji": "🏦", "population": 0.9},
        "پینتوس": {"emoji": "⛵", "population": 0.7},
        "والیریا": {"emoji": "🔥", "population": 0.001},
        "کالادان": {"emoji": "🛡️", "population": 0.3},
        "پادشاهی خاک": {"emoji": "🪨", "population": 20},
        "سایبرترون": {"emoji": "🤖", "population": 0.0001},
        "سرزمین آتش": {"emoji": "🔥", "population": 6},
        "سرزمین باد": {"emoji": "🌪️", "population": 2},
        "سرزمین آذرخش": {"emoji": "⚡", "population": 3},
        "سرزمین آب": {"emoji": "💧", "population": 1.5},
        "سرزمین خاک": {"emoji": "⛰️", "population": 4},
        "سرزمین ارواح": {"emoji": "👻", "population": 0.0001},
        "دره صلح": {"emoji": "🐼", "population": 0.02},
        "آگرابا": {"emoji": "🕌", "population": 0.5},
        "الموت": {"emoji": "🦅", "population": 0.01},
        "تروا": {"emoji": "🐴", "population": 0.02},
        "کوماندرا": {"emoji": "🐉", "population": 0.01},
        "ولکان": {"emoji": "🖖", "population": 6},
        "ماندالور": {"emoji": "⛑️", "population": 0.001},
        "کریپتون": {"emoji": "🪐", "population": 0.001},
        "آبیدوس": {"emoji": "🐫", "population": 0.001},
        "سیاره ادموندز": {"emoji": "🌄", "population": 0.0001},
        "اینگاری": {"emoji": "🎩", "population": 0.5},
        "شهر زد": {"emoji": "🥊", "population": 3},
        "گرید": {"emoji": "🔵", "population": 0.0001},
        "واس دوتراک": {"emoji": "🐺", "population": 0.01},
        "معبد هوای شرقی": {"emoji": "🌬️", "population": 0.001},
        "کونوها": {"emoji": "🍥", "population": 0.05},
    }},

    "europe": {"name": "اروپا", "flag": "🌍", "neighbors": ["asia"], "countries": {
        "آلبانی": {"emoji": "🇦🇱", "population": 2.8},
        "آندورا": {"emoji": "🇦🇩", "population": 0.07},
        "اتریش": {"emoji": "🇦🇹", "population": 9},
        "بلاروس": {"emoji": "🇧🇾", "population": 9.4},
        "بلژیک": {"emoji": "🇧🇪", "population": 11.5},
        "بوسنی و هرزگوین": {"emoji": "🇧🇦", "population": 3.3},
        "بلغارستان": {"emoji": "🇧🇬", "population": 7},
        "کرواسی": {"emoji": "🇭🇷", "population": 4},
        "جمهوری چک": {"emoji": "🇨🇿", "population": 10.7},
        "دانمارک": {"emoji": "🇩🇰", "population": 5.8},
        "استونی": {"emoji": "🇪🇪", "population": 1.3},
        "فنلاند": {"emoji": "🇫🇮", "population": 5.5},
        "فرانسه": {"emoji": "🇫🇷", "population": 67},
        "آلمان": {"emoji": "🇩🇪", "population": 83},
        "یونان": {"emoji": "🇬🇷", "population": 10.4},
        "مجارستان": {"emoji": "🇭🇺", "population": 9.7},
        "ایسلند": {"emoji": "🇮🇸", "population": 0.36},
        "ایرلند": {"emoji": "🇮🇪", "population": 5},
        "ایتالیا": {"emoji": "🇮🇹", "population": 60},
        "کوزوو": {"emoji": "🇽🇰", "population": 1.8},
        "لتونی": {"emoji": "🇱🇻", "population": 1.9},
        "لیختن اشتاین": {"emoji": "🇱🇮", "population": 0.038},
        "لیتوانی": {"emoji": "🇱🇹", "population": 2.8},
        "لوکزامبورگ": {"emoji": "🇱🇺", "population": 0.6},
        "مالت": {"emoji": "🇲🇹", "population": 0.5},
        "مولداوی": {"emoji": "🇲🇩", "population": 2.6},
        "موناکو": {"emoji": "🇲🇨", "population": 0.039},
        "مونته نگرو": {"emoji": "🇲🇪", "population": 0.6},
        "هلند": {"emoji": "🇳🇱", "population": 17.4},
        "مقدونیه شمالی": {"emoji": "🇲🇰", "population": 2.1},
        "نروژ": {"emoji": "🇳🇴", "population": 5.4},
        "لهستان": {"emoji": "🇵🇱", "population": 38},
        "پرتغال": {"emoji": "🇵🇹", "population": 10.3},
        "رومانی": {"emoji": "🇷🇴", "population": 19.2},
        "سان مارینو": {"emoji": "🇸🇲", "population": 0.033},
        "صربستان": {"emoji": "🇷🇸", "population": 6.9},
        "اسلواکی": {"emoji": "🇸🇰", "population": 5.4},
        "اسلوونی": {"emoji": "🇸🇮", "population": 2.1},
        "اسپانیا": {"emoji": "🇪🇸", "population": 47.3},
        "سوئد": {"emoji": "🇸🇪", "population": 10.3},
        "سوئیس": {"emoji": "🇨🇭", "population": 8.6},
        "اوکراین": {"emoji": "🇺🇦", "population": 41},
        "انگلستان": {"emoji": "🇬🇧", "population": 67},
        "واتیکان": {"emoji": "🇻🇦", "population": 0.0008},
        "سیسیل": {"emoji": "🇮🇹", "population": 5},
        "ساردینیا": {"emoji": "🇮🇹", "population": 1.6},
        "کرت": {"emoji": "🇬🇷", "population": 0.6},
        "کورس": {"emoji": "🇫🇷", "population": 0.33},
        "جزیره من": {"emoji": "🇮🇲", "population": 0.085},
        "جرزی": {"emoji": "🇯🇪", "population": 0.1},
        "گرنزی": {"emoji": "🇬🇬", "population": 0.063},
        "جزایر فارو": {"emoji": "🇫🇴", "population": 0.05},
        "البا": {"emoji": "🇮🇹", "population": 0.032},
        "کاپری": {"emoji": "🇮🇹", "population": 0.014},
        "سانتورینی": {"emoji": "🇬🇷", "population": 0.015},
        "میکونوس": {"emoji": "🇬🇷", "population": 0.01},
        "رودس": {"emoji": "🇬🇷", "population": 0.115},
        "کورفو": {"emoji": "🇬🇷", "population": 0.102},
        "مالیورکا": {"emoji": "🇪🇸", "population": 0.86},
        "منورکا": {"emoji": "🇪🇸", "population": 0.094},
        "ایبیزا": {"emoji": "🇪🇸", "population": 0.15},
        "گران کاناریا": {"emoji": "🇪🇸", "population": 0.85},
        "تنریف": {"emoji": "🇪🇸", "population": 0.9},
        "لانزاروته": {"emoji": "🇪🇸", "population": 0.15},
        "لا پالما": {"emoji": "🇪🇸", "population": 0.085},
        "مادیرا": {"emoji": "🇵🇹", "population": 0.25},
        "آزور": {"emoji": "🇵🇹", "population": 0.24},
        "گوتلاند": {"emoji": "🇸🇪", "population": 0.058},
        "بورنهولم": {"emoji": "🇩🇰", "population": 0.04},
        # ----- سرزمین‌های افسانه‌ای (اروپا) -----
        "شایر": {"emoji": "🍃", "population": 0.002},
        "گاندور": {"emoji": "🏰", "population": 3},
        "روهان": {"emoji": "🐎", "population": 1},
        "موردور": {"emoji": "🌋", "population": 0.5},
        "آیزنگارد": {"emoji": "⚙️", "population": 0.1},
        "ریوندل": {"emoji": "💫", "population": 0.001},
        "لوتلورین": {"emoji": "🌳", "population": 0.005},
        "موریا": {"emoji": "⛏️", "population": 0.0001},
        "آنگمار": {"emoji": "🌑", "population": 0.05},
        "میناس تیریت": {"emoji": "🗼", "population": 0.8},
        "فورنوست": {"emoji": "⚜️", "population": 0.02},
        "نارنیا": {"emoji": "🦁", "population": 0.3},
        "آرکلند": {"emoji": "🏹", "population": 0.2},
        "تلمار": {"emoji": "⚔️", "population": 0.5},
        "وستروس": {"emoji": "🐺", "population": 5},
        "دورن": {"emoji": "☀️", "population": 0.8},
        "مارلی": {"emoji": "🎖️", "population": 10},
        "تمریا": {"emoji": "🧙", "population": 0.5},
        "سینتر": {"emoji": "👑", "population": 0.4},
        "ریدانیا": {"emoji": "🛡️", "population": 0.6},
        "کاِدوِن": {"emoji": "🌲", "population": 0.3},
        "تمیسکیرا": {"emoji": "🗡️", "population": 0.001},
        "هاگوارتز": {"emoji": "🪄", "population": 0.001},
        "دیاگون اللی": {"emoji": "🕯️", "population": 0.0001},
        "خوگسمید": {"emoji": "🍺", "population": 0.0005},
        "آزکابان": {"emoji": "⛓️", "population": 0.0005},
        "آسگارد": {"emoji": "⚡", "population": 0.5},
        "کورونا": {"emoji": "🌸", "population": 0.2},
        "آرندل": {"emoji": "❄️", "population": 0.1},
        "نورثولدرا": {"emoji": "🧊", "population": 0.05},
        "برک": {"emoji": "🐉", "population": 0.001},
        "دور دور": {"emoji": "👟", "population": 0.05},
        "فانتازیا": {"emoji": "🐲", "population": 0.1},
        "شرود": {"emoji": "🎯", "population": 0.05},
        "کاملات": {"emoji": "♛", "population": 0.1},
        "وینترفل": {"emoji": "🌨️", "population": 0.3},
        "شهر شاهان": {"emoji": "🏯", "population": 1},
        "دراگون‌استون": {"emoji": "🔥", "population": 0.0005},
        "پیلتوور": {"emoji": "🔮", "population": 0.3},
        "زاون": {"emoji": "🧪", "population": 0.2},
        "والاکیا": {"emoji": "🦇", "population": 0.3},
        "ویندن": {"emoji": "⏳", "population": 0.01},
        "استورم‌هولد": {"emoji": "⭐", "population": 0.001},
        "پورتوروسو": {"emoji": "🐠", "population": 0.001},
        "آلدران": {"emoji": "🌌", "population": 0.1},
        "گودریک هالو": {"emoji": "🎃", "population": 0.0001},
    }},

    "africa": {"name": "آفریقا", "flag": "🌍", "neighbors": ["asia", "europe"], "countries": {
        "الجزایر": {"emoji": "🇩🇿", "population": 44},
        "آنگولا": {"emoji": "🇦🇴", "population": 32},
        "بنین": {"emoji": "🇧🇯", "population": 12},
        "بوتسوانا": {"emoji": "🇧🇼", "population": 2.3},
        "بورکینافاسو": {"emoji": "🇧🇫", "population": 20},
        "بوروندی": {"emoji": "🇧🇮", "population": 11},
        "کیپ ورد": {"emoji": "🇨🇻", "population": 0.5},
        "کامرون": {"emoji": "🇨🇲", "population": 26},
        "جمهوری آفریقای مرکزی": {"emoji": "🇨🇫", "population": 4.8},
        "چاد": {"emoji": "🇹🇩", "population": 16},
        "کومور": {"emoji": "🇰🇲", "population": 0.8},
        "جمهوری دموکراتیک کنگو": {"emoji": "🇨🇩", "population": 89},
        "جمهوری کنگو": {"emoji": "🇨🇬", "population": 5.5},
        "جیبوتی": {"emoji": "🇩🇯", "population": 0.9},
        "مصر": {"emoji": "🇪🇬", "population": 102},
        "گینه استوایی": {"emoji": "🇬🇶", "population": 1.4},
        "اریتره": {"emoji": "🇪🇷", "population": 3.5},
        "اسواتینی": {"emoji": "🇸🇿", "population": 1.1},
        "اتیوپی": {"emoji": "🇪🇹", "population": 114},
        "گابن": {"emoji": "🇬🇦", "population": 2.2},
        "گامبیا": {"emoji": "🇬🇲", "population": 2.4},
        "غنا": {"emoji": "🇬🇭", "population": 31},
        "گینه": {"emoji": "🇬🇳", "population": 13},
        "گینه بیسائو": {"emoji": "🇬🇼", "population": 1.9},
        "ساحل عاج": {"emoji": "🇨🇮", "population": 26},
        "کنیا": {"emoji": "🇰🇪", "population": 53},
        "لسوتو": {"emoji": "🇱🇸", "population": 2.1},
        "لیبریا": {"emoji": "🇱🇷", "population": 5},
        "لیبی": {"emoji": "🇱🇾", "population": 6.8},
        "ماداگاسکار": {"emoji": "🇲🇬", "population": 27},
        "مالاوی": {"emoji": "🇲🇼", "population": 19},
        "مالی": {"emoji": "🇲🇱", "population": 20},
        "موریتانی": {"emoji": "🇲🇷", "population": 4.6},
        "موریس": {"emoji": "🇲🇺", "population": 1.2},
        "مراکش": {"emoji": "🇲🇦", "population": 36},
        "موزامبیک": {"emoji": "🇲🇿", "population": 31},
        "نامیبیا": {"emoji": "🇳🇦", "population": 2.5},
        "نیجر": {"emoji": "🇳🇪", "population": 24},
        "نیجریه": {"emoji": "🇳🇬", "population": 206},
        "رواندا": {"emoji": "🇷🇼", "population": 12},
        "سائوتومه و پرنسیپ": {"emoji": "🇸🇹", "population": 0.2},
        "سنگال": {"emoji": "🇸🇳", "population": 16},
        "سیشل": {"emoji": "🇸🇨", "population": 0.09},
        "سیرالئون": {"emoji": "🇸🇱", "population": 7.8},
        "سومالی": {"emoji": "🇸🇴", "population": 15},
        "آفریقای جنوبی": {"emoji": "🇿🇦", "population": 59},
        "سودان جنوبی": {"emoji": "🇸🇸", "population": 11},
        "سودان": {"emoji": "🇸🇩", "population": 43},
        "تانزانیا": {"emoji": "🇹🇿", "population": 59},
        "توگو": {"emoji": "🇹🇬", "population": 8.2},
        "تونس": {"emoji": "🇹🇳", "population": 11},
        "اوگاندا": {"emoji": "🇺🇬", "population": 45},
        "زامبیا": {"emoji": "🇿🇲", "population": 18},
        "زیمبابوه": {"emoji": "🇿🇼", "population": 14},
        "صحرای غربی": {"emoji": "🇪🇭", "population": 0.5},
        "زنگبار": {"emoji": "🇹🇿", "population": 1.5},
        "پمبا": {"emoji": "🇹🇿", "population": 0.5},
        "مایوت": {"emoji": "🇾🇹", "population": 0.3},
        "ریونیون": {"emoji": "🇷🇪", "population": 0.9},
        "سنت هلنا": {"emoji": "🇸🇭", "population": 0.005},
        "جزیره آسنسیون": {"emoji": "🇦🇨", "population": 0.0008},
        # ----- سرزمین‌های افسانه‌ای (آفریقا) -----
        "هاراد": {"emoji": "🐘", "population": 2},
        "اومبار": {"emoji": "🏴‍☠️", "population": 0.3},
        "آراکیس": {"emoji": "🏜️", "population": 0.01},
        "گیدی پرایم": {"emoji": "🌧️", "population": 0.001},
        "واکاندا": {"emoji": "🖤", "population": 8},
        "زاموندا": {"emoji": "💎", "population": 3},
        "آلاباستا": {"emoji": "🏜️", "population": 0.8},
        "مریخ": {"emoji": "🔴", "population": 0.0001},
        "جومانجی": {"emoji": "🦁", "population": 0.0001},
        "دیستریکت ۹": {"emoji": "🛸", "population": 1.8},
        "سرزمین خشم": {"emoji": "🚗", "population": 0.001},
    }},

    "north_america": {"name": "آمریکای شمالی", "flag": "🌎", "neighbors": ["south_america"], "countries": {
        "آنتیگوا و باربودا": {"emoji": "🇦🇬", "population": 0.09},
        "باهاما": {"emoji": "🇧🇸", "population": 0.3},
        "باربادوس": {"emoji": "🇧🇧", "population": 0.2},
        "بلیز": {"emoji": "🇧🇿", "population": 0.4},
        "کانادا": {"emoji": "🇨🇦", "population": 38},
        "کاستاریکا": {"emoji": "🇨🇷", "population": 5},
        "کوبا": {"emoji": "🇨🇺", "population": 11},
        "دومینیکا": {"emoji": "🇩🇲", "population": 0.07},
        "جمهوری دومینیکن": {"emoji": "🇩🇴", "population": 10.8},
        "السالوادور": {"emoji": "🇸🇻", "population": 6.4},
        "گرنادا": {"emoji": "🇬🇩", "population": 0.1},
        "گواتمالا": {"emoji": "🇬🇹", "population": 17.9},
        "هائیتی": {"emoji": "🇭🇹", "population": 11.4},
        "هندوراس": {"emoji": "🇭🇳", "population": 9.9},
        "جامائیکا": {"emoji": "🇯🇲", "population": 2.9},
        "مکزیک": {"emoji": "🇲🇽", "population": 128},
        "نیکاراگوئه": {"emoji": "🇳🇮", "population": 6.6},
        "پاناما": {"emoji": "🇵🇦", "population": 4.3},
        "سنت کیتس و نویس": {"emoji": "🇰🇳", "population": 0.05},
        "سنت لوسیا": {"emoji": "🇱🇨", "population": 0.1},
        "سنت وینسنت و گرنادین": {"emoji": "🇻🇨", "population": 0.1},
        "ترینیداد و توباگو": {"emoji": "🇹🇹", "population": 1.4},
        "آمریکا": {"emoji": "🇺🇸", "population": 331},
        "پورتوریکو": {"emoji": "🇵🇷", "population": 3.3},
        "گرینلند": {"emoji": "🇬🇱", "population": 0.056},
        "برمودا": {"emoji": "🇧🇲", "population": 0.064},
        "جزایر کیمن": {"emoji": "🇰🇾", "population": 0.066},
        "جزایر ویرجین ایالات متحده": {"emoji": "🇻🇮", "population": 0.105},
        "آنگویلا": {"emoji": "🇦🇮", "population": 0.015},
        "نیوفاندلند": {"emoji": "🇨🇦", "population": 0.479},
        "ونکوور ایسلند": {"emoji": "🇨🇦", "population": 2.6},
        "جزیره شاهزاده ادوارد": {"emoji": "🇨🇦", "population": 0.14},
        "کیپ برتون": {"emoji": "🇨🇦", "population": 0.13},
        # ----- سرزمین‌های افسانه‌ای (آمریکای شمالی) -----
        "گاتهام": {"emoji": "🦇", "population": 10},
        "متروپلیس": {"emoji": "🦸", "population": 11},
        "پنم": {"emoji": "🐦", "population": 4},
        "زیون": {"emoji": "🕳️", "population": 0.25},
        "ایسلا نوبلار": {"emoji": "🦖", "population": 0.0001},
        "سرزمین مردگان": {"emoji": "💀", "population": 0.0001},
        "کمپ نیمه‌خدایان": {"emoji": "🔱", "population": 0.0001},
        "رادیاتور اسپرینگز": {"emoji": "🚗", "population": 0.0001},
        "زوتوپیا": {"emoji": "🐰", "population": 2},
        "سان فرانسوکیو": {"emoji": "🤖", "population": 6},
        "سرزمین از": {"emoji": "🌈", "population": 0.001},
        "نیورلند": {"emoji": "🧚", "population": 0.0001},
        "موستاناف": {"emoji": "🌋", "population": 0.001},
        "کورلیا": {"emoji": "🌊", "population": 0.001},
        "تورتوگا": {"emoji": "🏴‍☠️", "population": 0.01},
        "پورت رویال": {"emoji": "⚓", "population": 0.01},
        "ایسلا دی موئرتا": {"emoji": "💀", "population": 0},
        "هاوکینز": {"emoji": "🚨", "population": 0.03},
        "الکساندریا": {"emoji": "🧟", "population": 0.001},
        "المنت سیتی": {"emoji": "🔥", "population": 1.8},
        "گراویتی فالز": {"emoji": "🌲", "population": 0.001},
        "ترابیتیا": {"emoji": "🌳", "population": 0.0001},
        "میستیک فالز": {"emoji": "🧛", "population": 0.02},
        "قبیله آب شمالی": {"emoji": "🧊", "population": 0.001},
        "دیستریکت ۱۲": {"emoji": "⛏️", "population": 0.02},
    }},

    "south_america": {"name": "آمریکای جنوبی", "flag": "🌎", "neighbors": ["north_america"], "countries": {
        "آرژانتین": {"emoji": "🇦🇷", "population": 45},
        "بولیوی": {"emoji": "🇧🇴", "population": 11},
        "برزیل": {"emoji": "🇧🇷", "population": 212},
        "شیلی": {"emoji": "🇨🇱", "population": 19},
        "کلمبیا": {"emoji": "🇨🇴", "population": 50},
        "اکوادور": {"emoji": "🇪🇨", "population": 17},
        "گویان": {"emoji": "🇬🇾", "population": 0.7},
        "پاراگوئه": {"emoji": "🇵🇾", "population": 7.1},
        "پرو": {"emoji": "🇵🇪", "population": 32},
        "سورینام": {"emoji": "🇸🇷", "population": 0.5},
        "اروگوئه": {"emoji": "🇺🇾", "population": 3.5},
        "ونزوئلا": {"emoji": "🇻🇪", "population": 28},
        "گویان فرانسه": {"emoji": "🇬🇫", "population": 0.3},
        "جزایر فالکلند": {"emoji": "🇫🇰", "population": 0.0035},
        "جزیره مارگاریتا": {"emoji": "🇻🇪", "population": 0.5},
        "جزیره چیلوئه": {"emoji": "🇨🇱", "population": 0.15},
        "جزایر گالاپاگوس": {"emoji": "🐢", "population": 0.025},
        "تیرا دل فوئگو": {"emoji": "🇦🇷", "population": 0.15},
        "جزیره فرناندو دی نورونها": {"emoji": "🇧🇷", "population": 0.003},
        # ----- سرزمین‌های افسانه‌ای (آمریکای جنوبی) -----
        "قبیله آب جنوبی": {"emoji": "🌊", "population": 0.001},
        "آتلانتیس": {"emoji": "🔱", "population": 0.5},
        "پردیس آبشار": {"emoji": "🦜", "population": 0.0001},
        "انکانتو": {"emoji": "🕯️", "population": 0.01},
        "آزروت": {"emoji": "🦁", "population": 0.001},
        "الدورادو": {"emoji": "💰", "population": 0.01},
    }},

    "oceania": {"name": "اقیانوسیه", "flag": "🌏", "neighbors": [], "countries": {
        "استرالیا": {"emoji": "🇦🇺", "population": 25},
        "نیوزیلند": {"emoji": "🇳🇿", "population": 4.8},
        "فیجی": {"emoji": "🇫🇯", "population": 0.8},
        "جزایر سلیمان": {"emoji": "🇸🇧", "population": 0.6},
        "وانواتو": {"emoji": "🇻🇺", "population": 0.3},
        "ساموآ": {"emoji": "🇼🇸", "population": 0.2},
        "کیریباتی": {"emoji": "🇰🇮", "population": 0.1},
        "میکرونزی": {"emoji": "🇫🇲", "population": 0.1},
        "تونگا": {"emoji": "🇹🇴", "population": 0.1},
        "پالائو": {"emoji": "🇵🇼", "population": 0.02},
        "نائورو": {"emoji": "🇳🇷", "population": 0.01},
        "جزایر مارشال": {"emoji": "🇲🇭", "population": 0.05},
        "تووالو": {"emoji": "🇹🇻", "population": 0.01},
        "پاپوآ گینه نو": {"emoji": "🇵🇬", "population": 8.9},
        "گوآم": {"emoji": "🇬🇺", "population": 0.17},
        "کالدونیای جدید": {"emoji": "🇳🇨", "population": 0.27},
        "پلینزی فرانسه": {"emoji": "🇵🇫", "population": 0.28},
        "ساموآی آمریکا": {"emoji": "🇦🇸", "population": 0.055},
        "جزایر کوک": {"emoji": "🇨🇰", "population": 0.017},
        "والیس و فوتونا": {"emoji": "🇼🇫", "population": 0.011},
        "توکلائو": {"emoji": "🇹🇰", "population": 0.0015},
        "نیووی": {"emoji": "🇳🇺", "population": 0.0016},
        "جزیره ایستر": {"emoji": "🗿", "population": 0.0078},
        "تاسمانی": {"emoji": "🇦🇺", "population": 0.54},
        "جزیره کریسمس": {"emoji": "🇨🇽", "population": 0.002},
        "جزیره نورفک": {"emoji": "🇳🇫", "population": 0.0022},
        "جزیره لرد هاو": {"emoji": "🇦🇺", "population": 0.0004},
        "جزیره کانگورو": {"emoji": "🇦🇺", "population": 0.0045},
        # ----- سرزمین‌های افسانه‌ای (اقیانوسیه) -----
        "ملت آتش": {"emoji": "🔥", "population": 5},
        "معبد هوای جنوبی": {"emoji": "🌪️", "population": 0.001},
        "پاندورا": {"emoji": "🦋", "population": 0.001},
        "سوتوریس": {"emoji": "🌪️", "population": 0.5},
        "اسکایپیا": {"emoji": "☁️", "population": 0.001},
        "واتر سون": {"emoji": "🚂", "population": 0.3},
        "فیشمن آیلند": {"emoji": "🐟", "population": 0.001},
        "مارین‌فورد": {"emoji": "⚓", "population": 0.01},
        "پارادیس": {"emoji": "🏰", "population": 1},
        "سرزمین عجایب": {"emoji": "🐇", "population": 0.0001},
        "لاپوتا": {"emoji": "🎈", "population": 0.0001},
        "کرونوس": {"emoji": "👹", "population": 0.001},
        "تاتوین": {"emoji": "🏜️", "population": 0.2},
        "نابو": {"emoji": "🌊", "population": 4},
        "کوروسانت": {"emoji": "🏙️", "population": 1000},
        "هاث": {"emoji": "❄️", "population": 0.001},
        "اندور": {"emoji": "🌳", "population": 0.3},
        "داثومیر": {"emoji": "🌑", "population": 0.001},
        "جاکو": {"emoji": "🏝️", "population": 0.001},
        "اسکاریف": {"emoji": "🏝️", "population": 0.0001},
        "کاشیک": {"emoji": "🌲", "population": 45},
        "بسپین": {"emoji": "☁️", "population": 0.001},
        "جزیره مونستر": {"emoji": "🦖", "population": 0},
        "جزیره جمجمه": {"emoji": "🦍", "population": 0.0001},
        "موتونویی": {"emoji": "🌊", "population": 0.0001},
        "ساکار": {"emoji": "🗑️", "population": 0.001},
        "کامیانو": {"emoji": "🧬", "population": 0.0001},
        "سیاره میلر": {"emoji": "🌊", "population": 0},
        "پادشاهی قارچ": {"emoji": "🍄", "population": 0.5},
        "اویسس": {"emoji": "🎮", "population": 0.0001},
        "پیکسی هالو": {"emoji": "🧚", "population": 0.0001},
        "بیکینی باتم": {"emoji": "🍍", "population": 0.0001},
        "سرزمین اوی": {"emoji": "🍭", "population": 0.001},
        "آمفیبیا": {"emoji": "🐸", "population": 0.001},
        "اکسایوم": {"emoji": "🚀", "population": 0.001},
        "الاباف": {"emoji": "🪓", "population": 0.01},
        "یوین ۴": {"emoji": "🌳", "population": 0.0001},
    }},
}

CONTINENT_NAMES = {
    "asia": "آسیا", "europe": "اروپا", "africa": "آفریقا",
    "north_america": "آمریکای شمالی", "south_america": "آمریکای جنوبی", "oceania": "اقیانوسیه"
}

# ==================== سیستم کابینه ====================
CABINET_OPTIONS = {
    "diplomat": {"name": "وزیر امور خارجه", "icon": "🤝", "options": [
        "حسین امیرعبداللهیان (ایران)", "محمدجواد ظریف (ایران)", "علی اکبر صالحی (ایران)",
        "آنتونی بلینکن (آمریکا)", "سرگئی لاوروف (روسیه)", "وانگ یی (چین)",
        "جیمز کلورلی (انگلیس)", "اولاف شولتز (آلمان)", "امانوئل مکرون (فرانسه)"]},
    "leader": {"name": "رهبر کشور", "icon": "👑", "options": [
        "سید علی خامنه‌ای (ایران)", "ابراهیم رئیسی (ایران)", "حسن روحانی (ایران)",
        "جو بایدن (آمریکا)", "ولادیمیر پوتین (روسیه)", "شی جین پینگ (چین)",
        "رجب طیب اردوغان (ترکیه)", "نارندرا مودی (هند)", "کی یر استارمر (انگلیس)",
        "امانوئل مکرون (فرانسه)", "اولاف شولتز (آلمان)"]},
    "defense": {"name": "وزیر دفاع", "icon": "🛡️", "options": [
        "محمدرضا قرایی آشتیانی (ایران)", "امیر حاتمی (ایران)", "حسین دهقان (ایران)",
        "لوید آستین (آمریکا)", "سرگئی شویگو (روسیه)", "لی شانگ فو (چین)",
        "بوریس پستروسی (آلمان)", "سباستین لکورنو (فرانسه)", "گرانت شاپس (انگلیس)"]},
    "economy": {"name": "وزیر اقتصاد", "icon": "💰", "options": [
        "احسان خاندوزی (ایران)", "فرهاد دژپسند (ایران)", "علی طیب نیا (ایران)",
        "جنت یلن (آمریکا)", "آنتون سیلوانوف (روسیه)", "لیو کون (چین)",
        "کریستین لاگارد (اروپا)", "ریشی سوناک (انگلیس)", "کریستین لیندنر (آلمان)",
        "برونو لومر (فرانسه)"]},
    "intelligence": {"name": "وزیر اطلاعات", "icon": "🕵️", "options": [
        "حجت‌الاسلام خطیب (ایران)", "محمود علوی (ایران)", "علی یونسی (ایران)",
        "ویلیام برنز (سیا-آمریکا)", "سرگئی ناریشکین (روسیه)", "چن یی (چین)",
        "ریچارد مور (امآی6-انگلیس)", "برونو کال (فرانسه)", "برونو کال (آلمان)"]},
}

CABINET_KEYS = ["diplomat", "leader", "defense", "economy", "intelligence"]

# ==================== معادن و تجهیزات اقتصادی ====================
MINES = {
    "emerald": {"name": "معدن زمرد", "icon": "🟢", "price": 1000, "daily_profit": 200, "max": 100},
    "iron": {"name": "معدن آهن", "icon": "⚪", "price": 2000, "daily_profit": 300, "max": 100},
    "silver": {"name": "معدن نقره", "icon": "⚫", "price": 3000, "daily_profit": 700, "max": 100},
    "bronze": {"name": "معدن برنز", "icon": "🟠", "price": 4500, "daily_profit": 1050, "max": 100},
    "diamond": {"name": "معدن الماس", "icon": "🔵", "price": 7600, "daily_profit": 1600, "max": 100},
    "gold": {"name": "معدن طلا", "icon": "🟡", "price": 13000, "daily_profit": 2400, "max": 100},
}

ECONOMIC_ITEMS = {
    "factory": {"name": "کارخانه تولیدی", "icon": "🏭", "price": 180000, "profit": 8000},
    "oil_company": {"name": "شرکت انرژی نفت و گاز", "icon": "🛢️", "price": 550000, "profit": 28000},
    "industrial_company": {"name": "هلدینگ صنعتی", "icon": "🏢", "price": 1250000, "profit": 70000},
    "renewable_company": {"name": "شرکت انرژی‌های تجدیدپذیر", "icon": "🌱", "price": 2500000, "profit": 410000},
    "petrochemical_company": {"name": "پتروشیمی ملی", "icon": "⚗️", "price": 5500000, "profit": 900000},
    "technology_conglomerate": {"name": "ابرشرکت فناوری و صنایع دفاعی", "icon": "🛰️", "price": 12000000, "profit": 1950000},
}

# Gentle shop-wide price progression. Free play remains possible; this only
# slows down the earliest purchases so high-tier goods retain value.
SHOP_PRICE_MULTIPLIER = 1.2

# ==================== تجهیزات نظامی ====================
AIR_DEFENSES = {
    "normal": {"name": "پدافند عادی", "icon": "🔴", "q": 0.4, "cap": 200, "price": 8000, "count": 100, "power": 100},
    "sling": {"name": "پدافند فلاخن داوود", "icon": "🔴", "q": 0.6, "cap": 180, "price": 11200, "count": 100, "power": 150},
    "patriot": {"name": "پدافند پاتریوت", "icon": "🔴", "q": 0.8, "cap": 150, "price": 12000, "count": 50, "power": 200},
    "s400": {"name": "پدافند اس 400", "icon": "🔴", "q": 1.2, "cap": 80, "price": 19200, "count": 20, "power": 400},
    "iron_dome": {"name": "پدافند گنبد آهنین", "icon": "🔴", "q": 1.7, "cap": 40, "price": 25600, "count": 10, "power": 700},
}

TANKS = {
    "simple": {"name": "تانک ساده", "icon": "🟢", "q": 0.5, "cap": 400, "price": 1600, "count": 100, "power": 80},
    "zolfaghar": {"name": "تانک ذوالفقار", "icon": "🟢", "q": 0.7, "cap": 300, "price": 6400, "count": 100, "power": 150},
    "karrar": {"name": "تانک کرار", "icon": "🟢", "q": 0.8, "cap": 300, "price": 8000, "count": 100, "power": 180},
    "merkava": {"name": "تانک مرکاوا", "icon": "🟢", "q": 0.95, "cap": 250, "price": 9600, "count": 100, "power": 200},
    "challenger": {"name": "تانک چلنجر", "icon": "🟢", "q": 1.05, "cap": 250, "price": 10400, "count": 100, "power": 220},
    "leclerc": {"name": "تانک لکرک", "icon": "🟢", "q": 1.15, "cap": 200, "price": 11200, "count": 50, "power": 250},
    "torpedo": {"name": "تانک اژدر", "icon": "🟢", "q": 1.25, "cap": 200, "price": 12000, "count": 50, "power": 280},
    "black_panther": {"name": "تانک بلک پنتر", "icon": "🟢", "q": 1.35, "cap": 150, "price": 13600, "count": 50, "power": 300},
    "leopard": {"name": "تانک لئوپارد", "icon": "🟢", "q": 1.45, "cap": 150, "price": 14400, "count": 50, "power": 320},
    "abrams": {"name": "تانک ابرامز", "icon": "🟢", "q": 1.6, "cap": 100, "price": 19200, "count": 10, "power": 400},
    "type99": {"name": "تانک تایپ ۹۹", "icon": "🟢", "price": 11000, "count": 100, "power": 310, "q": 1.4, "cap": 130},
    "t90": {"name": "تانک تی-۹۰", "icon": "🟢", "price": 13500, "count": 100, "power": 350, "q": 1.5, "cap": 120},
}

FIGHTERS = {
    "f4": {"name": "جنگنده اف 4", "icon": "🟡", "q": 0.4, "cap": 400, "price": 11200, "count": 100, "power": 100},
    "f18": {"name": "جنگنده اف 18", "icon": "🟡", "q": 0.5, "cap": 350, "price": 12800, "count": 100, "power": 130},
    "j10": {"name": "جنگنده جی 10", "icon": "🟡", "q": 0.6, "cap": 300, "price": 14400, "count": 100, "power": 140},
    "j16": {"name": "جنگنده جی 16", "icon": "🟡", "q": 0.7, "cap": 300, "price": 16000, "count": 100, "power": 160},
    "f16": {"name": "جنگنده اف 16", "icon": "🟡", "q": 0.8, "cap": 250, "price": 17600, "count": 100, "power": 180},
    "su27": {"name": "جنگنده سوخو 27", "icon": "🟡", "q": 0.9, "cap": 250, "price": 19200, "count": 100, "power": 200},
    "eurofighter": {"name": "جنگنده یوروفایتر", "icon": "🟡", "q": 1.0, "cap": 200, "price": 20800, "count": 100, "power": 220},
    "j17": {"name": "جنگنده شیانگ جی 17", "icon": "🟡", "q": 1.1, "cap": 150, "price": 22400, "count": 50, "power": 250},
    "golden_eagle": {"name": "جنگنده گلدن ایگل", "icon": "🟡", "q": 1.2, "cap": 150, "price": 24000, "count": 50, "power": 280},
    "j20": {"name": "جنگنده جی 20", "icon": "🟡", "q": 1.3, "cap": 120, "price": 25600, "count": 50, "power": 300},
    "su35": {"name": "جنگنده سوخو 35", "icon": "🟡", "q": 1.4, "cap": 120, "price": 27200, "count": 50, "power": 320},
    "su57": {"name": "جنگنده سوخو 57", "icon": "🟡", "q": 1.5, "cap": 100, "price": 28800, "count": 50, "power": 350},
    "f35": {"name": "جنگنده اف 35", "icon": "🟡", "q": 1.6, "cap": 100, "price": 30400, "count": 50, "power": 380},
    "su75": {"name": "جنگنده سوخو 75", "icon": "🟡", "q": 1.75, "cap": 60, "price": 32000, "count": 50, "power": 570},
    "f22": {"name": "جنگنده اف 22", "icon": "🟡", "q": 1.9, "cap": 50, "price": 40000, "count": 50, "power": 760},
    "su30": {"name": "جنگنده سوخو-۳۰", "icon": "🟡", "price": 14000, "count": 100, "power": 330, "q": 1.35, "cap": 120},
    "mig35": {"name": "جنگنده میگ-۳۵", "icon": "🟡", "price": 17500, "count": 100, "power": 390, "q": 1.65, "cap": 80},
    "rafale": {"name": "جنگنده رافائل", "icon": "🟡", "price": 21000, "count": 100, "power": 400, "q": 1.7, "cap": 80},
}

HELICOPTERS = {
    "normal": {"name": "هلیکوپتر عادی", "icon": "⚫", "q": 0.4, "cap": 300, "price": 8000, "count": 100, "power": 100},
    "cobra": {"name": "هلیکوپتر کبری", "icon": "⚫", "q": 0.7, "cap": 250, "price": 9600, "count": 100, "power": 150},
    "littlebird": {"name": "هلیکوپتر لیتل برد", "icon": "⚫", "q": 0.55, "cap": 250, "price": 11200, "count": 100, "power": 120},
    "tiger": {"name": "هلیکوپتر تایگر", "icon": "⚫", "q": 0.85, "cap": 200, "price": 12800, "count": 100, "power": 180},
    "crocodile": {"name": "هلیکوپتر تمساح", "icon": "⚫", "q": 1.0, "cap": 200, "price": 14400, "count": 80, "power": 200},
    "shamook": {"name": "هلیکوپتر شاموک", "icon": "⚫", "q": 1.1, "cap": 150, "price": 16000, "count": 50, "power": 220},
    "kamov52": {"name": "هلیکوپتر کاموف 52", "icon": "⚫", "q": 1.25, "cap": 120, "price": 20800, "count": 50, "power": 250},
    "ah47": {"name": "هلیکوپتر ای اچ 47", "icon": "⚫", "q": 1.45, "cap": 80, "price": 25600, "count": 20, "power": 350},
    "apache": {"name": "هلیکوپتر آپاچی", "icon": "⚫", "q": 1.7, "cap": 60, "price": 32000, "count": 20, "power": 600},
    "z10": {"name": "هلیکوپتر ز-۱۰", "icon": "⚫", "price": 11500, "count": 100, "power": 230, "q": 1.15, "cap": 120},
    "mi28": {"name": "هلیکوپتر می-۲۸", "icon": "⚫", "price": 14000, "count": 100, "power": 280, "q": 1.35, "cap": 100},
}

MISSILES = {
    "point": {"name": "موشک نقطه زن", "icon": "🔴", "q": 0.4, "cap": 500, "price": 4800, "count": 100, "power": 100},
    "cruise": {"name": "موشک کروز", "icon": "🔴", "q": 0.55, "cap": 450, "price": 5600, "count": 100, "power": 120},
    "ghadir": {"name": "موشک قدر", "icon": "🔴", "q": 0.7, "cap": 400, "price": 6400, "count": 100, "power": 140},
    "khorramshahr": {"name": "موشک خرمشهر", "icon": "🔴", "q": 0.85, "cap": 350, "price": 8000, "count": 100, "power": 160},
    "sejil": {"name": "موشک سجیل", "icon": "🔴", "q": 1.0, "cap": 300, "price": 9600, "count": 100, "power": 180},
    "fatah": {"name": "موشک فتاح", "icon": "🔴", "q": 1.15, "cap": 250, "price": 11200, "count": 100, "power": 200},
    "tomahawk": {"name": "موشک تاماهاوک", "icon": "🔴", "q": 1.3, "cap": 200, "price": 12800, "count": 50, "power": 240},
    "iskander": {"name": "موشک اسکندر", "icon": "🔴", "q": 1.45, "cap": 150, "price": 14400, "count": 50, "power": 280},
    "dongfeng": {"name": "موشک دانگ فنگ", "icon": "🔴", "q": 1.6, "cap": 120, "price": 16000, "count": 50, "power": 320},
    "kinzhal": {"name": "موشک کینژال", "icon": "🔴", "q": 1.8, "cap": 100, "price": 19200, "count": 50, "power": 400},
    "hypersonic": {"name": "موشک هایپرسونیک", "icon": "🔴", "q": 2.1, "cap": 50, "price": 32000, "count": 10, "power": 600},
    "icbm": {"name": "موشک قاره‌پیما", "icon": "🔴", "price": 45000, "count": 50, "power": 700, "q": 2.4, "cap": 30},
}

DRONES = {
    "ghaza": {"name": "پهباد غزه", "icon": "🔵", "price": 6400, "count": 100, "power": 80},
    "surveillance": {"name": "پهباد نظارتی", "icon": "🔵", "price": 7200, "count": 100, "power": 60},
    "suicide": {"name": "پهباد انتحاری", "icon": "🔵", "price": 8000, "count": 100, "power": 150},
    "hermes": {"name": "پهباد هرمس", "icon": "🔵", "price": 9600, "count": 100, "power": 120},
    "shahed": {"name": "پهباد شاهد ۱۳۶", "icon": "🔵", "price": 12800, "count": 100, "power": 180},
    "mk1": {"name": "پهباد ام کی 1", "icon": "🔵", "price": 14400, "count": 50, "power": 200},
    "mk9": {"name": "پهباد ام کی 9", "icon": "🔵", "price": 24000, "count": 50, "power": 300},
    "jetx147": {"name": "جت ایکس 147", "icon": "🔵", "price": 32000, "count": 20, "power": 400},
    "rq170": {"name": "پهباد ار کیو 170", "icon": "🔵", "price": 64000, "count": 20, "power": 600},
}

NAVAL_VESSELS = {
    "simple_warship": {"name": "ناو جنگی", "icon": "🚢", "q": 1.0, "cap": 80, "price": 32000, "count": 50, "power": 150},
    "destroyer": {"name": "ناوشکن", "icon": "🚢", "price": 35000, "count": 50, "power": 220, "q": 1.3, "cap": 40},
    "cruiser": {"name": "ناو موشک‌بر", "icon": "🚢", "price": 45000, "count": 50, "power": 260, "q": 1.5, "cap": 25},
}

SUBMARINES = {
    "combat_sub": {"name": "زیردریایی", "icon": "🐋", "q": 1.0, "cap": 40, "price": 16000, "count": 10, "power": 350},
    "kilo": {"name": "زیردریایی کیلو", "icon": "🐋", "price": 22000, "count": 10, "power": 420, "q": 1.2, "cap": 25},
    "nuclear_sub": {"name": "زیردریایی هسته‌ای", "icon": "🐋", "price": 40000, "count": 10, "power": 520, "q": 1.6, "cap": 15},
}

AIRCRAFT_CARRIERS = {
    "washington": {"name": "ناو هواپیمابر واشنگتن", "icon": "🔴", "price": 32000, "count": 10, "capacity": 300},
    "queen_elizabeth": {"name": "ملکه الیزابت", "icon": "🔴", "price": 40000, "count": 10, "capacity": 350},
    "kuznetsov": {"name": "کونزنتسوف", "icon": "🔴", "price": 48000, "count": 10, "capacity": 400},
    "abraham_lincoln": {"name": "ابراهام لینکلن", "icon": "🔴", "price": 56000, "count": 10, "capacity": 450},
    "gerald_ford": {"name": "جرالد فورد", "icon": "🔴", "price": 32000, "count": 10, "capacity": 500},
}

GROUND_FORCES = {
    "normal_soldier": {"name": "سرباز عادی", "icon": "⚫", "q": 0.5, "cap": 2000, "price": 3200, "count": 1000, "power": 10},
    "professional_soldier": {"name": "سرباز حرفه‌ای", "icon": "⚫", "q": 0.8, "cap": 1500, "price": 4800, "count": 1000, "power": 20},
    "border_guard": {"name": "مرزبان", "icon": "⚫", "q": 0.9, "cap": 1500, "price": 6400, "count": 1000, "power": 25},
    "commando": {"name": "تکاور", "icon": "⚫", "q": 1.2, "cap": 1000, "price": 12800, "count": 1000, "power": 40},
    "bodyguard": {"name": "بادیگارد", "icon": "⚫", "q": 1.6, "cap": 300, "price": 19200, "count": 100, "power": 80},
}

ARTILLERY = {
    "anti_ground": {"name": "توپخانه ضد زمینی", "icon": "⚪", "q": 0.5, "cap": 300, "price": 4800, "count": 100, "power": 100},
    "towed": {"name": "توپخانه یدک کش", "icon": "⚪", "q": 0.7, "cap": 300, "price": 6400, "count": 100, "power": 120},
    "braveheart": {"name": "توپخانه بریوهارت", "icon": "⚪", "q": 0.9, "cap": 250, "price": 8000, "count": 100, "power": 150},
    "defense": {"name": "توپخانه پدافند دار", "icon": "⚪", "q": 1.1, "cap": 150, "price": 11200, "count": 50, "power": 200},
}

HACKERS = {
    "weak": {"name": "هکر ضعیف", "icon": "🟡", "q": 0.5, "cap": 30, "price": 24000, "count": 30, "power": 50, "level": 1, "abilities": ["defense_only"]},
    "medium": {"name": "هکر متوسط", "icon": "🟠", "q": 0.8, "cap": 20, "price": 40000, "count": 20, "power": 100, "level": 2, "abilities": ["info_attack", "defense_hack"]},
    "strong": {"name": "هکر قوی", "icon": "🔴", "q": 1.2, "cap": 10, "price": 80000, "count": 10, "power": 200, "level": 3, "abilities": ["info_attack", "defense_hack", "missile_hack"]},
    "elite": {"name": "هکر نخبه سایبری", "icon": "🟣", "price": 120000, "count": 5, "power": 350, "level": 4, "q": 1.8, "cap": 5, "abilities": ["info_attack", "defense_hack", "missile_hack"]},
}

BOMBS = {
    "fire": {"name": "بمب آتش زا", "icon": "⚫", "q": 1.0, "cap": 15, "price": 80000, "count": 10, "power": 5000},
    "space": {"name": "بمب فضاپیل", "icon": "⚫", "q": 1.0, "cap": 12, "price": 88000, "count": 10, "power": 6000},
    "continental": {"name": "بمب قاره‌ای", "icon": "⚫", "q": 1.0, "cap": 8, "price": 96000, "count": 10, "power": 8000},
}

PILOTS = {
    "helicopter": {"name": "خلبان هلیکوپتر", "icon": "🚁", "price": 12800, "count": 100, "for_type": "helicopter"},
    "normal": {"name": "خلبان عادی", "icon": "🟠", "price": 6400, "count": 50, "for_type": "normal_fighters",
               "fighters": ["f4", "f18", "j10", "j16", "f16", "su27"]},
    "strong": {"name": "خلبان قوی", "icon": "🔴", "price": 9600, "count": 50, "for_type": "strong_fighters",
               "fighters": ["eurofighter", "j17", "golden_eagle", "j20", "su35", "mig35", "su30"]},
    "professional": {"name": "خلبان حرفه‌ای", "icon": "⭐", "price": 16000, "count": 50, "for_type": "professional_fighters",
                     "fighters": ["su57", "f35", "su75", "f22", "rafale"]},
}

BUILDINGS = {
    "normal_hospital": {"name": "بیمارستان عادی", "icon": "🏥", "price": 6200, "description": "فقط سربازان زخمی را درمان می‌کند | روزانه ۱۵۰۰ جا"},
    "professional_hospital": {"name": "بیمارستان حرفه‌ای", "icon": "🏥", "price": 15500, "description": "همه نوع مریض درمان می‌شود | روزانه ۳۰۰۰ جا"},
    "barracks": {"name": "پادگان", "icon": "🛕", "price": 23200, "description": "هر فرد بعد ۳ روز یک لول پیشرفت می‌کند"},
    "metro": {"name": "ایستگاه مترو", "icon": "🚉", "price": 10800, "description": "برای حمل و نقل داخلی"},
    "airport": {"name": "فرودگاه", "icon": "🛬", "price": 12400, "description": "برای حمل و نقل خارجی"},
    "dock": {"name": "اسکله", "icon": "⛴️", "price": 10800, "description": "برای حمل و نقل تجهیزات از بقیه کشورها"},
}

TOMAN_SHOP_ITEMS = {
    "60000": {"coins": 60000, "price_toman": 60000, "price_text": "شصت هزار تومان"},
    "100000": {"coins": 100000, "price_toman": 100000, "price_text": "صد هزار تومان"},
    "130000": {"coins": 130000, "price_toman": 130000, "price_text": "صد و سی هزار تومان"},
    "180000": {"coins": 180000, "price_toman": 175000, "price_text": "صد و هفتاد و پنج هزار تومان"},
}

VIRUSES = {
    "flu": {"name": "ویروس آنفولانزا", "icon": "🦠", "daily_loss": 200, "hospital_needed": "normal", "damage_base": False},
    "corona": {"name": "ویروس کرونا", "icon": "🦠", "daily_loss": 250, "hospital_needed": "normal", "damage_base": True},
    "zika": {"name": "ویروس زیکا", "icon": "🦠", "daily_loss": 300, "hospital_needed": "normal", "damage_base": False},
    "rabies": {"name": "ویروس هاری", "icon": "🦠", "daily_loss": 500, "hospital_needed": "professional", "damage_base": True},
    "marburg": {"name": "ویروس ماربورگ", "icon": "🦠", "daily_loss": 1000, "hospital_needed": "professional", "damage_base": True},
}

WEAPONS_SYSTEM = {
    "artillery": {"name": "توپخانه", "icon": "💥", "type": "ground", "damage": 110, "defense": 75,
                  "can_target": ["tank", "ground_unit"], "effectiveness": {"tank": 1.2}},
    "tank": {"name": "تانک", "icon": "🪖", "type": "ground", "damage": 100, "defense": 85,
             "can_target": ["tank", "artillery", "air_defense"],
             "effectiveness": {"tank": 1.0, "artillery": 1.2, "air_defense": 1.3}},
    "fighter": {"name": "جنگنده", "icon": "✈️", "type": "air", "damage": 120, "defense": 70,
                "can_target": ["tank", "fighter", "helicopter", "air_defense", "navy"],
                "effectiveness": {"tank": 1.3, "fighter": 1.0, "helicopter": 1.2, "air_defense": 0.4, "navy": 0.8}},
    "helicopter": {"name": "بالگرد", "icon": "🚁", "type": "air", "damage": 100, "defense": 65,
                   "can_target": ["tank", "artillery", "air_defense", "helicopter"],
                   "effectiveness": {"tank": 1.2, "artillery": 1.3, "air_defense": 1.1, "helicopter": 1.0}},
    "navy": {"name": "ناو جنگی", "icon": "🚢", "type": "sea", "damage": 150, "defense": 100,
             "can_target": ["fighter", "helicopter", "navy", "submarine"],
             "effectiveness": {"fighter": 1.2, "helicopter": 1.3, "navy": 1.0, "submarine": 1.5}},
    "submarine": {"name": "زیردریایی", "icon": "🐋", "type": "sea", "damage": 130, "defense": 80,
                  "can_target": ["navy", "submarine"], "effectiveness": {"navy": 1.3, "submarine": 1.0}},
    "air_defense": {"name": "پدافند هوایی", "icon": "🛡️", "type": "air_defense", "damage": 140, "defense": 100,
                    "can_target": ["fighter", "helicopter"], "effectiveness": {"fighter": 1.5, "helicopter": 1.4}},
    "anti_ship_missile": {"name": "موشک", "icon": "🚀", "type": "missile", "damage": 180, "defense": 40,
                          "can_target": ["navy"], "effectiveness": {"navy": 1.4}},
    "drone": {"name": "پهپاد", "icon": "🛸", "type": "air", "damage": 130, "defense": 50,
              "can_target": ["tank", "air_defense", "ground_unit", "helicopter"],
              "effectiveness": {"tank": 1.1, "air_defense": 0.6, "helicopter": 0.8, "ground_unit": 1.0}},
    "missile": {"name": "موشک", "icon": "🚀", "type": "missile", "damage": 180, "defense": 40,
                "can_target": ["navy"], "effectiveness": {"navy": 1.4}},
}

# ==================== راهنمای بازی (۱۳ بخش) ====================
GUIDE_SECTIONS = [
    ("start", "🚀 شروع بازی",
     "**۱) ورود**\nبا ثبت‌نام وارد شو، نامت را ثبت کن و از بین صدها کشور جهان کشورت را انتخاب کن — هر کشور فقط یک صاحب دارد!\n\n"
     "**۲) کابینه**\nپس از انتخاب کشور، ۵ مقام کابینه را تعیین می‌کنی. برای هر مقام یک کد امنیتی مخفی ساخته می‌شود — آن‌ها را فقط نزد خودت نگه دار!\n\n"
     "**۳) داشبورد**\nقلب بازی: سکه، استقامت، امتیاز، جمعیت و همه بخش‌های بازی اینجاست.\n\n"
     "**۴) سرمایه اولیه**\nسکه‌های شروع را می‌توانی صرف اقتصاد، ارتش یا دفاع کنی — سبک بازی‌ات را خودت انتخاب کن!"),
    ("economy", "💰 اقتصاد",
     "**درآمد چطور کار می‌کند؟**\n• معادن و شرکت‌ها هر شب ساعت ۲۲ سودشان را واریز می‌کنند.\n"
     "• کالاهای گران‌تر سود روزانه بیشتری دارند، اما سرمایه اولیه‌ات محدود است!\n\n"
     "**کجا بخرم؟**\nفروشگاه ← بخش اقتصادی. هر کالا قیمت، سود روزانه و سقف تعداد خودش را دارد.\n\n"
     "**بدان که...**\nسکه فقط از اقتصاد نمی‌آید؛ در جنگ غنیمت می‌گیری... و در شکست از دست می‌دهی!"),
    ("army", "🪖 ارتش و تجهیزات",
     "**خرید تجهیزات**\nفروشگاه ← تهاجمی: تانک، جنگنده، بالگرد، پهپاد، ناو، زیردریایی، موشک و توپخانه.\n\n"
     "**خلبان‌ها**\nجنگنده‌ها و بالگردها بدون خلبان اضافی پرواز نمی‌کنند! هر دسته هواپیما خلبان مخصوص خودش را می‌خواهد.\n\n"
     "**تلفات واقعی است**\nدر هر نبرد دو طرف ممکن است تجهیزات از دست بدهند. تعداد بیشتر یعنی قدرت بیشتر — و هزینه بیشتر.\n\n"
     "**سربازها**\nسربازها جدا از تجهیزات‌اند؛ پادگان‌ها هر شب برایت سرباز تربیت می‌کنند."),
    ("war", "⚔️ جنگ و حمله",
     "**زمان جنگ**\nحمله فقط وقتی ممکن است که جنگ جهانی توسط مدیریت فعال شده باشد.\n\n"
     "**سهمیه حمله**\nدر هر ۲۴ ساعت تعداد محدودی حمله داری. هدف‌هایت را هوشمندانه انتخاب کن!\n\n"
     "**انواع حمله**\nهر سلاح نقاط قوت و ضعف خودش را دارد؛ بعضی در برابر پدافند قوی‌اند و بعضی ضعیف. ترکیب برنده را باید خودت با تجربه پیدا کنی!\n\n"
     "**غنیمت و امتیاز**\nحمله موفق = غنیمت سکه + امتیاز؛ شکست = از دست دادن هر دو. نتیجه نبردها عمومی اعلام می‌شود — افتخار یا رسوایی جلوی همه است!"),
    ("defense", "🛡️ دفاع",
     "**استقامت**\nسپر کشور توست؛ بمب‌ها و نبردها آن را کم می‌کنند. با پدافندها بالا می‌بریش.\n\n"
     "**پدافند هوایی**\nدر برابر حمله‌های هوایی می‌جنگد و می‌تواند رهگیری هم انجام دهد. انواع مختلف با قدرت‌های متفاوت دارد.\n\n"
     "**اختلالات دشمن**\nهکرهای حریف می‌توانند پدافند یا موشک‌هایت را موقتاً از کار بیندازند — همیشه آماده باش!\n\n"
     "**بازسازی**\nتجهیزات از دست رفته را باید دوباره بخری. فقط حمله نبین — دفاع هم بساز!"),
    ("special", "💣 تسلیحات ویژه",
     "**💣 بمب‌افکن استراتژیک**\nبمب‌ها یک‌بارمصرف‌اند و ویرانی عظیمی به بار می‌آورند:\n"
     "• آتش‌زا: شهر حریف چند روز در آتش می‌سوزد\n"
     "• فضاپیل: ضربه‌ای که پدافند جلویش را نمی‌گیرد\n"
     "• قاره‌ای: برد جهانی + نابودی ساختمان‌ها\n\n"
     "**💥 توپخانه**\nکوبنده تانک‌های حریف با برد کوتاه. توپخانه پدافنددار هم شراره‌ات را قوی‌تر می‌کند هم دفاعت را.\n\n"
     "**کجا؟**\nفروشگاه ← بمب و توپخانه | استفاده: منوی جنگ"),
    ("buildings", "🏗️ ساختمان‌ها",
     "هر ساختمان یک نقش واقعی دارد:\n"
     "• 🏥 بیمارستان: سربازان زخمی را درمان می‌کند و در شفای ویروس نقش دارد\n"
     "• 🚉 مترو: پناهگاه مردم در برابر بمب و ویروس\n"
     "• 🛬 فرودگاه: برد حمله‌های هوایی را جهانی می‌کند\n"
     "• ⛴️ اسکله: غنیمت نبردهای دریایی را بیشتر می‌کند\n"
     "• 🛕 پادگان: هر شب سرباز تربیت می‌کند\n\n"
     "⚠️ ساختمان‌ها با بمب قاره‌ای حریف می‌توانند نابود شوند — پس دفاع هم بساز!"),
    ("bases", "🏕️ پایگاه‌ها",
     "**پایگاه چیست؟**\nیک مقر نظامی در قاره‌ای دیگر. با پایگاه، برد حمله‌هایت به آن قاره باز می‌شود.\n\n"
     "**ساخت**\nمنوی پایگاه‌ها ← انتخاب قاره و کشور مقصد. ساخت زمان و هزینه دارد.\n\n"
     "**صاحب‌دار یا خالی؟**\nکشور خالی را مستقیم می‌سازی؛ کشور صاحب‌دار فقط با اجازه صاحبش!"),
    ("unions", "🤝 اتحادها",
     "**اتحاد چیست؟**\nگروهی از بازیکنان که کنار هم پیش می‌روند.\n\n"
     "**ساخت یا عضویت**\nمی‌توانی اتحاد بسازی (هزینه دارد) یا به اتحادها درخواست بدهی؛ رئیس تایید می‌کند.\n\n"
     "**خزانه و اهدا**\nاعضا به خزانه پول یا تجهیزات اهدا می‌کنند. با ارتقای لول اتحاد، سقف اهدا بیشتر می‌شود.\n\n"
     "**مدیریت**\nرئیس می‌تواند عضو اخراج کند و اتحاد را ارتقا دهد. همکاری، قدرت واقعی است!"),
    ("spy", "🕵️ جاسوسی و ترور",
     "**هک**\nهکرها می‌توانند اطلاعات حریف را بدزدند، دفاعش را موقتاً از کار بیندازند یا موشک‌هایش را غیرفعال کنند. هکر قوی‌تر = توانایی بیشتر.\n\n"
     "**ترور**\nبا کد امنیتی مقامات حریف می‌توانی علیه آن‌ها توطئه چینی!\n\n"
     "**⚠️ حفاظت**\nکدهای کابینه‌ات را به هیچ‌کس نده — لو رفتن کد یعنی به خطر افتادن مقام‌هایت!"),
    ("virus", "🦠 ویروس‌ها",
     "**ویروس چیست؟**\nگاهی ویروس‌ها در کشورها پخش می‌شوند و هر روز تلفات جمعی و آسیب دفاعی می‌زنند.\n\n"
     "**درمان**\nبیمارستان‌ها شانس درمان را در گزارش شبانه بالا می‌برند؛ بیمارستان حرفه‌ای مؤثرتر است.\n\n"
     "**کاهش آسیب**\nمتروها تلفات جمعیت را کم می‌کنند. ویروس را جدی بگیر!"),
    ("toman", "💳 خرید سکه",
     "**خرید سریع**\nفروشگاه ← فروشگاه تومان: بسته‌های سکه با پول واقعی.\n\n"
     "**مراحل:**\n۱) مبلغ را به کارت اعلام‌شده واریز کن\n۲) رسید واریز را بارگذاری کن\n۳) بعد از تایید ادمین، سکه‌ها اضافه می‌شود"),
    ("rules", "📜 قوانین",
     "**قوانین مهم**\n"
     "• اسپم و ارسال پشت سر هم ممنوع\n"
     "• بیانیه و توییت سهمیه روزانه دارند\n"
     "• حمله محدودیت ۲۴ ساعته دارد\n"
     "• اهدا به اعضای اتحاد سقف دارد\n"
     "• اکانت دوم و سوءاستفاده = حذف حساب\n\n"
     "🎯 تصمیم مدیریت نهایی است. بازی منصفانه یعنی بازی جذاب برای همه!"),
]

# ==================== دسته‌های سلاح: (دیکشنری، پسوند شمارنده) ====================
WEAPON_CATEGORIES = {
    "tank": (TANKS, "tank_count"),
    "fighter": (FIGHTERS, "fighter_count"),
    "helicopter": (HELICOPTERS, "helicopter_count"),
    "drone": (DRONES, "drone_count"),
    "navy": (NAVAL_VESSELS, "naval_count"),
    "submarine": (SUBMARINES, "submarine_count"),
    "missile": (MISSILES, "missile_count"),
    "artillery": (ARTILLERY, "artillery_count"),
    "air_defense": (AIR_DEFENSES, "air_defense_count"),
}

# ==================== رتبه‌های تخریب ترور بر اساس مقام ====================
ASSASSINATION_DAMAGE_RATES = {
    "leader": 25, "diplomat": 20, "defense": 20, "intelligence": 18, "economy": 10,
}

# ==================== ظرفیت اتحاد بر اساس لول ====================
UNION_CAPACITY = {1: 2, 2: 4, 3: 6, 4: 8, 5: 10}
UNION_LEVEL_PRICE = lambda level: 50000 * level

# ==================== موقعیت جغرافیایی تقریبی قاره‌ها برای نقشه ۳D ====================
CONTINENT_GEO = {
    "asia": {"lat": 34.0, "lon": 90.0},
    "europe": {"lat": 50.0, "lon": 15.0},
    "africa": {"lat": 2.0, "lon": 20.0},
    "north_america": {"lat": 45.0, "lon": -100.0},
    "south_america": {"lat": -15.0, "lon": -60.0},
    "oceania": {"lat": -25.0, "lon": 140.0},
}

# موقعیت تقریبی چند کشور مهم برای پراکندگی نشانگرها روی کره (بقیه با آفست قاره + هش نام جای‌گذاری می‌شوند)
COUNTRY_GEO_HINTS = {
    "ایران": (32.0, 53.0), "آمریکا": (38.0, -97.0), "روسیه": (61.0, 90.0), "چین": (35.0, 105.0),
    "آلمان": (51.0, 10.0), "فرانسه": (46.0, 2.0), "انگلستان": (54.0, -2.0), "ترکیه": (39.0, 35.0),
    "هند": (20.0, 77.0), "ژاپن": (36.0, 138.0), "برزیل": (-10.0, -52.0), "مصر": (26.0, 30.0),
    "آفریقای جنوبی": (-29.0, 24.0), "استرالیا": (-25.0, 134.0), "کانادا": (56.0, -106.0),
    "عربستان سعودی": (24.0, 45.0), "مکزیک": (23.0, -102.0), "اندونزی": (-2.0, 118.0),
    "نیجریه": (9.0, 8.0), "اسرائیل": (31.5, 34.8), "کره جنوبی": (36.5, 127.8),
    "کره شمالی": (40.0, 127.0), "اوکراین": (49.0, 32.0), "ایتالیا": (42.5, 12.5),
    "اسپانیا": (40.0, -4.0), "پاکستان": (30.0, 70.0), "عراق": (33.0, 44.0),
    "سوریه": (35.0, 38.0), "یمن": (15.5, 48.5), "ویتنام": (16.0, 107.0),
    "تایلند": (15.0, 101.0), "فیلیپین": (12.0, 122.0), "مالزی": (4.0, 102.0),
    "سنگاپور": (1.35, 103.8), "کویت": (29.3, 47.5), "قطر": (25.3, 51.2),
    "امارات متحده عربی": (24.0, 54.0), "عمان": (21.0, 57.0), "بحرین": (26.0, 50.5),
    "لبنان": (33.9, 35.5), "اردن": (31.2, 36.5), "افغانستان": (33.9, 67.7),
    "آذربایجان": (40.1, 47.6), "ارمنستان": (40.1, 45.0), "گرجستان": (42.3, 43.4),
    "قزاقستان": (48.0, 67.0), "ازبکستان": (41.4, 64.6), "ترکمنستان": (38.9, 59.6),
    "تاجیکستان": (38.9, 71.3), "قرقیزستان": (41.2, 74.8), "مغولستان": (46.8, 103.8),
    "بنگلادش": (23.7, 90.4), "نپال": (28.4, 84.1), "سریلانکا": (7.9, 80.8),
    "میانمار": (21.9, 95.9), "کامبوج": (12.6, 105.0), "لائوس": (19.9, 102.5),
    "استان‌های افسانه‌ای": None,
}


def get_country_continent_key(country_name):
    """کلید قاره یک کشور — منطق دقیقاً مطابق helpers.py تلگرام"""
    if not country_name:
        return None
    for ck, cd in COUNTRIES_LIST.items():
        if country_name in cd.get("countries", {}):
            return ck
        for cn in cd.get("countries", {}).keys():
            if cn.strip() == country_name.strip():
                return ck
    return None


def get_total_countries_count():
    """تعداد کل کشورهای بازی — باید ۴۵۰ باشد"""
    return sum(len(c.get("countries", {})) for c in COUNTRIES_LIST.values())


# ==================== دستاوردها (ویژه نسخه وب — بند Gamification) ====================
# condition types: credit_gte | daily_profit_gte | defense_gte | attack_power_gte |
#   population_gte | score_gte | battles_total_gte | codes_stolen_gte | bases_count_gte |
#   union_level_gte | invite_count_gte | item_total_gte (suffix) | item_key_gte (suffix+item_key)
ACHIEVEMENTS = {
    "first_blood": {"name": "نبرد نخست", "icon": "⚔️", "tier": "bronze",
                    "condition": "battles_total_gte", "threshold": 1, "reward": 5000,
                    "description": "اولین نبرد خود را ثبت کن"},
    "veteran_commander": {"name": "فرمانده کهنه‌کار", "icon": "🎖️", "tier": "silver",
                          "condition": "battles_total_gte", "threshold": 25, "reward": 50000,
                          "description": "۲۵ نبرد ثبت کن"},
    "warlord": {"name": "جنگ‌سالار", "icon": "🏅", "tier": "gold",
                "condition": "battles_total_gte", "threshold": 100, "reward": 250000,
                "description": "۱۰۰ نبرد ثبت کن"},
    "treasury_builder": {"name": "خزانه‌دار", "icon": "💰", "tier": "bronze",
                         "condition": "credit_gte", "threshold": 100000, "reward": 10000,
                         "description": "۱۰۰,۰۰۰ سکه در خزانه داشته باش"},
    "oil_magnate": {"name": "مگنات اقتصاد", "icon": "🛢️", "tier": "silver",
                    "condition": "daily_profit_gte", "threshold": 100000, "reward": 50000,
                    "description": "سود روزانه ۱۰۰,۰۰۰ سکه بساز"},
    "impregnable": {"name": "استحکامات نامتحد", "icon": "🛡️", "tier": "silver",
                    "condition": "defense_gte", "threshold": 100000, "reward": 50000,
                    "description": "استقامت ۱۰۰,۰۰۰ برس"},
    "iron_fist": {"name": "مشت آهنین", "icon": "💥", "tier": "silver",
                  "condition": "attack_power_gte", "threshold": 100000, "reward": 50000,
                  "description": "قدرت تخریب ۱۰۰,۰۰۰ برس"},
    "megacity": {"name": "کلان‌شهر", "icon": "🌆", "tier": "bronze",
                 "condition": "population_gte", "threshold": 1000000, "reward": 20000,
                 "description": "جمعیت کشورت به ۱ میلیون برسد"},
    "tank_battalion": {"name": "گروه زرهی", "icon": "⚙️", "tier": "bronze",
                       "condition": "item_total_gte", "threshold": 100, "suffix": "tank_count",
                       "reward": 15000, "description": "۱۰۰ تانک در ارتش داشته باش"},
    "spymaster": {"name": "استاد جاسوسی", "icon": "🕵️", "tier": "gold",
                  "condition": "codes_stolen_gte", "threshold": 5, "reward": 100000,
                  "description": "۵ بار کد امنیتی حریفان را سرقت کن"},
    "field_medic": {"name": "پزشک میدانی", "icon": "🏥", "tier": "bronze",
                    "condition": "item_key_gte", "threshold": 2, "suffix": "count",
                    "item_key": "normal_hospital", "reward": 15000,
                    "description": "۲ بیمارستان عادی بساز"},
    "global_reach": {"name": "برد جهانی", "icon": "🌍", "tier": "silver",
                     "condition": "bases_count_gte", "threshold": 2, "reward": 40000,
                     "description": "۲ پایگاه نظامی خارجی بساز"},
    "diplomat": {"name": "ارابه دیپلماسی", "icon": "🤝", "tier": "silver",
                 "condition": "union_level_gte", "threshold": 3, "reward": 60000,
                 "description": "اتحادت به لول ۳ برسد"},
    "popular_leader": {"name": "رهبر محبوب", "icon": "📣", "tier": "bronze",
                       "condition": "invite_count_gte", "threshold": 3, "reward": 30000,
                       "description": "۳ دوست را به بازی دعوت کن"},
    "world_power": {"name": "قدرت جهانی", "icon": "👑", "tier": "gold",
                    "condition": "score_gte", "threshold": 1000, "reward": 150000,
                    "description": "امتیاز ۱۰۰۰ کسب کن"},
}
