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
from .config import MAIN_ADMIN_ID, REQUIRED_CHANNELS, TOKEN, UNION_DONATION_LIMITS
from .helpers import answer_callback, find_player_by_input, get_missing_channels, get_updates, is_admin, is_spam, send_message, edit_message, show_screen
from .state import (
    assassination_info, db, donation_cooldown, players_data, unions_data,
    user_in_cabinet_setup, waiting_for_add_admin, waiting_for_add_credit,
    waiting_for_add_virus, waiting_for_assassination_code, waiting_for_attack_count,
    waiting_for_attack_search, waiting_for_broadcast, waiting_for_buy_count,
    waiting_for_cabinet_manual, waiting_for_confirm_delete, waiting_for_country_selection,
    waiting_for_delete_all_economy, waiting_for_delete_economy_confirm,
    waiting_for_delete_player, waiting_for_donation_amount, waiting_for_edit_attack,
    waiting_for_edit_country, waiting_for_edit_defense, waiting_for_edit_name,
    waiting_for_edit_player, waiting_for_edit_population, waiting_for_edit_score,
    waiting_for_fix_union_id, waiting_for_give_item, waiting_for_global_reward_type,
    waiting_for_hack_count, waiting_for_name, waiting_for_payment_screenshot,
    waiting_for_remove_admin, waiting_for_remove_credit, waiting_for_sanction_target,
    waiting_for_statement, waiting_for_tweet, waiting_for_union_create,
    waiting_for_union_deposit, waiting_for_union_search, waiting_for_union_withdraw,
    waiting_for_war_time
)
from .static_data import (
    AIRCRAFT_CARRIERS, AIR_DEFENSES, ARTILLERY, BOMBS, BUILDINGS, DRONES,
    ECONOMIC_ITEMS, FIGHTERS, GROUND_FORCES, HACKERS, HELICOPTERS, MINES,
    MISSILES, NAVAL_VESSELS, SUBMARINES, TANKS
)

# ==================== Import همه توابع از ماژول‌های دیگه ====================

# از dashboard
from .dashboard import (
    send_dashboard, send_admin_home, show_my_info, send_my_equipment,
    send_statement_menu, send_statement_to_group, send_tweet_to_group,
    send_invite_message, show_battle_log, get_dashboard_text
)

# از registration
from .registration import (
    send_country_selection_menu, send_countries_of_continent,
    process_country_selection, complete_player_info,
    send_start_button, send_start_button_closed,
    start_name_input, process_name_input, send_join_required,
    handle_check_join, is_registration_available,
    is_registered_player, process_referral, is_registration_closed,
    set_registration_closed, purge_junk_players, award_pending_referral
)

# از cabinet
from .cabinet import (
    start_cabinet_selection, send_cabinet_question, process_cabinet_answer,
    start_manual_cabinet_input, process_manual_cabinet_input,
    finish_cabinet_selection, show_cabinet_options
)

# از shop
from .shop import (
    send_shop_menu, send_shop_economic, send_shop_defense,
    send_shop_offensive, send_shop_building, send_shop_hacker,
    send_shop_bomb, send_shop_pilot, send_shop_missile,
    send_shop_drone, send_shop_helicopter, send_shop_fighter,
    send_shop_tank, send_shop_artillery, send_shop_ground,
    send_shop_navy, send_shop_naval_vehicles, send_shop_submarine,
    send_shop_carrier, ask_for_buy_count, process_buy_item, buy_building
)

# از payments
from .payments import (
    send_shop_toman, toman_purchase_callback, process_payment_screenshot,
    approve_payment, reject_payment, clean_old_payment_requests
)

# از bases
from .bases import (
    send_bases_menu, send_build_base_menu, process_build_base_continent,
    build_base_in_country, allow_base_construction, deny_base_construction,
    debug_bases, clear_all_bases
)

# از unions
from .unions import (
    send_alliance_panel, union_list, union_search, union_production,
    union_wealth, union_power, union_create, show_union_members,
    union_leave, union_treasury_menu, union_deposit, union_withdraw,
    union_upgrade, union_delete, send_join_request, show_union_requests,
    approve_join_request, reject_join_request, process_union_create,
    process_union_search, process_union_deposit, process_union_withdraw,
    union_donate_menu, union_donate_select_target, union_donate_credit,
    union_donate_item, union_donate_item_amount, process_donation_credit,
    process_donation_item, check_expired_requests,
    show_union_kick_menu, union_kick_member
)

# از attack
from .attack import (
    send_attack_menu, show_battle_rules, attack_ground, attack_air,
    attack_helicopter, attack_drone, attack_navy, attack_submarine,
    attack_missile, attack_search_target, process_attack_search,
    attack_select_from_search, attack_weapon_select, ask_attack_count,
    process_attack_count_callback, process_attack, process_attack_text_input,
    attack_bombs_menu, bomb_targets_menu, ask_bomb_count,
    attack_artillery_menu, artillery_targets_menu, ask_artillery_count,
    process_bomb_strike, process_artillery_attack
)

# از hacks
from .hacks import (
    attack_hacker_menu, select_hack_target, process_hack_target_selection,
    process_hack_attack, attack_assassination_menu, select_assassination_member,
    process_assassination_code, execute_hack_defense, attack_hacker_from_search,
    process_hack_from_search, execute_assassination, show_assassination_methods
)

# از admin
from .admin import (
    send_admin_panel, admin_start_war, admin_end_war, admin_broadcast,
    admin_set_war_time, admin_give_virus, process_give_virus,
    admin_manage_admins, admin_add_admin, admin_remove_admin,
    get_admin_stats, admin_change_all_codes,
    admin_complete_players_report, admin_find_incomplete_players,
    admin_send_warning_to_all_incomplete, admin_delete_incomplete_player,
    admin_delete_all_incomplete_players, admin_assign_random_country_to_players,
    admin_close_registration, admin_open_registration,
    admin_registration_status, admin_global_reward_menu,
    process_global_reward, admin_global_reward_amount,
    admin_manage_players, show_player_edit_menu,
    admin_add_credit, admin_remove_credit, admin_edit_defense,
    admin_edit_attack, admin_edit_score, admin_edit_population,
    admin_edit_country, admin_edit_name, admin_give_item_menu,
    admin_give_item, process_give_item, admin_change_player_codes,
    process_add_credit, process_remove_credit, process_edit_defense,
    process_edit_attack, process_edit_score, process_edit_population,
    process_edit_country, process_edit_name,
    admin_delete_player_menu, admin_search_delete_player,
    show_delete_confirmation, execute_player_deletion,
    process_delete_confirm, process_delete_economy_confirm,
    process_delete_all_economy_confirm, process_delete_all_economy_callback,
    process_incomplete_delete_callback,
    admin_show_duplicate_countries, admin_fix_duplicate_countries,
    admin_find_players_without_economy, admin_delete_all_economy_players,
    admin_find_players_without_country, admin_show_players_with_country_no_cabinet,
    admin_list_all_countries, admin_attack_stats,
    admin_send_smart_warning, admin_check_country_status,
    un_search_country, un_select_sanction_from_search,
    un_full_player_list, un_full_player_list_page,
    select_sanction_type, process_un_sanction, remove_sanction,
    admin_auto_assign_country, send_un_panel,
    fix_user_union, admin_fix_union_menu, admin_fix_union_manual,
    process_fix_union_by_id, send_broadcast_to_all,
    admin_end_season_menu, admin_end_season_confirm, admin_show_last_winners
)

# از economy
from .economy import (
    check_and_add_daily_profit, spread_random_virus, apply_virus_damage,
    load_game_config
)

# از guide
from .guide import send_guide_menu, handle_guide


# ==================== پردازش دکمه‌های شیشه‌ای ====================
def process_callback_data(chat_id, user_id, data):
    """پردازش تمام کال‌بک‌های ربات"""
    
    # 📌 message_id پیام فعلی — برای ویرایش پیام‌های منو
    current_message_id = state.menu_message.get(str(chat_id))

    # ==================== 1. بیانیه و توییت ====================
    if data == "new_statement":
        send_message(chat_id, "📝 متن بیانیه را ارسال کن:")
        waiting_for_statement[user_id] = True
        return True
    
    if data == "new_tweet":
        send_message(chat_id, "🐦 متن توییت را ارسال کن:")
        waiting_for_tweet[user_id] = True
        return True
    
    if data == "statement_menu":
        send_statement_menu(chat_id, user_id)
        return True
    
    # ==================== 2. تعداد حمله ====================
    if data.startswith("attack_count_"):
        count = data.replace("attack_count_", "")
        try:
            count_int = int(count)
            if user_id in waiting_for_attack_count:
                attack_data = waiting_for_attack_count.pop(user_id)
                target_id = attack_data["target_id"]
                weapon = attack_data["weapon"]
                max_count = attack_data["max_count"]
                
                if count_int < 1:
                    send_message(chat_id, "❌ تعداد باید حداقل 1 باشد!")
                elif count_int > max_count:
                    weapon_name = "تجهیزات"
                    if weapon == "tank":
                        weapon_name = "تانک"
                    elif weapon == "fighter":
                        weapon_name = "جنگنده"
                    elif weapon == "helicopter":
                        weapon_name = "بالگرد"
                    elif weapon == "drone":
                        weapon_name = "پهپاد"
                    elif weapon == "navy":
                        weapon_name = "ناو جنگی"
                    elif weapon == "submarine":
                        weapon_name = "زیردریایی"
                    elif weapon == "missile":
                        weapon_name = "موشک"
                    send_message(chat_id, f"❌ شما فقط {max_count} عدد {weapon_name} دارید!")
                else:
                    process_attack(chat_id, user_id, target_id, weapon, count_int)
            else:
                send_message(chat_id, "❌ درخواست نامعتبر! دوباره از منوی حمله اقدام کنید.")
        except ValueError:
            send_message(chat_id, "❌ تعداد نامعتبر!")
        return True
    
    # ==================== 3. حمله از طریق جستجو ====================
    if data.startswith("attack_weapon_"):
        parts = data.split("_")
        if len(parts) >= 4:
            weapon = parts[2]
            target_id = parts[3]
            attack_weapon_select(chat_id, user_id, weapon, target_id)
        else:
            send_message(chat_id, "❌ فرمت حمله نامعتبر!")
        return True
    
    if data.startswith("attack_search_select_"):
        target_id = data.replace("attack_search_select_", "")
        attack_select_from_search(chat_id, user_id, target_id)
        return True
    
    if data == "attack_search":
        attack_search_target(chat_id, user_id)
        return True
    
    # ==================== 3.8 🛠 دکمه‌های پنل ادمین ====================
    if data == "admin_manage_players":
        admin_manage_players(chat_id, user_id)
        return True

    if data == "admin_check_country_status":
        admin_check_country_status(chat_id, user_id)
        return True

    if data == "admin_list_countries":
        admin_list_all_countries(chat_id, user_id)
        return True

    if data == "admin_incomplete_players":
        admin_find_incomplete_players(chat_id, user_id)
        return True

    if data == "admin_warning_all_incomplete":
        admin_send_warning_to_all_incomplete(chat_id, user_id)
        return True

    if data == "admin_delete_incomplete_all":
        admin_delete_all_incomplete_players(chat_id, user_id)
        return True

    if data.startswith("admin_delete_incomplete_"):
        admin_delete_incomplete_player(chat_id, user_id, data.replace("admin_delete_incomplete_", ""))
        return True

    if data.startswith("confirm_incomplete_delete_"):
        process_incomplete_delete_callback(chat_id, user_id, data.replace("confirm_incomplete_delete_", ""))
        return True

    if data == "admin_no_economy":
        admin_find_players_without_economy(chat_id, user_id)
        return True

    if data == "admin_delete_all_economy":
        admin_delete_all_economy_players(chat_id, user_id)
        return True

    if data.startswith("confirm_delete_all_"):
        process_delete_all_economy_callback(chat_id, user_id, data.replace("confirm_delete_all_", ""))
        return True

    if data == "admin_no_country":
        admin_find_players_without_country(chat_id, user_id)
        return True

    if data == "admin_delete_no_cabinet":
        admin_show_players_with_country_no_cabinet(chat_id, user_id)
        return True

    if data == "admin_delete_no_country":
        admin_find_players_without_country(chat_id, user_id)
        return True

    if data == "admin_duplicate_countries":
        admin_show_duplicate_countries(chat_id, user_id)
        return True

    if data == "admin_fix_duplicate_countries":
        admin_fix_duplicate_countries(chat_id, user_id)
        return True

    if data == "admin_stats":
        get_admin_stats(chat_id)
        return True

    if data == "admin_change_all_codes":
        admin_change_all_codes(chat_id, user_id)
        return True

    if data == "admin_auto_assign_country":
        admin_assign_random_country_to_players(chat_id, user_id)
        return True

    # 🏁 پایان فصل
    if data == "admin_end_season":
        admin_end_season_menu(chat_id, user_id)
        return True

    if data == "admin_end_season_confirm":
        admin_end_season_confirm(chat_id, user_id)
        return True

    if data == "admin_show_last_winners":
        admin_show_last_winners(chat_id, user_id)
        return True

    # 🎁 اهدای آیتم به بازیکن
    if data.startswith("admin_give_"):
        rest = data.replace("admin_give_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            item_type, target_id = parts[0], parts[1]
            if item_type.startswith("mine_"):
                admin_give_item(chat_id, user_id, target_id, "mine", item_key=item_type.replace("mine_", ""))
            else:
                admin_give_item(chat_id, user_id, target_id, item_type)
            return True

    # 🌐 صفحه‌بندی سازمان ملل
    if data.startswith("un_page_"):
        page_str = data.replace("un_page_", "")
        if page_str.isdigit():
            un_full_player_list_page(chat_id, user_id, int(page_str))
            return True

    if data == "un_full_list":
        un_full_player_list(chat_id, user_id)
        return True

    if data == "un_search":
        un_search_country(chat_id, user_id)
        return True

    # ==================== 3.7 📖 راهنما (با editMessageText) ====================
    if data == "guide" or data.startswith("guide_"):
        handle_guide(chat_id, user_id, data, message_id=current_message_id)
        return True

    # ==================== 3.6 💣💥 تسلیحات ویژه ====================
    if data == "attack_bombs":
        attack_bombs_menu(chat_id, user_id)
        return True

    if data == "attack_artillery":
        attack_artillery_menu(chat_id, user_id)
        return True

    if data.startswith("bomb_type_"):
        bomb_targets_menu(chat_id, user_id, data.replace("bomb_type_", ""))
        return True

    if data.startswith("bomb_target_"):
        _rest = data.replace("bomb_target_", "")
        _tid, _, _bkey = _rest.rpartition("_")
        ask_bomb_count(chat_id, user_id, _tid, _bkey)
        return True

    if data.startswith("artillery_type_"):
        artillery_targets_menu(chat_id, user_id, data.replace("artillery_type_", ""))
        return True

    if data.startswith("artillery_target_"):
        _rest = data.replace("artillery_target_", "")
        _tid, _, _akey = _rest.rpartition("_")
        ask_artillery_count(chat_id, user_id, _tid, _akey)
        return True

    # ==================== 3.5 جوین اجباری ====================
    if data == "check_join":
        handle_check_join(chat_id, user_id)
        return True

    if data == "my_battles":
        show_battle_log(chat_id, user_id)
        return True

    # ==================== 4. منوی اصلی ====================
    if data == "start_game":
        if is_admin(user_id) and players_data.get(user_id, {}).get("player_name"):
            send_dashboard(chat_id, user_id)
            return True
        available, msg = is_registration_available()
        if not available:
            send_start_button_closed(chat_id, msg)
            return True
        if is_registered_player(user_id):
            send_dashboard(chat_id, user_id)
        else:
            start_name_input(chat_id, user_id)
        return True
    
    if data == "dashboard":
        send_dashboard(chat_id, user_id)
        return True
    
    if data == "back_to_continents":
        state.menu_message.pop(str(chat_id), None)
        send_country_selection_menu(chat_id, user_id)
        return True
    
    # ==================== 5. تجهیزات و اطلاعات ====================
    if data == "my_equipment":
        send_my_equipment(chat_id, user_id)
        return True
    
    if data == "my_info":
        show_my_info(chat_id, user_id)
        return True
    
    if data == "leaderboard":
        sorted_players = sorted(players_data.items(), key=lambda x: x[1].get('score', 0), reverse=True)[:10]
        text = "🏆 **لیدربرد**\n━━━━━━━━━━━━━━━━━━\n"
        for i, (uid, pdata) in enumerate(sorted_players, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
            text += f"\n{medal} {i}. {pdata.get('player_name')}\n   🌍 {pdata.get('country')}\n   🏆 {pdata.get('score', 0)} امتیاز\n━━━━━━━━━━━━━━━━━━"
        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت به داشبورد", "callback_data": "dashboard"}]]}
        show_screen(chat_id, text, keyboard)
        return True
    
    # ==================== 6. فروشگاه ====================
    if data == "shop_menu":
        send_shop_menu(chat_id)
        return True
    
    if data == "shop_toman":
        send_shop_toman(chat_id)
        return True
    
    if data == "shop_economic":
        send_shop_economic(chat_id)
        return True
    
    if data == "shop_defense":
        send_shop_defense(chat_id)
        return True
    
    if data == "shop_offensive":
        send_shop_offensive(chat_id)
        return True
    
    if data == "shop_building":
        send_shop_building(chat_id)
        return True
    
    if data == "shop_hacker":
        send_shop_hacker(chat_id)
        return True
    
    if data == "shop_bomb":
        send_shop_bomb(chat_id)
        return True
    
    if data == "shop_pilot":
        send_shop_pilot(chat_id)
        return True
    
    if data == "shop_missile":
        send_shop_missile(chat_id)
        return True
    
    if data == "shop_drone":
        send_shop_drone(chat_id)
        return True
    
    if data == "shop_helicopter":
        send_shop_helicopter(chat_id)
        return True
    
    if data == "shop_fighter":
        send_shop_fighter(chat_id)
        return True
    
    if data == "shop_tank":
        send_shop_tank(chat_id)
        return True
    
    if data == "shop_artillery":
        send_shop_artillery(chat_id)
        return True
    
    if data == "shop_ground":
        send_shop_ground(chat_id)
        return True
    
    if data == "shop_navy":
        send_shop_navy(chat_id)
        return True
    
    if data == "shop_naval_vehicles":
        send_shop_naval_vehicles(chat_id)
        return True
    
    if data == "shop_submarine":
        send_shop_submarine(chat_id)
        return True
    
    if data == "shop_carrier":
        send_shop_carrier(chat_id)
        return True
    
    # ==================== 7. خریدها ====================
    if data.startswith("buy_mine_"):
        key = data.replace("buy_mine_", "")
        if key in MINES:
            item = MINES[key]
            ask_for_buy_count(chat_id, user_id, "mine", key, item["name"], item["price"], profit=item["daily_profit"])
        return True
    
    if data.startswith("buy_economic_"):
        key = data.replace("buy_economic_", "")
        if key in ECONOMIC_ITEMS:
            item = ECONOMIC_ITEMS[key]
            ask_for_buy_count(chat_id, user_id, "economic", key, item["name"], item["price"], profit=item["profit"])
        return True
    
    if data.startswith("buy_defense_"):
        key = data.replace("buy_defense_", "")
        if key in AIR_DEFENSES:
            item = AIR_DEFENSES[key]
            ask_for_buy_count(chat_id, user_id, "defense", key, item["name"], item["price"], defense=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_tank_"):
        key = data.replace("buy_tank_", "")
        if key in TANKS:
            item = TANKS[key]
            ask_for_buy_count(chat_id, user_id, "tank", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_fighter_"):
        key = data.replace("buy_fighter_", "")
        if key in FIGHTERS:
            item = FIGHTERS[key]
            ask_for_buy_count(chat_id, user_id, "fighter", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_helicopter_"):
        key = data.replace("buy_helicopter_", "")
        if key in HELICOPTERS:
            item = HELICOPTERS[key]
            ask_for_buy_count(chat_id, user_id, "helicopter", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_missile_"):
        key = data.replace("buy_missile_", "")
        if key in MISSILES:
            item = MISSILES[key]
            ask_for_buy_count(chat_id, user_id, "missile", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_hacker_"):
        key = data.replace("buy_hacker_", "")
        if key in HACKERS:
            item = HACKERS[key]
            ask_for_buy_count(chat_id, user_id, "hacker", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_bomb_"):
        key = data.replace("buy_bomb_", "")
        if key in BOMBS:
            item = BOMBS[key]
            ask_for_buy_count(chat_id, user_id, "bomb", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_drone_"):
        key = data.replace("buy_drone_", "")
        if key in DRONES:
            item = DRONES[key]
            ask_for_buy_count(chat_id, user_id, "drone", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_artillery_"):
        key = data.replace("buy_artillery_", "")
        if key in ARTILLERY:
            item = ARTILLERY[key]
            ask_for_buy_count(chat_id, user_id, "artillery", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_ground_"):
        key = data.replace("buy_ground_", "")
        if key in GROUND_FORCES:
            item = GROUND_FORCES[key]
            ask_for_buy_count(chat_id, user_id, "ground", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_naval_"):
        key = data.replace("buy_naval_", "")
        if key in NAVAL_VESSELS:
            item = NAVAL_VESSELS[key]
            ask_for_buy_count(chat_id, user_id, "naval", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_submarine_"):
        key = data.replace("buy_submarine_", "")
        if key in SUBMARINES:
            item = SUBMARINES[key]
            ask_for_buy_count(chat_id, user_id, "submarine", key, item["name"], item["price"], power=item["power"], count_per_unit=item["count"])
        return True
    
    if data.startswith("buy_carrier_"):
        key = data.replace("buy_carrier_", "")
        if key in AIRCRAFT_CARRIERS:
            item = AIRCRAFT_CARRIERS[key]
            ask_for_buy_count(chat_id, user_id, "carrier", key, item["name"], item["price"])
        return True
    
    if data.startswith("buy_building_"):
        key = data.replace("buy_building_", "")
        if key in BUILDINGS:
            buy_building(chat_id, user_id, key)
        return True
    
    # ==================== 8. فروشگاه تومان ====================
    if data.startswith("buy_toman_"):
        coins_key = data.replace("buy_toman_", "")
        toman_purchase_callback(chat_id, user_id, coins_key)
        return True
    
    if data.startswith("approve_payment_"):
        payment_id = data.replace("approve_payment_", "")
        approve_payment(chat_id, user_id, payment_id)
        return True
    
    if data.startswith("reject_payment_"):
        payment_id = data.replace("reject_payment_", "")
        reject_payment(chat_id, user_id, payment_id)
        return True
    
    # ==================== 9. پایگاه‌ها ====================
    if data == "bases_menu":
        send_bases_menu(chat_id, user_id)
        return True
    
    if data == "build_base_menu":
        send_build_base_menu(chat_id, user_id)
        return True
    
    if data.startswith("build_base_continent_"):
        continent = data.replace("build_base_continent_", "")
        process_build_base_continent(chat_id, user_id, continent)
        return True
    
    if data.startswith("build_base_country_"):
        parts = data.split("_")
        if len(parts) >= 5:
            continent = parts[3]
            country_name = "_".join(parts[4:])
            build_base_in_country(chat_id, user_id, continent, country_name)
        return True
    
    if data.startswith("allow_base_"):
        parts = data.split("_")
        if len(parts) >= 4:
            requester_id = parts[2]
            country_name = "_".join(parts[3:])
            allow_base_construction(chat_id, user_id, requester_id, country_name)
        return True
    
    if data.startswith("deny_base_"):
        parts = data.split("_")
        if len(parts) >= 4:
            requester_id = parts[2]
            country_name = "_".join(parts[3:])
            deny_base_construction(chat_id, user_id, requester_id, country_name)
        return True
    
    if data == "debug_bases":
        debug_bases(chat_id, user_id)
        return True
    
    if data == "clear_bases":
        clear_all_bases(chat_id, user_id)
        return True
    
    # ==================== 10. اتحاد ====================
    if data == "alliance":
        send_alliance_panel(chat_id, user_id)
        return True
    
    if data == "union_list":
        union_list(chat_id)
        return True
    
    if data == "union_search":
        union_search(chat_id, user_id)
        return True
    
    if data == "union_production":
        union_production(chat_id)
        return True
    
    if data == "union_wealth":
        union_wealth(chat_id)
        return True
    
    if data == "union_power":
        union_power(chat_id)
        return True
    
    if data == "union_create":
        union_create(chat_id, user_id)
        return True
    
    if data.startswith("union_members_"):
        show_union_members(chat_id, data.replace("union_members_", ""))
        return True
    
    if data.startswith("union_leave_"):
        union_leave(chat_id, user_id, data.replace("union_leave_", ""))
        return True
    
    if data.startswith("union_treasury_"):
        union_treasury_menu(chat_id, user_id, data.replace("union_treasury_", ""))
        return True
    
    if data.startswith("union_deposit_"):
        union_deposit(chat_id, user_id, data.replace("union_deposit_", ""))
        return True
    
    if data.startswith("union_withdraw_"):
        union_withdraw(chat_id, user_id, data.replace("union_withdraw_", ""))
        return True
    
    if data.startswith("union_upgrade_"):
        union_upgrade(chat_id, user_id, data.replace("union_upgrade_", ""))
        return True
    
    if data.startswith("union_delete_"):
        union_delete(chat_id, user_id, data.replace("union_delete_", ""))
        return True
    
    if data.startswith("union_join_request_"):
        union_name = data.replace("union_join_request_", "")
        send_join_request(chat_id, user_id, union_name)
        return True
    
    if data.startswith("union_requests_"):
        union_name = data.replace("union_requests_", "")
        show_union_requests(chat_id, user_id, union_name)
        return True
    
    # ==================== 11. اهدا در اتحاد ====================
    if data.startswith("union_donate_select_"):
        target_id = data.replace("union_donate_select_", "")
        union_donate_select_target(chat_id, user_id, target_id)
        return True
    
    if data.startswith("union_donate_credit_"):
        target_id = data.replace("union_donate_credit_", "")
        union_donate_credit(chat_id, user_id, target_id)
        return True
    
    if data.startswith("union_donate_item_mine_"):
        rest = data.replace("union_donate_item_mine_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            item_key, target_id = parts[0], parts[1]
            union_donate_item_amount(chat_id, user_id, "mine", item_key, target_id)
        return True
    
    if data.startswith("union_donate_item_fighter_"):
        rest = data.replace("union_donate_item_fighter_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            item_key, target_id = parts[0], parts[1]
            union_donate_item_amount(chat_id, user_id, "fighter", item_key, target_id)
        return True
    
    if data.startswith("union_donate_item_tank_"):
        rest = data.replace("union_donate_item_tank_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            item_key, target_id = parts[0], parts[1]
            union_donate_item_amount(chat_id, user_id, "tank", item_key, target_id)
        return True
    
    if data.startswith("union_donate_item_missile_"):
        rest = data.replace("union_donate_item_missile_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            item_key, target_id = parts[0], parts[1]
            union_donate_item_amount(chat_id, user_id, "missile", item_key, target_id)
        return True
    
    if data.startswith("union_donate_item_helicopter_"):
        rest = data.replace("union_donate_item_helicopter_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            item_key, target_id = parts[0], parts[1]
            union_donate_item_amount(chat_id, user_id, "helicopter", item_key, target_id)
        return True
    
    if data.startswith("union_donate_item_drone_"):
        rest = data.replace("union_donate_item_drone_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            item_key, target_id = parts[0], parts[1]
            union_donate_item_amount(chat_id, user_id, "drone", item_key, target_id)
        return True
    
    if data.startswith("union_donate_item_defense_"):
        rest = data.replace("union_donate_item_defense_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            item_key, target_id = parts[0], parts[1]
            union_donate_item_amount(chat_id, user_id, "defense", item_key, target_id)
        return True
    
    if data.startswith("union_donate_item_"):
        target_id = data.replace("union_donate_item_", "")
        union_donate_item(chat_id, user_id, target_id)
        return True
    
    if data.startswith("union_donate_"):
        union_name = data.replace("union_donate_", "")
        if union_name and union_name != "":
            user_union = players_data.get(user_id, {}).get("union")
            if user_union == union_name:
                union_donate_menu(chat_id, user_id, union_name)
            else:
                send_message(chat_id, f"❌ شما عضو اتحاد {union_name} نیستید!")
        return True
    
    # ==================== 12. اخراج از اتحاد ====================
    if data.startswith("union_kick_menu_"):
        union_name = data.replace("union_kick_menu_", "")
        show_union_kick_menu(chat_id, user_id, union_name)
        return True
    
    if data.startswith("union_kick_"):
        rest = data.replace("union_kick_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            union_name, target_id = parts[0], parts[1]
            union_kick_member(chat_id, user_id, union_name, target_id)
        return True
    
    # ==================== 13. درخواست‌های عضویت ====================
    if data.startswith("approve_request_"):
        request_id = data.replace("approve_request_", "")
        approve_join_request(chat_id, user_id, request_id)
        return True
    
    if data.startswith("reject_request_"):
        request_id = data.replace("reject_request_", "")
        reject_join_request(chat_id, user_id, request_id)
        return True
    
    # ==================== 14. حمله و جنگ ====================
    if data == "attack_menu":
        send_attack_menu(chat_id, user_id)
        return True
    
    if data == "battle_rules":
        show_battle_rules(chat_id)
        return True
    
    if data == "attack_ground":
        attack_ground(chat_id, user_id)
        return True
    
    if data == "attack_air":
        attack_air(chat_id, user_id)
        return True
    
    if data == "attack_helicopter":
        attack_helicopter(chat_id, user_id)
        return True
    
    if data == "attack_drone":
        attack_drone(chat_id, user_id)
        return True
    
    if data == "attack_navy":
        attack_navy(chat_id, user_id)
        return True
    
    if data == "attack_submarine":
        attack_submarine(chat_id, user_id)
        return True
    
    if data == "attack_missile":
        attack_missile(chat_id, user_id)
        return True
    
    if data == "attack_hacker":
        attack_hacker_menu(chat_id, user_id)
        return True
    
    if data == "attack_assassination":
        attack_assassination_menu(chat_id, user_id)
        return True
    
    if data == "hack_weak":
        select_hack_target(chat_id, user_id, "weak")
        return True
    
    if data == "hack_medium":
        select_hack_target(chat_id, user_id, "medium")
        return True
    
    if data == "hack_strong":
        select_hack_target(chat_id, user_id, "strong")
        return True
    
    if data.startswith("hack_target_"):
        target_id = data.replace("hack_target_", "")
        process_hack_target_selection(chat_id, user_id, target_id)
        return True
    
    if data.startswith("hack_count_"):
        count = data.replace("hack_count_", "")
        if user_id in waiting_for_hack_count:
            hack_data = waiting_for_hack_count.pop(user_id)
            try:
                count_int = int(count)
                process_hack_attack(chat_id, user_id, hack_data["target_id"], hack_data["hacker_level"], count_int)
            except ValueError:
                send_message(chat_id, "❌ تعداد نامعتبر!")
        return True
    
    if data.startswith("hack_defense_"):
        execute_hack_defense(chat_id, user_id)
        return True
    
    if data.startswith("attack_hacker_target_"):
        target_id = data.replace("attack_hacker_target_", "")
        attack_hacker_from_search(chat_id, user_id, target_id)
        return True
    
    if data.startswith("hack_search_medium_"):
        target_id = data.replace("hack_search_medium_", "")
        process_hack_from_search(chat_id, user_id, "medium", target_id)
        return True
    
    if data.startswith("hack_search_strong_"):
        target_id = data.replace("hack_search_strong_", "")
        process_hack_from_search(chat_id, user_id, "strong", target_id)
        return True
    
    if data.startswith("attack_weapon_back_"):
        target_id = data.replace("attack_weapon_back_", "")
        attack_select_from_search(chat_id, user_id, target_id)
        return True
    
    if data.startswith("attack_target_"):
        parts = data.split("_")
        if len(parts) >= 4:
            ask_attack_count(chat_id, user_id, parts[2], parts[3])
        return True
    
    if data.startswith("missile_target_"):
        target_id = data.replace("missile_target_", "")
        ask_attack_count(chat_id, user_id, target_id, "missile")
        return True
    
    if data.startswith("assassinate_target_"):
        target_id = data.replace("assassinate_target_", "")
        if user_id in assassination_info and assassination_info[user_id]:
            select_assassination_member(chat_id, user_id, target_id)
        else:
            send_message(chat_id, "❌ شما هیچ کد امنیتی از کابینه دشمنان ندارید!\n\n💻 ابتدا با هکرهای متوسط یا قوی، کدهای کابینه را بدزدید.")
        return True
    
    if data.startswith("assassinate_method_"):
        parts = data.replace("assassinate_method_", "").split("_")
        if len(parts) >= 3:
            method = parts[0]
            target_id = parts[1]
            member_key = parts[2]
            execute_assassination(chat_id, user_id, method, target_id, member_key)
        return True
    
    if data.startswith("assassinate_member_"):
        send_message(chat_id, "⚠️ در حال توسعه...")
        return True
    
    # ==================== 15. دعوت دوستان ====================
    if data == "invite":
        send_invite_message(chat_id, user_id)
        return True
    
    # ==================== 16. تکمیل اطلاعات ====================
    if data == "complete_info":
        complete_player_info(chat_id, user_id)
        return True
    
    # ==================== 17. پنل ادمین ====================
    if data == "admin_panel":
        send_admin_panel(chat_id, user_id)
        return True
    
    if data == "admin_start_war":
        admin_start_war(chat_id, user_id)
        return True
    
    if data == "admin_end_war":
        admin_end_war(chat_id, user_id)
        return True
    
    if data == "admin_complete_report":
        admin_complete_players_report(chat_id, user_id)
        return True
    
    if data == "admin_broadcast":
        admin_broadcast(chat_id, user_id)
        return True
    
    if data == "admin_war_time":
        admin_set_war_time(chat_id, user_id)
        return True
    
    if data == "admin_war_close":
        state.war_start_time = None
        state.war_end_time = None
        send_message(chat_id, "✅ جنگ بسته شد!")
        send_admin_panel(chat_id, user_id)
        return True
    
    if data == "admin_give_virus":
        admin_give_virus(chat_id, user_id)
        return True
    
    if data == "admin_manage_admins":
        admin_manage_admins(chat_id, user_id)
        return True
    
    if data == "admin_add_admin":
        admin_add_admin(chat_id, user_id)
        return True
    
    if data == "admin_remove_admin":
        admin_remove_admin(chat_id, user_id)
        return True
    
    if data == "admin_close_registration":
        admin_close_registration(chat_id, user_id)
        return True
    
    if data == "admin_open_registration":
        admin_open_registration(chat_id, user_id)
        return True
    
    if data == "admin_registration_status":
        admin_registration_status(chat_id, user_id)
        return True
    
    if data == "admin_attack_stats":
        admin_attack_stats(chat_id, user_id)
        return True
    
    if data == "admin_smart_warning":
        admin_send_smart_warning(chat_id, user_id)
        return True
    
    if data == "admin_random_country":
        admin_assign_random_country_to_players(chat_id, user_id)
        return True
    
    if data == "admin_global_reward":
        admin_global_reward_menu(chat_id, user_id)
        return True
    
    if data.startswith("global_reward_"):
        reward_type = data.replace("global_reward_", "")
        admin_global_reward_amount(chat_id, user_id, reward_type)
        return True
    
    if data.startswith("admin_edit_player_"):
        target_id = data.replace("admin_edit_player_", "")
        show_player_edit_menu(chat_id, user_id, target_id)
        return True
    
    if data.startswith("admin_change_player_codes_"):
        target_id = data.replace("admin_change_player_codes_", "")
        admin_change_player_codes(chat_id, user_id, target_id)
        return True
    
    if data.startswith("admin_add_credit_"):
        target_id = data.replace("admin_add_credit_", "")
        admin_add_credit(chat_id, user_id, target_id)
        return True
    
    if data.startswith("admin_remove_credit_"):
        target_id = data.replace("admin_remove_credit_", "")
        admin_remove_credit(chat_id, user_id, target_id)
        return True
    
    if data.startswith("admin_edit_defense_"):
        target_id = data.replace("admin_edit_defense_", "")
        admin_edit_defense(chat_id, user_id, target_id)
        return True
    
    if data.startswith("admin_edit_attack_"):
        target_id = data.replace("admin_edit_attack_", "")
        admin_edit_attack(chat_id, user_id, target_id)
        return True
    
    if data.startswith("admin_edit_score_"):
        target_id = data.replace("admin_edit_score_", "")
        admin_edit_score(chat_id, user_id, target_id)
        return True
    
    if data == "admin_delete_player":
        admin_delete_player_menu(chat_id, user_id)
        return True
    
    if data.startswith("admin_delete_confirm_"):
        target_id = data.replace("admin_delete_confirm_", "")
        if target_id in players_data:
            player_data = players_data[target_id]
            player = {
                "user_id": target_id,
                "name": player_data.get("player_name", "نامشخص"),
                "country": player_data.get("country", "نامشخص"),
                "credit": player_data.get("credit", 0),
                "score": player_data.get("score", 0),
                "union": player_data.get("union", "ندارد"),
                "daily_profit": player_data.get("daily_profit", 0),
                "defense": player_data.get("defense", 0),
                "attack_power": player_data.get("attack_power", 0),
                "created_at": player_data.get("created_at", 0)
            }
            show_delete_confirmation(chat_id, user_id, player)
        else:
            send_message(chat_id, "❌ بازیکن یافت نشد!")
        return True
    
    if data.startswith("admin_edit_population_"):
        target_id = data.replace("admin_edit_population_", "")
        admin_edit_population(chat_id, user_id, target_id)
        return True
    
    if data.startswith("admin_edit_country_"):
        target_id = data.replace("admin_edit_country_", "")
        admin_edit_country(chat_id, user_id, target_id)
        return True
    
    if data.startswith("admin_edit_name_"):
        target_id = data.replace("admin_edit_name_", "")
        admin_edit_name(chat_id, user_id, target_id)
        return True
    
    # ==================== خرید خلبان ====================
    if data == "buy_pilot_helicopter":
        ask_for_buy_count(chat_id, user_id, "pilot", "helicopter", "خلبان هلیکوپتر", 12800, count_per_unit=100)
        return True

    if data == "buy_pilot_normal":
        ask_for_buy_count(chat_id, user_id, "pilot", "normal", "خلبان عادی", 6400, count_per_unit=50)
        return True

    if data == "buy_pilot_strong":
        ask_for_buy_count(chat_id, user_id, "pilot", "strong", "خلبان قوی", 9600, count_per_unit=50)
        return True

    if data == "buy_pilot_professional":
        ask_for_buy_count(chat_id, user_id, "pilot", "professional", "خلبان حرفه‌ای", 16000, count_per_unit=50)
        return True
    
    if data.startswith("admin_give_item_"):
        target_id = data.replace("admin_give_item_", "")
        admin_give_item_menu(chat_id, user_id, target_id)
        return True
    
    if data.startswith("admin_fix_union_"):
        target_id = data.replace("admin_fix_union_", "")
        if target_id.isdigit():
            fix_user_union(chat_id, user_id, target_id)
        else:
            admin_fix_union_menu(chat_id, user_id)
        return True
    
    if data == "admin_fix_union_manual":
        admin_fix_union_manual(chat_id, user_id)
        return True
    
    # ==================== 18. سازمان ملل ====================
    if data == "un_panel":
        send_un_panel(chat_id, user_id)
        return True
    
    if data.startswith("un_sanction_select_"):
        target_id = data.replace("un_sanction_select_", "")
        un_select_sanction_from_search(chat_id, user_id, target_id)
        return True
    
    if data.startswith("sanction_select_"):
        target_id = data.replace("sanction_select_", "")
        select_sanction_type(chat_id, user_id, target_id)
        return True
    
    if data.startswith("sanction_light_"):
        target_id = data.replace("sanction_light_", "")
        process_un_sanction(chat_id, user_id, target_id, "light")
        return True
    
    if data.startswith("sanction_heavy_"):
        target_id = data.replace("sanction_heavy_", "")
        process_un_sanction(chat_id, user_id, target_id, "heavy")
        return True
    
    # ==================== 19. کابینه (فلو جدید با editMessageText) ====================
    if data.startswith("cabinet_"):
        if data == "cabinet_back":
            send_cabinet_question(chat_id, user_id, message_id=current_message_id)
        elif data == "cabinet_finish":
            finish_cabinet_selection(chat_id, user_id, message_id=current_message_id)
        elif data.startswith("cabinet_manual_"):
            key = data.replace("cabinet_manual_", "")
            start_manual_cabinet_input(chat_id, user_id, key, message_id=current_message_id)
        elif data.startswith("cabinet_pick_"):
            key = data.replace("cabinet_pick_", "")
            show_cabinet_options(chat_id, user_id, key, message_id=current_message_id)
        elif data.startswith("cabinet_show_"):
            send_message(chat_id, "ℹ️ این مقام قبلاً انتخاب شده. برای تغییر، روی دکمه‌اش بزنید.")
        elif data.startswith("cabinet_set_"):
            rest = data.replace("cabinet_set_", "")
            parts = rest.rsplit("_", 1)
            if len(parts) == 2:
                key, opt_idx = parts[0], parts[1]
                process_cabinet_answer(chat_id, user_id, key, opt_idx, message_id=current_message_id)
        return True
    
    # ==================== 20. انتخاب قاره و کشور (پیام جدید) ====================
    if data.startswith("continent_"):
        continent = data.replace("continent_", "")
        state.menu_message.pop(str(chat_id), None)
        send_countries_of_continent(chat_id, continent)
        return True
    
    if data.startswith("select_country_"):
        if waiting_for_country_selection.get(user_id):
            country_name = data.replace("select_country_", "")
            process_country_selection(chat_id, user_id, country_name)
        return True
    
    # ==================== 21. اگر هیچکدام ====================
    print(f"⚠️ Unknown callback: {data}")
    send_message(chat_id, "⚠️ در حال توسعه...")
    return True


# ==================== حلقه اصلی ====================
def main():
    from . import state
    
    print("✅ ربات جنگ جهانی روشن شد...")
    print("🔑 توکن ربات:", TOKEN[:20] + "...")
    print(f"👥 بازیکنان بارگذاری شده: {len(players_data)}")
    
    load_game_config()
    removed = purge_junk_players()
    if removed:
        print(f"🧹 {removed} اکانت بی‌نام و ناقص پاک شد")
    print(f"📅 تاریخ شروع: {time.ctime(state.game_start_date)}")
    print(f"🦠 روز شروع ویروس: {state.virus_start_day}")
    
    while True:
        try:
            check_and_add_daily_profit()
            spread_random_virus()
            apply_virus_damage()
            check_expired_requests()
            clean_old_payment_requests()
            updates = get_updates()
            
            for update in updates:
                state.last_update_id = update["update_id"]
                
                if "message" in update:
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    user_id = str(chat_id)
                    
                    # 🔒 جوین اجباری کانال
                    if (REQUIRED_CHANNELS and message.get("chat", {}).get("type") == "private"
                            and not is_admin(user_id) and get_missing_channels(user_id)):
                        send_join_required(chat_id, user_id)
                        continue

                    # پردازش عکس (رسید خرید)
                    if "photo" in message:
                        # 📌 چک کن اگه کاربر باید restart کنه (بعد از پایان فصل)
                        if state.is_force_restart(user_id):
                            send_message(chat_id,
                                "🏁 **فصل جدید شروع شده!**\n"
                                "━━━━━━━━━━━━━━━━━━\n"
                                "📌 برای شرکت در فصل جدید، لطفاً دستور /start را بفرستید.")
                            continue
                        
                        if user_id in waiting_for_payment_screenshot:
                            photo = message["photo"][-1]
                            file_id = photo["file_id"]
                            caption = message.get("caption", "")
                            process_payment_screenshot(chat_id, user_id, file_id, caption)
                        else:
                            send_message(chat_id, "❌ شما هیچ درخواست خرید فعالی ندارید!")
                        continue
                    
                    # پردازش متن
                    if "text" in message:
                        text = message["text"].strip()
                        chat_id = message["chat"]["id"]
                        user_id = str(chat_id)
                        
                        # ==================== 📌 چک فصل جدید ====================
                        if state.is_force_restart(user_id):
                            # فقط /start مجاز
                            if text == "/start" or text.startswith("/start"):
                                # کاربر مجدداً شروع کرد → از لیست حذف کن
                                state.remove_force_restart_user(user_id)
                                # ادامه به پردازش /start پایین‌تر
                            else:
                                # پیام «ابتدا /start بزن»
                                send_message(chat_id,
                                    "🏁 **فصل جدید شروع شده!**\n"
                                    "━━━━━━━━━━━━━━━━━━\n"
                                    "📌 برای شرکت در فصل جدید، لطفاً دستور /start را بفرستید.")
                                continue
                        
                        # بررسی اسپم
                        is_spammer, spam_message = is_spam(user_id)
                        if is_spammer:
                            send_message(chat_id, spam_message)
                            continue
                        
                        # ==================== 0. دکمه‌های Reply Keyboard ====================
                        if text == "🚀 شروع":
                            # معادل دکمه start_game
                            if is_admin(user_id) and players_data.get(user_id, {}).get("player_name"):
                                send_dashboard(chat_id, user_id)
                                continue
                            if is_registered_player(user_id):
                                send_dashboard(chat_id, user_id)
                            else:
                                available, msg = is_registration_available()
                                if not available:
                                    send_start_button_closed(chat_id, msg)
                                else:
                                    start_name_input(chat_id, user_id)
                            continue
                        
                        if text == "🔄 بروزرسانی":
                            # معادل دکمه dashboard (ویرایش پیام)
                            if is_registered_player(user_id) or is_admin(user_id):
                                send_dashboard(chat_id, user_id)
                            else:
                                send_message(chat_id, "🔒 **ابتدا باید ثبت‌نام کنید!**\nدستور /start را بفرستید.")
                            continue
                        
                        if text == "👥 دعوت دوستان":
                            # معادل دکمه invite
                            if is_registered_player(user_id):
                                send_invite_message(chat_id, user_id)
                            else:
                                send_message(chat_id, "🔒 **ابتدا باید ثبت‌نام کنید!**\nدستور /start را بفرستید.")
                            continue
                        
                        if text == "📖 راهنمای بازی":
                            # معادل دکمه guide
                            if is_registered_player(user_id) or is_admin(user_id):
                                state.menu_message.pop(str(chat_id), None)
                                send_guide_menu(chat_id)
                            else:
                                send_message(chat_id, "🔒 **ابتدا باید ثبت‌نام کنید!**\nدستور /start را بفرستید.")
                            continue
                        
                        if text == "📜 نبردهای من":
                            # معادل دکمه my_battles
                            if is_registered_player(user_id):
                                show_battle_log(chat_id, user_id)
                            else:
                                send_message(chat_id, "🔒 **ابتدا باید ثبت‌نام کنید!**\nدستور /start را بفرستید.")
                            continue
                        
                        # ==================== اولویت 1: تایید عملیات حساس ====================
                        if user_id in waiting_for_delete_economy_confirm:
                            waiting_for_delete_economy_confirm.pop(user_id, None)
                            process_delete_economy_confirm(chat_id, user_id, text)
                            continue

                        if user_id in waiting_for_delete_all_economy:
                            waiting_for_delete_all_economy.pop(user_id, None)
                            process_delete_all_economy_confirm(chat_id, user_id, text)
                            continue

                        if user_id in waiting_for_delete_player:
                            waiting_for_delete_player.pop(user_id, None)
                            admin_search_delete_player(chat_id, user_id, text)
                            continue

                        if user_id in waiting_for_confirm_delete:
                            process_delete_confirm(chat_id, user_id, text)
                            continue

                        if user_id in waiting_for_fix_union_id:
                            waiting_for_fix_union_id.pop(user_id, None)
                            process_fix_union_by_id(chat_id, user_id, text)
                            continue
                        
                        # ==================== اولویت 2: کابینه (فلو جدید با editMessageText) ====================
                        if user_in_cabinet_setup.get(user_id):
                            if user_id in waiting_for_cabinet_manual:
                                process_manual_cabinet_input(chat_id, user_id, text)
                            else:
                                current_message_id = state.menu_message.get(str(chat_id))
                                send_message(chat_id, "⚠️ **لطفاً از دکمه‌های بالا یکی از گزینه‌ها را انتخاب کنید!**")
                                send_cabinet_question(chat_id, user_id, message_id=current_message_id)
                            continue
                        
                        # 🔒 گیت ثبت‌نام
                        if not is_registered_player(user_id) and not is_admin(user_id):
                            if not text.startswith("/start") and user_id not in waiting_for_name:
                                if message.get("chat", {}).get("type") == "private":
                                    send_message(chat_id, "🔒 **برای استفاده از ربات ابتدا باید ثبت‌نام کنید!**\nدستور /start را بفرستید.")
                                continue

                        # ==================== اولویت 3: استارت ====================
                        if text == "/start" or text.startswith("/start"):
                            referrer_id = None
                            
                            if " " in text:
                                parts = text.split()
                                if len(parts) > 1 and parts[1].startswith("ref_"):
                                    referrer_id = parts[1].replace("ref_", "")
                            
                            if not referrer_id and "?" in text:
                                parts = text.split("?")
                                if len(parts) > 1:
                                    query = parts[1]
                                    if query.startswith("start=ref_"):
                                        referrer_id = query.replace("start=ref_", "")
                                    elif "ref_" in query:
                                        for param in query.split("&"):
                                            if param.startswith("ref_"):
                                                referrer_id = param.replace("ref_", "")
                                            elif "=ref_" in param:
                                                referrer_id = param.split("=ref_")[1]
                            
                            if not referrer_id and "ref_" in text:
                                match = re.search(r'ref_(\d+)', text)
                                if match:
                                    referrer_id = match.group(1)
                            
                            # 👑 ادمین‌ها همیشه مستقیم وارد می‌شوند
                            if is_admin(user_id):
                                if players_data.get(user_id, {}).get("player_name"):
                                    state.menu_message.pop(str(chat_id), None)
                                    send_dashboard(chat_id, user_id)
                                else:
                                    send_admin_home(chat_id, user_id)
                                continue
                            
                            if user_id in players_data:
                                user = players_data[user_id]
                                has_country = user.get("country") and user.get("country") != ""
                                has_cabinet = user.get("cabinet") and len(user.get("cabinet", {})) == 5
                                has_name = user.get("player_name")
                                
                                if has_name and has_country and has_cabinet:
                                    state.menu_message.pop(str(chat_id), None)
                                    send_dashboard(chat_id, user_id)
                                else:
                                    send_start_button(chat_id, user_id, is_existing_player=True)
                            else:
                                available, msg = is_registration_available()
                                if not available:
                                    send_start_button_closed(chat_id, msg)
                                else:
                                    if referrer_id:
                                        process_referral(user_id, referrer_id)
                                    send_start_button(chat_id, user_id, is_existing_player=False)
                            continue
                        
                        # جستجوی هدف برای حمله
                        if waiting_for_attack_search.get(user_id):
                            process_attack_search(chat_id, user_id, text)
                            waiting_for_attack_search.pop(user_id, None)
                            continue
                        
                        # ==================== اولویت 4: ثبت نام بازیکن ====================
                        if waiting_for_name.get(user_id):
                            process_name_input(chat_id, user_id, text)
                            continue
                        
                        # جستجوی کشور در سازمان ملل
                        if waiting_for_sanction_target.get(user_id):
                            process_un_search_country(chat_id, user_id, text)
                            waiting_for_sanction_target.pop(user_id, None)
                            continue
                        
                        # ==================== اولویت 5: بقیه waiting_for ها ====================
                        if waiting_for_statement.get(user_id):
                            if len(text) >= 3:
                                send_statement_to_group(chat_id, user_id, text)
                                waiting_for_statement.pop(user_id)
                            else:
                                send_message(chat_id, "❌ متن حداقل ۳ کاراکتر!")
                            continue
                        
                        if user_id in waiting_for_cabinet_manual:
                            process_manual_cabinet_input(chat_id, user_id, text)
                            continue
                        
                        if user_id in waiting_for_donation_amount:
                            try:
                                count = int(text.replace(',', '').replace(' ', ''))
                                if count <= 0:
                                    send_message(chat_id, "❌ تعداد باید بیشتر از 0 باشد!")
                                    del waiting_for_donation_amount[user_id]
                                    continue
                                
                                donation_data = waiting_for_donation_amount.pop(user_id)
                                target_id = donation_data["target_id"]
                                donation_type = donation_data["type"]
                                
                                if donation_type == "credit":
                                    user_union = players_data.get(user_id, {}).get("union")
                                    union_info = unions_data.get(user_union, {})
                                    donation_limit = UNION_DONATION_LIMITS.get(union_info.get('level', 1), 20000)
                                    
                                    if count > donation_limit:
                                        send_message(chat_id, f"❌ مبلغ اهدا بیشتر از سقف مجاز ({donation_limit:,}) است!")
                                        continue
                                    
                                    if count > players_data.get(user_id, {}).get("credit", 0):
                                        send_message(chat_id, f"❌ موجودی شما کافی نیست!")
                                        continue
                                    
                                    players_data[user_id]["credit"] = players_data[user_id].get("credit", 0) - count
                                    players_data[target_id]["credit"] = players_data[target_id].get("credit", 0) + count
                                    donation_cooldown[user_id] = time.time()
                                    
                                    db.save_player(user_id, players_data[user_id])
                                    db.save_player(target_id, players_data[target_id])
                                    
                                    send_message(chat_id, f"✅ **{count:,} سکه به {players_data[target_id].get('player_name')} اهدا شد!**")
                                    send_message(int(target_id), f"🎁 **شما {count:,} سکه از {players_data[user_id].get('player_name')} دریافت کردید!**")
                                    send_alliance_panel(chat_id, user_id)
                                    
                                elif donation_type == "item":
                                    category = donation_data["category"]
                                    item_key = donation_data["item_key"]
                                    process_donation_item(chat_id, user_id, count, target_id, category, item_key)
                            except ValueError:
                                send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")
                            continue
                        
                        if waiting_for_tweet.get(user_id):
                            if 3 <= len(text) <= 1000:
                                send_tweet_to_group(chat_id, user_id, text)
                                waiting_for_tweet.pop(user_id)
                            else:
                                send_message(chat_id, "❌ متن باید ۳ تا ۱۰۰۰ کاراکتر!")
                            continue
                        
                        if waiting_for_broadcast.get(user_id):
                            success = send_broadcast_to_all(text)
                            waiting_for_broadcast.pop(user_id)
                            send_message(chat_id, f"✅ بیانیه به {success} نفر ارسال شد!")
                            send_admin_panel(chat_id, user_id)
                            continue
                        
                        if user_id in waiting_for_global_reward_type:
                            reward_type = waiting_for_global_reward_type.pop(user_id)
                            process_global_reward(chat_id, user_id, reward_type, text)
                            continue
                        
                        if waiting_for_war_time.get(user_id):
                            try:
                                parts = text.split("-")
                                start_hour = int(parts[0])
                                end_hour = int(parts[1])
                                today = time.localtime()
                                start_time = time.mktime((today.tm_year, today.tm_mon, today.tm_mday, start_hour, 0, 0, 0, 0, 0))
                                end_time = time.mktime((today.tm_year, today.tm_mon, today.tm_mday, end_hour, 0, 0, 0, 0, 0))
                                if end_time < start_time:
                                    end_time += 86400
                                state.war_start_time = start_time
                                state.war_end_time = end_time
                                waiting_for_war_time.pop(user_id)
                                send_message(chat_id, f"✅ جنگ تنظیم شد: {start_hour}:00 تا {end_hour}:00")
                                send_admin_panel(chat_id, user_id)
                            except:
                                send_message(chat_id, "❌ فرمت نامعتبر! مثال: 20-22")
                            continue
                        
                        if waiting_for_add_admin.get(user_id):
                            if text.isdigit() and text != MAIN_ADMIN_ID:
                                if db.add_admin(text):
                                    send_message(chat_id, f"✅ ادمین {text} اضافه شد!")
                                else:
                                    send_message(chat_id, f"❌ کاربر {text} قبلاً ادمین است!")
                            else:
                                send_message(chat_id, "❌ آیدی نامعتبر!")
                            waiting_for_add_admin.pop(user_id)
                            send_admin_panel(chat_id, user_id)
                            continue

                        if waiting_for_remove_admin.get(user_id):
                            if text.isdigit() and text != MAIN_ADMIN_ID:
                                if db.remove_admin(text):
                                    send_message(chat_id, f"✅ ادمین {text} حذف شد!")
                                else:
                                    send_message(chat_id, f"❌ کاربر {text} ادمین نیست یا قابل حذف نیست!")
                            else:
                                send_message(chat_id, "❌ آیدی نامعتبر!")
                            waiting_for_remove_admin.pop(user_id)
                            send_admin_panel(chat_id, user_id)
                            continue
                        
                        if waiting_for_union_create.get(user_id):
                            process_union_create(chat_id, user_id, text)
                            waiting_for_union_create.pop(user_id)
                            continue
                        
                        if waiting_for_union_search.get(user_id):
                            process_union_search(chat_id, text)
                            waiting_for_union_search.pop(user_id)
                            continue
                        
                        if user_id in waiting_for_union_deposit:
                            process_union_deposit(chat_id, user_id, waiting_for_union_deposit.pop(user_id), text)
                            continue
                        
                        if user_id in waiting_for_union_withdraw:
                            process_union_withdraw(chat_id, user_id, waiting_for_union_withdraw.pop(user_id), text)
                            continue
                        
                        if user_id in waiting_for_attack_count:
                            if process_attack_text_input(chat_id, user_id, text):
                                waiting_for_attack_count.pop(user_id, None)
                            continue
                        
                        if user_id in waiting_for_assassination_code:
                            process_assassination_code(chat_id, user_id, text)
                            waiting_for_assassination_code.pop(user_id, None)
                            continue
                        
                        if user_id in waiting_for_buy_count:
                            try:
                                count = int(text)
                                if count > 0:
                                    buy_info = waiting_for_buy_count.pop(user_id)
                                    process_buy_item(chat_id, user_id, buy_info["category"], buy_info["item_key"], count)
                                else:
                                    send_message(chat_id, "❌ تعداد باید بیشتر از 0 باشد!")
                            except ValueError:
                                send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید!")
                            continue
                        
                        if waiting_for_add_virus.get(user_id):
                            parts = text.split()
                            if len(parts) >= 2:
                                process_give_virus(chat_id, user_id, parts[0], parts[1])
                            else:
                                send_message(chat_id, "❌ فرمت: آیدی نام_ویروس")
                            waiting_for_add_virus.pop(user_id)
                            send_admin_panel(chat_id, user_id)
                            continue
                        
                        if user_id in waiting_for_edit_player:
                            target_id, player_name = find_player_by_input(text)
                            if target_id:
                                waiting_for_edit_player.pop(user_id)
                                show_player_edit_menu(chat_id, user_id, target_id)
                            else:
                                send_message(chat_id, f"❌ بازیکنی با مشخصات '{text}' یافت نشد!")
                            continue
                        
                        if user_id in waiting_for_add_credit:
                            process_add_credit(chat_id, user_id, text)
                            continue
                        
                        if user_id in waiting_for_remove_credit:
                            process_remove_credit(chat_id, user_id, text)
                            continue
                        
                        if user_id in waiting_for_edit_defense:
                            process_edit_defense(chat_id, user_id, text)
                            continue
                        
                        if user_id in waiting_for_edit_attack:
                            process_edit_attack(chat_id, user_id, text)
                            continue
                        
                        if user_id in waiting_for_edit_score:
                            process_edit_score(chat_id, user_id, text)
                            continue
                        
                        if user_id in waiting_for_edit_population:
                            process_edit_population(chat_id, user_id, text)
                            continue
                        
                        if user_id in waiting_for_edit_country:
                            process_edit_country(chat_id, user_id, text)
                            continue
                        
                        if user_id in waiting_for_edit_name:
                            process_edit_name(chat_id, user_id, text)
                            continue
                        
                        if user_id in waiting_for_give_item:
                            process_give_item(chat_id, user_id, text)
                            continue
                        
                        else:
                            pass
                
                # ==================== پردازش Callback ====================
                elif "callback_query" in update:
                    callback = update["callback_query"]
                    chat_id = callback["message"]["chat"]["id"]
                    data = callback["data"]
                    callback_id = callback["id"]
                    user_id = str(chat_id)
                    
                    answer_callback(callback_id)

                    # 📌 چک کن اگه کاربر باید restart کنه (بعد از پایان فصل)
                    if state.is_force_restart(user_id):
                        send_message(chat_id,
                            "🏁 **فصل جدید شروع شده!**\n"
                            "━━━━━━━━━━━━━━━━━━\n"
                            "📌 برای شرکت در فصل جدید، لطفاً دستور /start را بفرستید.")
                        continue

                    # 🔄 ذخیره پیام منو برای ویرایش
                    try:
                        state.menu_message[str(chat_id)] = callback["message"]["message_id"]
                    except Exception:
                        pass

                    # 🔒 جوین اجباری کانال
                    if (REQUIRED_CHANNELS and not is_admin(user_id)
                            and data != "check_join" and not data.startswith("guide")
                            and get_missing_channels(user_id)):
                        send_join_required(chat_id, user_id)
                        continue
                    
                    # ⚠️ کاربر وسط کابینه
                    if user_in_cabinet_setup.get(user_id):
                        if data.startswith("cabinet_"):
                            if not process_callback_data(chat_id, user_id, data):
                                send_message(chat_id, "⚠️ در حال توسعه...")
                        else:
                            current_message_id = state.menu_message.get(str(chat_id))
                            send_message(chat_id, "⚠️ **لطفاً ابتدا کابینه خود را تکمیل کنید!**")
                            send_cabinet_question(chat_id, user_id, message_id=current_message_id)
                        continue
                    
                    # 🔒 گیت ثبت‌نام برای دکمه‌ها
                    if not is_registered_player(user_id) and not is_admin(user_id):
                        if data not in ("start_game", "complete_info", "check_join") and not data.startswith("guide"):
                            send_message(chat_id, "🔒 **برای استفاده از ربات ابتدا باید ثبت‌نام کنید!**\nدستور /start را بفرستید.")
                            continue

                    if not process_callback_data(chat_id, user_id, data):
                        send_message(chat_id, "⚠️ در حال توسعه...")
                        
        except KeyboardInterrupt:
            print("\n❌ ربات متوقف شد")
            break
        except Exception as e:
            print(f"خطا: {e}")
            time.sleep(3)