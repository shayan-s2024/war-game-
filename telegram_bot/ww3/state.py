# -*- coding: utf-8 -*-
"""حالت سراسری بازی: دیتابیس، داده‌های بازیکنان و متغیرهای وضعیت.

نکته مهم: دیکشنری‌های این ماژول با from-import به ماژول‌های دیگر منتقل می‌شوند
و چون فقط mutate می‌شوند (rebind نمی‌شوند) همه ماژول‌ها همان یک نسخه را می‌بینند.
اسکالرهای runtime (war_active، last_update_id و ...) مقدارشان عوض می‌شود،
پس حتماً باید به صورت state.X خوانده/نوشته شوند نه from-import.
"""
import json
import time

from .database import Database
from .config import (
    ATTACK_LIMIT, ATTACK_WINDOW, STATEMENT_LIMIT, STATEMENT_WINDOW,
    SPAM_LIMIT, SPAM_WINDOW, COMMAND_COOLDOWN, PAYMENT_REQUEST_TIMEOUT,
    UNION_DONATION_LIMITS, MAX_ITEM_DONATION,
)

# روز شروع ویروس (با load_game_config از دیتابیس خوانده می‌شود)
virus_start_day = 5

# آخرین روزِ بازی که آسیب ویروس اعمال شده (فقط یک بار در روز)
last_virus_damage_day = None

# کش نتیجه بررسی عضویت کانال‌ها: {user_id: (missing_list, checked_at)}
join_check_cache = {}

# 🔄 پیام منوی قابل ویرایش: {chat_id: message_id} — منوها به‌جای پیام جدید، همین پیام را آپدیت می‌کنند
menu_message = {}

# 🔒 کاربرانی که باید از /start مجدد شروع کنن (بعد از پایان فصل)
force_restart_required = set()


last_update_id = 0



# ==================== متغیرهای حالت انتظار ====================
waiting_for_country = {}


waiting_for_name = {}


waiting_for_statement = {}


waiting_for_tweet = {}




# ==================== محدودیت حمله ====================
user_attacks = {}  # {user_id: [timestamp1, timestamp2, timestamp3]}


waiting_for_broadcast = {}


waiting_for_add_admin = {}


waiting_for_remove_admin = {}


waiting_for_attack_search = {}  # {user_id: True}


waiting_for_war_time = {}


waiting_for_buy_count = {}


waiting_for_union_search = {}


waiting_for_union_create = {}


waiting_for_union_deposit = {}


waiting_for_union_withdraw = {}


waiting_for_attack_target = {}


waiting_for_attack_weapon = {}


waiting_for_attack_count = {}


waiting_for_country_selection = {}


waiting_for_base_location = {}


waiting_for_base_continent = {}


waiting_for_sanction_type = {}


waiting_for_hack_target = {}


waiting_for_hack_type = {}


waiting_for_hack_action = {}


waiting_for_assassination_target = {}


waiting_for_assassination_member = {}


waiting_for_assassination_method = {}


waiting_for_assassination_code = {}


waiting_for_hack_target_info = {}


waiting_for_hack_count = {}


waiting_for_add_virus = {}


waiting_for_cabinet = {}


waiting_for_cabinet_manual = {}


waiting_for_virus_day = {}


waiting_for_union_join_request = {}


waiting_for_sanction_target = {}  # {user_id: True}


waiting_for_edit_player = {}


waiting_for_add_credit = {}


waiting_for_remove_credit = {}


waiting_for_edit_defense = {}


waiting_for_edit_attack = {}


waiting_for_edit_score = {}


waiting_for_edit_population = {}


waiting_for_edit_country = {}


waiting_for_edit_name = {}


waiting_for_give_item = {}


waiting_for_item_count = {}


waiting_for_global_reward_type = {}


waiting_for_global_reward_amount = {}


# ==================== محدودیت بیانیه ====================
user_statements = {}  # {user_id: [timestamp1, timestamp2, timestamp3, timestamp4]}


# ==================== متغیرهای هشدار ====================
warning_sent_users = {}  # {user_id: warning_time}


waiting_for_warning_response = {}  # {user_id: True}


# ==================== متغیرهای اهدا ====================
waiting_for_donation_amount = {}


donation_cooldown = {}


waiting_for_delete_player = {}


waiting_for_confirm_delete = {}


waiting_for_delete_economy_confirm = {}


waiting_for_delete_all_economy = {}


pending_deletions = {}


# ==================== متغیرهای مجوز ساخت پایگاه ====================
waiting_for_base_permission = {}  # {user_id: {"country": xxx, "continent": xxx, "owner_id": xxx}}


country_base_count = {}  # {country_name: count} تعداد پایگاه‌های هر کشور


base_costs = {}  # {base_id: cost} هزینه هر پایگاه


free_countries_with_bases = set()  # کشورهای بدون صاحب که پایگاه دارند


# ==================== متغیرهای زمان جنگ ====================
war_start_time = None


war_end_time = None


war_active = False


last_profit_date = None


game_start_date = time.time()


last_virus_spread = 0


last_daily_check = 0



user_in_cabinet_setup = {}


waiting_for_fix_union_id = {}


pending_incomplete_deletions = {}



# ==================== سیستم ضد اسپم ====================
user_last_command = {}  # {user_id: last_command_time}


user_command_count = {}  # {user_id: {"count": x, "reset_time": y}}



# ==================== سیستم خرید با تومان ====================
waiting_for_payment_screenshot = {}  # {user_id: {"coins": xxx, "amount": xxx, "price_text": xxx}}


pending_payments = {}  # {payment_id: {"user_id": xxx, "coins": xxx, "amount": xxx, "status": "pending", "screenshot_file_id": xxx}}





# ایجاد نمونه از دیتابیس
db = Database()



# ==================== بارگذاری داده‌ها از دیتابیس ====================
players_data = db.load_all_players()


used_countries = db.load_countries()


unions_data = db.load_all_unions()


bases_data = db.load_all_bases()


union_requests = db.load_all_union_requests()


sanctions_data = db.load_sanctions()


cabinet_codes = db.load_all_cabinet_codes()


hack_cooldown = db.load_hack_cooldown()


assassination_cooldown = db.load_assassination_cooldown()


assassination_info = db.load_all_assassination_info()



# ==================== توابع کمکی دیتابیس ====================
def save_data(data=None):
    """همگام‌سازی بازیکن خاص با دیتابیس"""
    for user_id, player_data in players_data.items():
        db.save_player(user_id, player_data)



def save_countries(data):
    for country_name, user_id in data.items():
        db.save_country(country_name, user_id)



def save_unions(data):
    for union_name, union_data in data.items():
        db.save_union(union_name, union_data)



def save_bases(data):
    for base_id, base_data in data.items():
        db.save_base(base_id, base_data)



def save_union_requests(data):
    for req_id, req_data in data.items():
        db.save_union_request(req_id, req_data)



def save_sanctions(data):
    for user_id, sanction_data in data.items():
        db.save_sanction(user_id, sanction_data)



def save_cabinet_codes(data):
    for user_id, codes in data.items():
        for pos_key, code in codes.items():
            db.save_cabinet_code(user_id, pos_key, code)



def save_hack_cooldown(data):
    for user_id, cooldowns in data.items():
        for hack_type, expires_at in cooldowns.items():
            db.save_hack_cooldown(user_id, hack_type, expires_at)



def save_assassination_cooldown(data):
    if "used_codes" in data:
        for code, used_at in data["used_codes"].items():
            db.save_assassination_cooldown(code, used_at)



def save_assassination_info(data):
    for user_id, info in data.items():
        for key, info_data in info.items():
            db.save_assassination_info(user_id, info_data['target_id'], info_data['member_key'], info_data)


# 🔒 سهمیه حملات ماندگار (با ری‌استارت پاک نمی‌شود)
user_attacks = json.loads(db.get_game_config("attack_limits", "{}"))


# ==================== 🏁 توابع پایان فصل ====================
def reset_for_new_season():
    """ریست کامل state برای فصل جدید
    
    این تابع همه داده‌های سراسری رو پاک می‌کنه و متغیرهای runtime رو 
    به مقدار اولیه برمی‌گردونه. بعد از پایان فصل صدا زده میشه.
    """
    global war_active, war_start_time, war_end_time, game_start_date
    global last_profit_date, last_virus_damage_day, last_virus_spread
    global last_daily_check, last_update_id
    
    # 🔄 ریست متغیرهای runtime
    war_active = False
    war_start_time = None
    war_end_time = None
    game_start_date = time.time()
    last_profit_date = None
    last_virus_damage_day = None
    last_virus_spread = 0
    last_daily_check = 0
    last_update_id = 0
    
    # 🔄 پاک کردن کش‌ها
    menu_message.clear()
    join_check_cache.clear()
    
    # 🔄 پاک کردن همه waiting dictها
    _all_waiting_dicts = [
        # کابینه و ثبت‌نام
        waiting_for_name, waiting_for_country_selection, waiting_for_cabinet,
        waiting_for_cabinet_manual, user_in_cabinet_setup,
        waiting_for_country,
        # حمله
        waiting_for_attack_count, waiting_for_attack_search, waiting_for_attack_target,
        waiting_for_attack_weapon, user_attacks,
        # هک و ترور
        waiting_for_hack_count, waiting_for_hack_target, waiting_for_hack_type,
        waiting_for_hack_action, waiting_for_hack_target_info,
        waiting_for_assassination_code, waiting_for_assassination_method,
        waiting_for_assassination_target, waiting_for_assassination_member,
        # خرید و فروشگاه
        waiting_for_buy_count,
        # ادمین
        waiting_for_add_admin, waiting_for_remove_admin, waiting_for_add_credit,
        waiting_for_remove_credit, waiting_for_add_virus, waiting_for_broadcast,
        waiting_for_edit_attack, waiting_for_edit_country, waiting_for_edit_defense,
        waiting_for_edit_name, waiting_for_edit_player, waiting_for_edit_population,
        waiting_for_edit_score, waiting_for_give_item, waiting_for_item_count,
        waiting_for_global_reward_type, waiting_for_global_reward_amount,
        waiting_for_fix_union_id, waiting_for_war_time,
        waiting_for_sanction_target, waiting_for_sanction_type,
        # حذف
        waiting_for_confirm_delete, waiting_for_delete_all_economy,
        waiting_for_delete_economy_confirm, waiting_for_delete_player,
        pending_deletions, pending_incomplete_deletions,
        # بیانیه و توییت
        waiting_for_statement, waiting_for_tweet,
        # پایگاه
        waiting_for_base_location, waiting_for_base_continent,
        waiting_for_base_permission, country_base_count, base_costs,
        free_countries_with_bases,
        # اتحاد
        waiting_for_union_create, waiting_for_union_deposit,
        waiting_for_union_search, waiting_for_union_withdraw,
        waiting_for_union_join_request,
        # اهدا
        waiting_for_donation_amount, donation_cooldown,
        # هشدار
        warning_sent_users, waiting_for_warning_response,
        # پرداخت
        waiting_for_payment_screenshot, pending_payments,
        # محدودیت‌ها
        user_statements, user_last_command, user_command_count,
        # ویروس
        waiting_for_virus_day,
    ]
    
    for d in _all_waiting_dicts:
        try:
            d.clear()
        except Exception as e:
            print(f"⚠️ خطا در پاک کردن {d}: {e}")
    
    # 🔄 پاک کردن dictهای داده‌ای
    players_data.clear()
    used_countries.clear()
    unions_data.clear()
    bases_data.clear()
    union_requests.clear()
    sanctions_data.clear()
    cabinet_codes.clear()
    hack_cooldown.clear()
    assassination_cooldown.clear()
    assassination_info.clear()
    
    # 🔄 پاک کردن لیست force_restart (چون همه از صفر شروع می‌کنن)
    # نکته: این clear قبل از اضافه شدن کاربران جدید به force_restart صدا زده میشه
    # پس نیازی به پاک کردنش نیست — در admin.py بعد از ریست، کاربران جدید اضافه میشن
    
    print("🔄 State برای فصل جدید ریست شد")


def add_force_restart_user(user_id):
    """اضافه کردن کاربر به لیست اجبار به restart"""
    force_restart_required.add(str(user_id))


def remove_force_restart_user(user_id):
    """حذف کاربر از لیست اجبار به restart"""
    force_restart_required.discard(str(user_id))


def is_force_restart(user_id):
    """چک میکنه که آیا کاربر باید restart کنه"""
    return str(user_id) in force_restart_required


def clear_force_restart():
    """پاک کردن کل لیست اجبار به restart"""
    force_restart_required.clear()