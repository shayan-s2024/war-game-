import requests
import json
import os
import time
import random
import math
import sqlite3
import re
from datetime import datetime, timedelta



# ==================== لیست کامل کشورها ====================
# ==================== لیست کامل کشورها و جزایر (500+ مورد) ====================
COUNTRIES_LIST = {
    "asia": {"name": "آسیا", "flag": "🌏", "neighbors": ["europe", "africa"], "countries": {
        # کشورهای اصلی آسیا
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
        
        # جزایر آسیا (جدید)
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
        # ----- سرزمین‌های افسانه‌ای فیلم‌ها (آسیا) -----
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
        # کشورهای اصلی اروپا
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
        
        # جزایر اروپا
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
        "بورنهولم": {"emoji": "🇩🇰", "population": 0.04},        # ----- سرزمین‌های افسانه‌ای فیلم‌ها (اروپا) -----
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
        # کشورهای اصلی آفریقا
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
        
        # جزایر آفریقا
        "زنگبار": {"emoji": "🇹🇿", "population": 1.5},
        "پمبا": {"emoji": "🇹🇿", "population": 0.5},
        "مایوت": {"emoji": "🇾🇹", "population": 0.3},
        "ریونیون": {"emoji": "🇷🇪", "population": 0.9},
        "سنت هلنا": {"emoji": "🇸🇭", "population": 0.005},
        "جزیره آسنسیون": {"emoji": "🇦🇨", "population": 0.0008},
        # ----- سرزمین‌های افسانه‌ای فیلم‌ها (آفریقا) -----
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
        # کشورهای اصلی آمریکای شمالی
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
        
        # جزایر آمریکای شمالی
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
        # ----- سرزمین‌های افسانه‌ای فیلم‌ها (آمریکای شمالی) -----
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
        # کشورهای اصلی آمریکای جنوبی
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
        
        # جزایر آمریکای جنوبی
        "جزایر فالکلند": {"emoji": "🇫🇰", "population": 0.0035},
        "جزیره مارگاریتا": {"emoji": "🇻🇪", "population": 0.5},
        "جزیره چیلوئه": {"emoji": "🇨🇱", "population": 0.15},
        "جزایر گالاپاگوس": {"emoji": "🐢", "population": 0.025},
        "تیرا دل فوئگو": {"emoji": "🇦🇷", "population": 0.15},
        "جزیره فرناندو دی نورونها": {"emoji": "🇧🇷", "population": 0.003},
        # ----- سرزمین‌های افسانه‌ای فیلم‌ها (آمریکای جنوبی) -----
        "قبیله آب جنوبی": {"emoji": "🌊", "population": 0.001},
        "آتلانتیس": {"emoji": "🔱", "population": 0.5},
        "پردیس آبشار": {"emoji": "🦜", "population": 0.0001},
        "انکانتو": {"emoji": "🕯️", "population": 0.01},
        "آزروت": {"emoji": "🦁", "population": 0.001},
        "الدورادو": {"emoji": "💰", "population": 0.01},
    }},
    
    "oceania": {"name": "اقیانوسیه", "flag": "🌏", "neighbors": [], "countries": {
        # کشورهای اصلی اقیانوسیه
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
        
        # جزایر اقیانوسیه
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
        # ----- سرزمین‌های افسانه‌ای فیلم‌ها (اقیانوسیه) -----
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
    "diplomat": {
        "name": "وزیر امور خارجه", 
        "icon": "🤝", 
        "options": [
            "حسین امیرعبداللهیان (ایران)",
            "محمدجواد ظریف (ایران)",
            "علی اکبر صالحی (ایران)",
            "آنتونی بلینکن (آمریکا)",
            "سرگئی لاوروف (روسیه)",
            "وانگ یی (چین)",
            "جیمز کلورلی (انگلیس)",
            "اولاف شولتز (آلمان)",
            "امانوئل مکرون (فرانسه)"
        ]
    },
    "leader": {
        "name": "رهبر کشور", 
        "icon": "👑", 
        "options": [
            "سید علی خامنه‌ای (ایران)",
            "ابراهیم رئیسی (ایران)",
            "حسن روحانی (ایران)",
            "جو بایدن (آمریکا)",
            "ولادیمیر پوتین (روسیه)",
            "شی جین پینگ (چین)",
            "رجب طیب اردوغان (ترکیه)",
            "نارندرا مودی (هند)",
            "کی یر استارمر (انگلیس)",
            "امانوئل مکرون (فرانسه)",
            "اولاف شولتز (آلمان)"
        ]
    },
    "defense": {
        "name": "وزیر دفاع", 
        "icon": "🛡️", 
        "options": [
            "محمدرضا قرایی آشتیانی (ایران)",
            "امیر حاتمی (ایران)",
            "حسین دهقان (ایران)",
            "لوید آستین (آمریکا)",
            "سرگئی شویگو (روسیه)",
            "لی شانگ فو (چین)",
            "بوریس پستروسی (آلمان)",
            "سباستین لکورنو (فرانسه)",
            "گرانت شاپس (انگلیس)"
        ]
    },
    "economy": {
        "name": "وزیر اقتصاد", 
        "icon": "💰", 
        "options": [
            "احسان خاندوزی (ایران)",
            "فرهاد دژپسند (ایران)",
            "علی طیب نیا (ایران)",
            "جنت یلن (آمریکا)",
            "آنتون سیلوانوف (روسیه)",
            "لیو کون (چین)",
            "کریستین لاگارد (اروپا)",
            "ریشی سوناک (انگلیس)",
            "کریستین لیندنر (آلمان)",
            "برونو لومر (فرانسه)"
        ]
    },
    "intelligence": {
        "name": "وزیر اطلاعات", 
        "icon": "🕵️", 
        "options": [
            "حجت‌الاسلام خطیب (ایران)",
            "محمود علوی (ایران)",
            "علی یونسی (ایران)",
            "ویلیام برنز (سیا-آمریکا)",
            "سرگئی ناریشکین (روسیه)",
            "چن یی (چین)",
            "ریچارد مور (امآی6-انگلیس)",
            "برونو کال (فرانسه)",
            "برونو کال (آلمان)"
        ]
    }
}



CABINET_KEYS = ["diplomat", "leader", "defense", "economy", "intelligence"]



# ==================== معادن و تجهیزات ====================
MINES = {
    "emerald": {"name": "معدن زمرد", "icon": "🟢", "price": 1000, "daily_profit": 200, "max": 100},
    "iron": {"name": "معدن آهن", "icon": "⚪", "price": 2000, "daily_profit": 300, "max": 100},
    "silver": {"name": "معدن نقره", "icon": "⚫", "price": 3000, "daily_profit": 700, "max": 100},
    "bronze": {"name": "معدن برنز", "icon": "🟠", "price": 4500, "daily_profit": 1050, "max": 100},
    "diamond": {"name": "معدن الماس", "icon": "🔵", "price": 7600, "daily_profit": 1600, "max": 100},
    "gold": {"name": "معدن طلا", "icon": "🟡", "price": 13000, "daily_profit": 2400, "max": 100}
}



ECONOMIC_ITEMS = {
    "factory": {"name": "کارخانه تولیدی", "icon": "🏭", "price": 180000, "profit": 8000},
    "oil_company": {"name": "شرکت انرژی نفت و گاز", "icon": "🛢️", "price": 550000, "profit": 28000},
    "industrial_company": {"name": "هلدینگ صنعتی", "icon": "🏢", "price": 1250000, "profit": 70000},
    "renewable_company": {"name": "شرکت انرژی‌های تجدیدپذیر", "icon": "🌱", "price": 2500000, "profit": 410000},
    "petrochemical_company": {"name": "پتروشیمی ملی", "icon": "⚗️", "price": 5500000, "profit": 900000},
    "technology_conglomerate": {"name": "ابرشرکت فناوری و صنایع دفاعی", "icon": "🛰️", "price": 12000000, "profit": 1950000}
}
SHOP_PRICE_MULTIPLIER = 1.2



AIR_DEFENSES = {
    "normal": {"name": "پدافند عادی", "icon": "🔴", "q": 0.4, "cap": 200, "price": 8000, "count": 100, "power": 100},
    "sling": {"name": "پدافند فلاخن داوود", "icon": "🔴", "q": 0.6, "cap": 180, "price": 11200, "count": 100, "power": 150},
    "patriot": {"name": "پدافند پاتریوت", "icon": "🔴", "q": 0.8, "cap": 150, "price": 12000, "count": 50, "power": 200},
    "s400": {"name": "پدافند اس 400", "icon": "🔴", "q": 1.2, "cap": 80, "price": 19200, "count": 20, "power": 400},
    "iron_dome": {"name": "پدافند گنبد آهنین", "icon": "🔴", "q": 1.7, "cap": 40, "price": 25600, "count": 10, "power": 700}
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
    "type99": {"name": "تانک تایپ ۹۹", "icon": "🟢", "price": 17600, "count": 10, "power": 310},
    "t90": {"name": "تانک تی-۹۰", "icon": "🟢", "price": 21600, "count": 10, "power": 350},
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
    "su30": {"name": "جنگنده سوخو-۳۰", "icon": "🟡", "price": 22400, "count": 50, "power": 330},
    "mig35": {"name": "جنگنده میگ-۳۵", "icon": "🟡", "price": 28000, "count": 50, "power": 390},
    "rafale": {"name": "جنگنده رافائل", "icon": "🟡", "price": 33600, "count": 50, "power": 400},
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
    "z10": {"name": "هلیکوپتر ز-۱۰", "icon": "⚫", "price": 18400, "count": 100, "power": 230},
    "mi28": {"name": "هلیکوپتر می-۲۸", "icon": "⚫", "price": 22400, "count": 100, "power": 280},
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
    "icbm": {"name": "موشک قاره‌پیما", "icon": "🔴", "price": 72000, "count": 50, "power": 700},
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
    "rq170": {"name": "پهباد ار کیو 170", "icon": "🔵", "price": 64000, "count": 20, "power": 600}
}



NAVAL_VESSELS = {
    "simple_warship": {"name": "ناو جنگی", "icon": "🚢", "q": 1.0, "cap": 80, "price": 32000, "count": 50, "power": 150},
    "destroyer": {"name": "ناوشکن", "icon": "🚢", "price": 56000, "count": 50, "power": 220},
    "cruiser": {"name": "ناو موشک‌بر", "icon": "🚢", "price": 72000, "count": 50, "power": 260},
    "destroyer": {"name": "ناوشکن", "icon": "🚢", "price": 35000, "count": 50, "power": 220, "q": 1.3, "cap": 40},
    "cruiser": {"name": "ناو موشک‌بر", "icon": "🚢", "price": 45000, "count": 50, "power": 260, "q": 1.5, "cap": 25},
    }



SUBMARINES = {
    "combat_sub": {"name": "زیردریایی", "icon": "🐋", "q": 1.0, "cap": 40, "price": 16000, "count": 10, "power": 350},
    "kilo": {"name": "زیردریایی کیلو", "icon": "🐋", "price": 35200, "count": 10, "power": 420},
    "nuclear_sub": {"name": "زیردریایی هسته‌ای", "icon": "🐋", "price": 64000, "count": 10, "power": 520},
    "kilo": {"name": "زیردریایی کیلو", "icon": "🐋", "price": 22000, "count": 10, "power": 420, "q": 1.2, "cap": 25},
    "nuclear_sub": {"name": "زیردریایی هسته‌ای", "icon": "🐋", "price": 40000, "count": 10, "power": 520, "q": 1.6, "cap": 15},
    }



AIRCRAFT_CARRIERS = {
    "washington": {"name": "ناو هواپیمابر واشنگتن", "icon": "🔴", "price": 32000, "count": 10, "capacity": 300},
    "queen_elizabeth": {"name": "ملکه الیزابت", "icon": "🔴", "price": 40000, "count": 10, "capacity": 350},
    "kuznetsov": {"name": "کونزنتسوف", "icon": "🔴", "price": 48000, "count": 10, "capacity": 400},
    "abraham_lincoln": {"name": "ابراهام لینکلن", "icon": "🔴", "price": 56000, "count": 10, "capacity": 450},
    "gerald_ford": {"name": "جرالد فورد", "icon": "🔴", "price": 32000, "count": 10, "capacity": 500}
}



GROUND_FORCES = {
    "normal_soldier": {"name": "سرباز عادی", "icon": "⚫", "q": 0.5, "cap": 2000, "price": 3200, "count": 1000, "power": 10},
    "professional_soldier": {"name": "سرباز حرفه‌ای", "icon": "⚫", "q": 0.8, "cap": 1500, "price": 4800, "count": 1000, "power": 20},
    "border_guard": {"name": "مرزبان", "icon": "⚫", "q": 0.9, "cap": 1500, "price": 6400, "count": 1000, "power": 25},
    "commando": {"name": "تکاور", "icon": "⚫", "q": 1.2, "cap": 1000, "price": 12800, "count": 1000, "power": 40},
    "bodyguard": {"name": "بادیگارد", "icon": "⚫", "q": 1.6, "cap": 300, "price": 19200, "count": 100, "power": 80}
}



ARTILLERY = {
    "anti_ground": {"name": "توپخانه ضد زمینی", "icon": "⚪", "q": 0.5, "cap": 300, "price": 4800, "count": 100, "power": 100},
    "towed": {"name": "توپخانه یدک کش", "icon": "⚪", "q": 0.7, "cap": 300, "price": 6400, "count": 100, "power": 120},
    "braveheart": {"name": "توپخانه بریوهارت", "icon": "⚪", "q": 0.9, "cap": 250, "price": 8000, "count": 100, "power": 150},
    "defense": {"name": "توپخانه پدافند دار", "icon": "⚪", "q": 1.1, "cap": 150, "price": 11200, "count": 50, "power": 200}
}



HACKERS = {
    "weak": {"name": "هکر ضعیف", "icon": "🟡", "q": 0.5, "cap": 30, "price": 24000, "count": 30, "power": 50, "level": 1,
             "abilities": ["defense_only"]},
    "medium": {"name": "هکر متوسط", "icon": "🟠", "q": 0.8, "cap": 20, "price": 40000, "count": 20, "power": 100, "level": 2,
               "abilities": ["info_attack", "defense_hack"]},
    "strong": {"name": "هکر قوی", "icon": "🔴", "q": 1.2, "cap": 10, "price": 80000, "count": 10, "power": 200, "level": 3,
               "abilities": ["info_attack", "defense_hack", "missile_hack"]},
    "elite": {"name": "هکر نخبه سایبری", "icon": "🟣", "price": 192000, "count": 5, "power": 350, "level": 4,
               "abilities": ["info_attack", "defense_hack", "missile_hack"]},
    "elite": {"name": "هکر نخبه سایبری", "icon": "🟣", "price": 120000, "count": 5, "power": 350, "level": 4, "q": 1.8, "cap": 5, "abilities": ["info_attack", "defense_hack", "missile_hack"]},
    }



BOMBS = {
    "fire": {"name": "بمب آتش زا", "icon": "⚫", "q": 1.0, "cap": 15, "price": 80000, "count": 10, "power": 5000},
    "space": {"name": "بمب فضاپیل", "icon": "⚫", "q": 1.0, "cap": 12, "price": 88000, "count": 10, "power": 6000},
    "continental": {"name": "بمب قاره‌ای", "icon": "⚫", "q": 1.0, "cap": 8, "price": 96000, "count": 10, "power": 8000}
}



PILOTS = {
    "helicopter": {
        "name": "خلبان هلیکوپتر", 
        "icon": "🚁", 
        "price": 12800, 
        "count": 100,
        "for_type": "helicopter"
    },
    "normal": {
        "name": "خلبان عادی", 
        "icon": "🟠", 
        "price": 6400,
        "count": 50,
        "for_type": "normal_fighters",
        "fighters": ["f4", "f18", "j10", "j16", "f16", "su27"]
    },
    "strong": {
        "name": "خلبان قوی", 
        "icon": "🔴", 
        "price": 9600,
        "count": 50,
        "for_type": "strong_fighters", 
        "fighters": ["eurofighter", "j17", "golden_eagle", "j20", "su35", "mig35", "su30"]
    },
    "professional": {
        "name": "خلبان حرفه‌ای", 
        "icon": "⭐", 
        "price": 16000,
        "count": 50,
        "for_type": "professional_fighters",
        "fighters": ["su57", "f35", "su75", "f22", "rafale"]
    }
}



BUILDINGS = {
    "normal_hospital": {"name": "بیمارستان عادی", "icon": "🏥", "price": 6200, "description": "فقط سربازان زخمی رو درمان میکنه | روزانه ۱۵۰۰ جا"},
    "professional_hospital": {"name": "بیمارستان حرفه‌ای", "icon": "🏥", "price": 15500, "description": "همه نوع مریض درمان میشه | روزانه ۳۰۰۰ جا"},
    "barracks": {"name": "پادگان", "icon": "🛕", "price": 23200, "description": "هر فرد بعد ۳ روز یه لول پیشرفت میکنه"},
    "metro": {"name": "ایستگاه مترو", "icon": "🚉", "price": 10800, "description": "برای حمل و نقل داخلی"},
    "airport": {"name": "فرودگاه", "icon": "🛬", "price": 12400, "description": "برای حمل و نقل خارجی"},
    "dock": {"name": "اسکله", "icon": "⛴️", "price": 10800, "description": "برای حمل و نقل تجهیزات از بقیه کشورها"}
}



TOMAN_SHOP_ITEMS = {
    "60000": {"coins": 60000, "price_toman": 60000, "price_text": "شصت هزار تومان"},
    "100000": {"coins": 100000, "price_toman": 100000, "price_text": "صد هزار تومان"},
    "130000": {"coins": 130000, "price_toman": 130000, "price_text": "صد و سی هزار تومان"},
    "180000": {"coins": 180000, "price_toman": 175000, "price_text": "صد و هفتاد و پنج هزار تومان"}
}



VIRUSES = {
    "flu": {"name": "ویروس آنفولانزا", "icon": "🦠", "daily_loss": 200, "hospital_needed": "normal", "damage_base": False},
    "corona": {"name": "ویروس کرونا", "icon": "🦠", "daily_loss": 250, "hospital_needed": "normal", "damage_base": True},
    "zika": {"name": "ویروس زیکا", "icon": "🦠", "daily_loss": 300, "hospital_needed": "normal", "damage_base": False},
    "rabies": {"name": "ویروس هاری", "icon": "🦠", "daily_loss": 500, "hospital_needed": "professional", "damage_base": True},
    "marburg": {"name": "ویروس ماربورگ", "icon": "🦠", "daily_loss": 1000, "hospital_needed": "professional", "damage_base": True}
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
                "can_target": ["navy"], "effectiveness": {"navy": 1.4}}
}
