# -*- coding: utf-8 -*-
"""Stable ASCII command aliases for country names."""
import re

# A compact Persian/Arabic transliteration that keeps commands predictable.
_TRANS = str.maketrans({
    "ا":"a","آ":"a","أ":"a","إ":"e","ء":"'","ب":"b","پ":"p","ت":"t","ث":"s",
    "ج":"j","چ":"ch","ح":"h","خ":"kh","د":"d","ذ":"z","ر":"r","ز":"z","ژ":"zh",
    "س":"s","ش":"sh","ص":"s","ض":"z","ط":"t","ظ":"z","ع":"a","غ":"gh","ف":"f",
    "ق":"gh","ک":"k","ك":"k","گ":"g","ل":"l","م":"m","ن":"n","و":"v","ه":"h","ی":"y","ي":"y",
    "ى":"y","ة":"h","ؤ":"v","ئ":"y","‌":"-","ٔ":"","ً":"","ٌ":"","ٍ":"","َ":"","ُ":"","ِ":"","ّ":"",
    "۰":"0","۱":"1","۲":"2","۳":"3","۴":"4","۵":"5","۶":"6","۷":"7","۸":"8","۹":"9",
})

ALIASES = {
    "ایران": "iran",
    "آمریکا": "usa",
    "انگلستان": "uk",
    "امارات متحده عربی": "uae",
    "کره جنوبی": "south-korea",
    "کره شمالی": "north-korea",
    "روسیه": "russia",
    "آلمان": "germany",
    "فرانسه": "france",
    "چین": "china",
    "ژاپن": "japan",
    "هند": "india",
    "ترکیه": "turkey",
    "عراق": "iraq",
    "عربستان سعودی": "saudi-arabia",
    "کانادا": "canada",
    "مکزیک": "mexico",
    "برزیل": "brazil",
    "استرالیا": "australia",
    "نیوزیلند": "new-zealand",
    "اسرائیل": "israel",
    "هلند": "netherlands",
    "ایتالیا": "italy",
    "اسپانیا": "spain",
}


def command_name(name: str) -> str:
    raw = ALIASES.get(name, name.translate(_TRANS).lower())
    raw = raw.replace("&", "and")
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or "country"


def unique_command_name(name: str, used: set[str]) -> str:
    base = command_name(name)[:60] or "country"
    candidate = base
    n = 2
    while candidate in used:
        suffix = f"-{n}"
        candidate = f"{base[:72-len(suffix)]}{suffix}"
        n += 1
    used.add(candidate)
    return candidate
