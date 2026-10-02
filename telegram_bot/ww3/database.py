import requests
import json
import os
import time
import random
import math
import sqlite3
import shutil
import re
from datetime import datetime, timedelta

from .config import MAIN_ADMIN_ID

# ==================== کلاس دیتابیس SQLite ====================

# ==================== مسیر دیتابیس: کنار کد (پوشه پروژه) ====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_DB_PATH = r"D:\bot_bale\game_data.db"


class Database:
    
    def __init__(self, db_file=None):
        self.db_file = db_file or os.environ.get("WW3_DB_PATH") or os.path.join(BASE_DIR, "game_data.db")
        # اگر دیتابیس کنار کد نبود ولی دیتابیس قدیمی در مسیر قبلی بود، خودکار منتقل می‌شود
        if (not os.path.exists(self.db_file)
                and os.path.abspath(self.db_file) != os.path.abspath(LEGACY_DB_PATH)
                and os.path.exists(LEGACY_DB_PATH)):
            shutil.copy2(LEGACY_DB_PATH, self.db_file)
            print(f"📦 دیتابیس قدیمی از {LEGACY_DB_PATH} به {self.db_file} منتقل شد")
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_file, check_same_thread=False)
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # جدول بازیکنان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id TEXT PRIMARY KEY,
                player_name TEXT,
                country TEXT,
                continent TEXT,
                union_name TEXT,
                credit INTEGER DEFAULT 10000,
                defense INTEGER DEFAULT 5000,
                attack_power INTEGER DEFAULT 0,
                daily_profit INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                population INTEGER DEFAULT 10000,
                invite_count INTEGER DEFAULT 0,
                referred_by TEXT,
                cabinet TEXT,
                active_viruses TEXT,
                cabinet_changed INTEGER DEFAULT 0,
                created_at REAL DEFAULT CURRENT_TIMESTAMP,
                updated_at REAL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول تجهیزات بازیکنان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_items (
                user_id TEXT,
                item_key TEXT,
                item_value INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, item_key)
            )
        ''')
        
        # جدول کشورهای استفاده شده
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS used_countries (
                country_name TEXT PRIMARY KEY,
                user_id TEXT
            )
        ''')
        
        # جدول ادمین‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id TEXT PRIMARY KEY
            )
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO admins (user_id) VALUES (?)
        ''', (MAIN_ADMIN_ID,))
        
        # جدول اتحادها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unions (
                union_name TEXT PRIMARY KEY,
                union_id TEXT UNIQUE,
                owner TEXT,
                owner_name TEXT,
                level INTEGER DEFAULT 1,
                treasury INTEGER DEFAULT 0,
                total_deposits INTEGER DEFAULT 0,
                total_withdrawals INTEGER DEFAULT 0,
                created_at TEXT,
                members TEXT
            )
        ''')
        
        # جدول پایگاه‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bases (
                base_id TEXT PRIMARY KEY,
                owner TEXT,
                country TEXT,
                country_emoji TEXT,
                continent TEXT,
                built_at REAL,
                ready_at REAL,
                ground_troops INTEGER DEFAULT 0,
                air_troops INTEGER DEFAULT 0,
                max_ground INTEGER DEFAULT 5000,
                max_air INTEGER DEFAULT 1000
            )
        ''')
        
        # جدول درخواست‌های اتحاد
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS union_requests (
                request_id TEXT PRIMARY KEY,
                user_id TEXT,
                user_name TEXT,
                user_country TEXT,
                user_score INTEGER,
                union_name TEXT,
                union_owner TEXT,
                request_time REAL,
                expiry_time REAL,
                status TEXT
            )
        ''')
        
        # جدول تحریم‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sanctions (
                user_id TEXT PRIMARY KEY,
                sanction_type TEXT,
                sanctioner TEXT,
                sanctioner_name TEXT,
                start_date REAL,
                end_date REAL,
                price_penalty REAL
            )
        ''')
        
        # جدول کدهای کابینه
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cabinet_codes (
                user_id TEXT,
                position_key TEXT,
                code TEXT,
                PRIMARY KEY (user_id, position_key)
            )
        ''')
        
        # جدول کدهای استفاده شده ترور
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assassination_cooldown (
                code TEXT PRIMARY KEY,
                used_at REAL
            )
        ''')
        
        # جدول اطلاعات سرقت شده برای ترور
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assassination_info (
                user_id TEXT,
                target_id TEXT,
                position_key TEXT,
                code TEXT,
                member_name TEXT,
                position_name TEXT,
                icon TEXT,
                obtained_at REAL,
                PRIMARY KEY (user_id, target_id, position_key)
            )
        ''')
        
        # جدول هک
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hack_cooldown (
                user_id TEXT,
                hack_type TEXT,
                expires_at REAL,
                PRIMARY KEY (user_id, hack_type)
            )
        ''')
        
        # جدول تنظیمات بازی
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # جدول وضعیت جنگ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS war_status (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # 📜 تاریخچه نبردها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS battle_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                ts REAL,
                text TEXT
            )
        ''')

        # 🏆 جدول برندگان فصل‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS season_winners (
                season_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                player_name TEXT,
                country TEXT,
                score INTEGER,
                credit INTEGER,
                defense INTEGER,
                attack_power INTEGER,
                population INTEGER,
                rank INTEGER,
                ended_at REAL
            )
        ''')

        # 📝 جدول پیام‌های ربات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                message_id INTEGER,
                ts REAL
            )
        ''')

        # تنظیمات پیش‌فرض
        cursor.execute('''
            INSERT OR IGNORE INTO game_config (key, value) VALUES ('virus_start_day', '5')
        ''')
        cursor.execute('''
            INSERT OR IGNORE INTO game_config (key, value) VALUES ('game_start_date', ?)
        ''', (str(time.time()),))
        
        conn.commit()
        conn.close()
        print("✅ دیتابیس SQLite با موفقیت ایجاد شد!")
        print(f"👑 ادمین اصلی با آیدی {MAIN_ADMIN_ID} اضافه شد")
    
    # ==================== توابع ادمین ====================
    def is_admin(self, user_id, required_level=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (str(user_id),))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def add_admin(self, user_id):
        if self.is_admin(user_id):
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO admins (user_id) VALUES (?)', (str(user_id),))
        conn.commit()
        conn.close()
        return True
    
    def remove_admin(self, user_id):
        if user_id == MAIN_ADMIN_ID:
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM admins WHERE user_id = ?', (str(user_id),))
        conn.commit()
        conn.close()
        return True
    
    def get_all_admins(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM admins')
        admins = [row[0] for row in cursor.fetchall()]
        conn.close()
        return admins
    
    # ==================== توابع بازیکنان ====================
    def save_player(self, user_id, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        cabinet_json = json.dumps(data.get('cabinet', {}))
        active_viruses_json = json.dumps(data.get('active_viruses', {}))

        cursor.execute('SELECT created_at FROM players WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        created_at = row[0] if row and row[0] else time.time()

        cursor.execute('''
            INSERT OR REPLACE INTO players
            (user_id, player_name, country, continent, union_name, credit, defense,
             attack_power, daily_profit, score, population, invite_count, referred_by,
             cabinet, active_viruses, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, data.get('player_name'), data.get('country'), data.get('continent'),
            data.get('union'), data.get('credit', 10000), data.get('defense', 5000),
            data.get('attack_power', 0), data.get('daily_profit', 0), data.get('score', 0),
            data.get('population', 10000), data.get('invite_count', 0), data.get('referred_by'),
            cabinet_json, active_viruses_json, created_at, time.time()
        ))

        items = [(user_id, key, value)
                 for key, value in data.items()
                 if key not in ('player_name', 'country', 'continent', 'union', 'cabinet',
                                'active_viruses', 'credit', 'defense', 'attack_power',
                                'daily_profit', 'score', 'population', 'invite_count',
                                'referred_by', 'created_at')
                 and isinstance(value, (int, float))]
        if items:
            cursor.executemany('''
                INSERT OR REPLACE INTO player_items (user_id, item_key, item_value)
                VALUES (?, ?, ?)
            ''', items)

        conn.commit()
        conn.close()

    def load_player(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        columns = [d[0] for d in cursor.description]
        player_data = dict(zip(columns, row))
        player_data['cabinet'] = json.loads(player_data.get('cabinet') or '{}')
        player_data['active_viruses'] = json.loads(player_data.get('active_viruses') or '{}')
        player_data['union'] = player_data.pop('union_name', None)

        cursor.execute('SELECT item_key, item_value FROM player_items WHERE user_id = ?', (user_id,))
        for item_row in cursor.fetchall():
            player_data[item_row[0]] = item_row[1]

        conn.close()
        return player_data

    def load_all_players(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM players')
        columns = [d[0] for d in cursor.description]
        players = {}
        for row in cursor.fetchall():
            p = dict(zip(columns, row))
            p['cabinet'] = json.loads(p.get('cabinet') or '{}')
            p['active_viruses'] = json.loads(p.get('active_viruses') or '{}')
            p['union'] = p.pop('union_name', None)
            players[p['user_id']] = p
        cursor.execute('SELECT user_id, item_key, item_value FROM player_items')
        for uid, key, val in cursor.fetchall():
            if uid in players:
                players[uid][key] = val
        conn.close()
        return players
    
    def delete_player(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM players WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM player_items WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    # ==================== توابع کشورها ====================
    def save_country(self, country_name, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO used_countries (country_name, user_id) VALUES (?, ?)', 
                      (country_name, user_id))
        conn.commit()
        conn.close()
    
    def load_countries(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT country_name, user_id FROM used_countries')
        countries = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return countries
    
    def remove_country(self, country_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM used_countries WHERE country_name = ?', (country_name,))
        conn.commit()
        conn.close()
    
    # ==================== توابع اتحاد ====================
    def save_union(self, union_name, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        members_json = json.dumps(data.get('members', []))
        cursor.execute('''
            INSERT OR REPLACE INTO unions 
            (union_name, union_id, owner, owner_name, level, treasury, total_deposits, total_withdrawals, created_at, members)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            union_name, data.get('union_id'), data.get('owner'), data.get('owner_name'),
            data.get('level', 1), data.get('treasury', 0), data.get('total_deposits', 0),
            data.get('total_withdrawals', 0), data.get('created_at'), members_json
        ))
        conn.commit()
        conn.close()
    
    def load_union(self, union_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM unions WHERE union_name = ?', (union_name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = ['union_name', 'union_id', 'owner', 'owner_name', 'level', 'treasury', 
                      'total_deposits', 'total_withdrawals', 'created_at', 'members']
            data = dict(zip(columns, row))
            data['members'] = json.loads(data.get('members', '[]'))
            return data
        return None
    
    def load_all_unions(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT union_name FROM unions')
        unions = {}
        for row in cursor.fetchall():
            data = self.load_union(row[0])
            if data:
                unions[row[0]] = data
        conn.close()
        return unions
    
    def delete_union(self, union_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM unions WHERE union_name = ?', (union_name,))
        conn.commit()
        conn.close()
    
    # ==================== توابع پایگاه ====================
    def save_base(self, base_id, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO bases 
            (base_id, owner, country, country_emoji, continent, built_at, ready_at, 
             ground_troops, air_troops, max_ground, max_air)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            base_id, data.get('owner'), data.get('country'), data.get('country_emoji'),
            data.get('continent'), data.get('built_at'), data.get('ready_at'),
            data.get('ground_troops', 0), data.get('air_troops', 0),
            data.get('max_ground', 5000), data.get('max_air', 1000)
        ))
        conn.commit()
        conn.close()
    
    def load_all_bases(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM bases')
        bases = {}
        columns = ['base_id', 'owner', 'country', 'country_emoji', 'continent', 'built_at', 
                   'ready_at', 'ground_troops', 'air_troops', 'max_ground', 'max_air']
        for row in cursor.fetchall():
            base_data = dict(zip(columns, row))
            bases[row[0]] = base_data
        conn.close()
        return bases
    
    def delete_base(self, base_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM bases WHERE base_id = ?', (base_id,))
        conn.commit()
        conn.close()
    
    def delete_all_bases(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM bases')
        conn.commit()
        conn.close()
    
    # ==================== توابع درخواست اتحاد ====================
    def save_union_request(self, request_id, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO union_requests 
            (request_id, user_id, user_name, user_country, user_score, union_name, 
             union_owner, request_time, expiry_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request_id, data.get('user_id'), data.get('user_name'), data.get('user_country'),
            data.get('user_score'), data.get('union_name'), data.get('union_owner'),
            data.get('request_time'), data.get('expiry_time'), data.get('status')
        ))
        conn.commit()
        conn.close()
    
    def load_all_union_requests(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM union_requests')
        requests = {}
        columns = ['request_id', 'user_id', 'user_name', 'user_country', 'user_score', 
                   'union_name', 'union_owner', 'request_time', 'expiry_time', 'status']
        for row in cursor.fetchall():
            req_data = dict(zip(columns, row))
            requests[row[0]] = req_data
        conn.close()
        return requests
    
    def update_union_request_status(self, request_id, status):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE union_requests SET status = ? WHERE request_id = ?', (status, request_id))
        conn.commit()
        conn.close()
    
    # ==================== توابع تحریم ====================
    def save_sanction(self, user_id, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO sanctions 
            (user_id, sanction_type, sanctioner, sanctioner_name, start_date, end_date, price_penalty)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, data.get('type'), data.get('sanctioner'), data.get('sanctioner_name'),
            data.get('start_date'), data.get('end_date'), data.get('price_penalty')
        ))
        conn.commit()
        conn.close()
    
    def load_sanctions(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sanctions')
        sanctions = {}
        columns = ['user_id', 'type', 'sanctioner', 'sanctioner_name', 'start_date', 'end_date', 'price_penalty']
        for row in cursor.fetchall():
            sanction_data = dict(zip(columns, row))
            sanctions[row[0]] = sanction_data
        conn.close()
        return sanctions
    
    def remove_sanction(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sanctions WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    # ==================== توابع کدهای کابینه ====================
    def save_cabinet_code(self, user_id, position_key, code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO cabinet_codes (user_id, position_key, code)
            VALUES (?, ?, ?)
        ''', (user_id, position_key, code))
        conn.commit()
        conn.close()
    
    def load_cabinet_codes(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT position_key, code FROM cabinet_codes WHERE user_id = ?', (user_id,))
        codes = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return codes
    
    def load_all_cabinet_codes(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, position_key, code FROM cabinet_codes')
        codes = {}
        for row in cursor.fetchall():
            if row[0] not in codes:
                codes[row[0]] = {}
            codes[row[0]][row[1]] = row[2]
        conn.close()
        return codes
    
    def delete_cabinet_code(self, user_id, position_key):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cabinet_codes WHERE user_id = ? AND position_key = ?', (user_id, position_key))
        conn.commit()
        conn.close()
    
    def delete_all_cabinet_codes(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cabinet_codes')
        conn.commit()
        conn.close()
    
    # ==================== توابع ترور ====================
    def save_assassination_cooldown(self, code, used_at):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO assassination_cooldown (code, used_at) VALUES (?, ?)', (code, used_at))
        conn.commit()
        conn.close()
    
    def load_assassination_cooldown(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT code, used_at FROM assassination_cooldown')
        cooldowns = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return cooldowns
    
    def save_assassination_info(self, user_id, target_id, position_key, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO assassination_info 
            (user_id, target_id, position_key, code, member_name, position_name, icon, obtained_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, target_id, position_key, data.get('code'), data.get('member_name'),
            data.get('position_name'), data.get('icon'), data.get('obtained_at')
        ))
        conn.commit()
        conn.close()
    
    def load_assassination_info(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT target_id, position_key, code, member_name, position_name, icon, obtained_at 
            FROM assassination_info WHERE user_id = ?
        ''', (user_id,))
        info = {}
        for row in cursor.fetchall():
            key = f"{row[0]}_{row[1]}"
            info[key] = {
                'target_id': row[0],
                'member_key': row[1],
                'code': row[2],
                'member_name': row[3],
                'position_name': row[4],
                'icon': row[5],
                'obtained_at': row[6]
            }
        conn.close()
        return info
    
    def load_all_assassination_info(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, target_id, position_key, code, member_name, position_name, icon, obtained_at FROM assassination_info')
        info = {}
        for row in cursor.fetchall():
            if row[0] not in info:
                info[row[0]] = {}
            key = f"{row[1]}_{row[2]}"
            info[row[0]][key] = {
                'target_id': row[1],
                'member_key': row[2],
                'code': row[3],
                'member_name': row[4],
                'position_name': row[5],
                'icon': row[6],
                'obtained_at': row[7]
            }
        conn.close()
        return info
    
    # ==================== توابع هک ====================
    def save_hack_cooldown(self, user_id, hack_type, expires_at):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO hack_cooldown (user_id, hack_type, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, hack_type, expires_at))
        conn.commit()
        conn.close()
    
    def load_hack_cooldown(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, hack_type, expires_at FROM hack_cooldown')
        cooldowns = {}
        for row in cursor.fetchall():
            if row[0] not in cooldowns:
                cooldowns[row[0]] = {}
            cooldowns[row[0]][row[1]] = row[2]
        conn.close()
        return cooldowns
    
    # ==================== توابع تنظیمات بازی ====================
    def get_game_config(self, key, default=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM game_config WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        return default
    
    def delete_game_config_key(self, key):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM game_config WHERE key = ?', (key,))
        conn.commit()
        conn.close()

    def set_game_config(self, key, value):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO game_config (key, value) VALUES (?, ?)', (key, str(value)))
        conn.commit()
        conn.close()
    
    # ==================== توابع وضعیت جنگ ====================
    def get_war_status(self, key, default=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM war_status WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        return default
    
    def set_war_status(self, key, value):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO war_status (key, value) VALUES (?, ?)', (key, str(value)))
        conn.commit()
        conn.close()

    # ==================== 📜 تاریخچه نبردها ====================
    def add_battle_log(self, user_id, text):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO battle_logs (user_id, ts, text) VALUES (?, ?, ?)',
                       (user_id, time.time(), text))
        cursor.execute("""
            DELETE FROM battle_logs WHERE user_id = ? AND log_id NOT IN
            (SELECT log_id FROM battle_logs WHERE user_id = ? ORDER BY log_id DESC LIMIT 10)
        """, (user_id, user_id))
        conn.commit()
        conn.close()

    def get_battle_log(self, user_id, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT ts, text FROM battle_logs WHERE user_id = ? ORDER BY log_id DESC LIMIT ?',
                       (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return rows

    # ==================== معرفی‌های در انتظار ====================
    def set_pending_referral(self, user_id, referrer_id):
        self.set_game_config(f"pending_referral_{user_id}", str(referrer_id))

    def get_pending_referral(self, user_id):
        return self.get_game_config(f"pending_referral_{user_id}")

    def delete_pending_referral(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM game_config WHERE key = ?', (f"pending_referral_{user_id}",))
        conn.commit()
        conn.close()

    # ==================== 🏆 توابع فصل ====================
    def save_season_winners(self, winners_list):
        """ذخیره لیست برندگان فصل (به ترتیب رتبه)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = time.time()
        for rank, p in enumerate(winners_list, 1):
            cursor.execute('''
                INSERT INTO season_winners
                (user_id, player_name, country, score, credit, defense,
                 attack_power, population, rank, ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p.get("user_id"), p.get("player_name"), p.get("country"),
                p.get("score", 0), p.get("credit", 0), p.get("defense", 0),
                p.get("attack_power", 0), p.get("population", 0), rank, now
            ))
        conn.commit()
        conn.close()
    
    def get_last_season_winners(self, limit=10):
        """دریافت برندگان آخرین فصل"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, player_name, country, score, credit,
                   defense, attack_power, population, rank, ended_at
            FROM season_winners
            WHERE ended_at = (SELECT MAX(ended_at) FROM season_winners)
            ORDER BY rank ASC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_all_seasons_count(self):
        """تعداد کل فصل‌های انجام شده"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(DISTINCT ended_at) FROM season_winners')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def reset_all_players(self):
        """ریست کامل همه بازیکنان (برای پایان فصل)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM players')
        cursor.execute('DELETE FROM player_items')
        cursor.execute('DELETE FROM cabinet_codes')
        cursor.execute('DELETE FROM used_countries')
        cursor.execute('DELETE FROM unions')
        cursor.execute('DELETE FROM union_requests')
        cursor.execute('DELETE FROM bases')
        cursor.execute('DELETE FROM sanctions')
        cursor.execute('DELETE FROM assassination_info')
        cursor.execute('DELETE FROM assassination_cooldown')
        cursor.execute('DELETE FROM hack_cooldown')
        cursor.execute('DELETE FROM battle_logs')
        cursor.execute('DELETE FROM bot_messages')
        conn.commit()
        conn.close()
    
    def reset_game_config_for_new_season(self):
        """ریست تنظیمات بازی برای فصل جدید"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM game_config WHERE key IN "
                       "('war_active', 'war_start_time', "
                       "'war_end_time', 'last_profit_date', 'last_virus_damage_day', "
                       "'registration_closed', 'attack_limits')")
        cursor.execute("INSERT OR REPLACE INTO game_config (key, value) VALUES (?, ?)",
                       ("game_start_date", str(time.time())))
        conn.commit()
        conn.close()
    
    # ==================== 📝 توابع پیام‌های ربات ====================
    def save_bot_message(self, chat_id, message_id):
        """ذخیره message_id پیام ربات برای حذف بعدی"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bot_messages (chat_id, message_id, ts)
            VALUES (?, ?, ?)
        ''', (str(chat_id), message_id, time.time()))
        conn.commit()
        conn.close()
    
    def get_bot_messages(self, chat_id=None, limit=100):
        """دریافت پیام‌های ربات"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if chat_id:
            cursor.execute('''
                SELECT message_id FROM bot_messages 
                WHERE chat_id = ? 
                ORDER BY id DESC LIMIT ?
            ''', (str(chat_id), limit))
        else:
            cursor.execute('''
                SELECT chat_id, message_id FROM bot_messages 
                ORDER BY id DESC LIMIT ?
            ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def clear_bot_messages(self):
        """پاک کردن جدول پیام‌های ربات"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM bot_messages')
        conn.commit()
        conn.close()