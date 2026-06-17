#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════╗
║                    🎌 ANIMEBUM BOT 🎌                        ║
║                  To'liq O'zbek Tilida                        ║
║                  Barcha funksiyalar bilan                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
import sqlite3
import time
import json
import io
import os
import threading
from datetime import datetime, timedelta
from typing import Optional

from flask import Flask

import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ╔══════════════════════════════════════════════════════════════╗
# ║                    ⚙️ BOT SOZLAMALARI                        ║
# ╚══════════════════════════════════════════════════════════════╝

BOT_TOKEN = "8746287840:AAEjaeBqz89607bs0_W34DeFGvjLx13B9RY"
ADMIN_IDS = [6998664132]

BOT_USERNAME = "animebum_bot"
BACKUP_CHAT_ID = "@animebumhotira"  # Backup kanal - bu o'zgarmaydi!

# ╔══════════════════════════════════════════════════════════════╗
# ║                    🎭 JANRLAR RO'YXATI                       ║
# ╚══════════════════════════════════════════════════════════════╝

GENRES = [
    "Sport", "O'zga dunya", "Jangari", "Kundalik hayot",
    "Garem", "Etti", "Mexa", "Komediya",
    "Fantaziya", "Drama", "Sarguzasht", "Fantastika",
    "Romantika", "Maktab"
]

# ╔══════════════════════════════════════════════════════════════╗
# ║                   📊 LOG SOZLAMALARI                         ║
# ╚══════════════════════════════════════════════════════════════╝

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ╔══════════════════════════════════════════════════════════════╗
# ║                   🤖 BOT YARATISH                            ║
# ╚══════════════════════════════════════════════════════════════╝

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', num_threads=8)

# ╔══════════════════════════════════════════════════════════════╗
# ║              🌐 KEEP-ALIVE SERVER (UptimeRobot uchun)        ║
# ╚══════════════════════════════════════════════════════════════╝

_flask_app = Flask(__name__)

@_flask_app.route('/')
def home():
    return '🤖 AnimeBum Bot ishlayapti!', 200

@_flask_app.route('/health')
def health():
    return {'status': 'ok', 'bot': 'AnimeBum'}, 200

def run_keep_alive():
    port = int(os.environ.get('PORT', os.environ.get('KEEP_ALIVE_PORT', 8000)))
    _flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ╔══════════════════════════════════════════════════════════════╗
# ║               🗄️ MA'LUMOTLAR BAZASI                          ║
# ╚══════════════════════════════════════════════════════════════╝

def create_database():
    """Ma'lumotlar bazasini yaratish va jadvallarni sozlash"""
    conn = sqlite3.connect('kino_bot.db', timeout=30, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode=WAL')
    cursor.execute('PRAGMA synchronous=NORMAL')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            status TEXT DEFAULT 'user',
            status_expires_at TEXT,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referral_count INTEGER DEFAULT 0,
            bonus_points INTEGER DEFAULT 0,
            last_bonus_date TEXT,
            spam_count INTEGER DEFAULT 0,
            last_spam_time REAL DEFAULT 0,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    try:
        cursor.execute('ALTER TABLE users ADD COLUMN status_expires_at TEXT')
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            file_id TEXT NOT NULL DEFAULT '',
            file_type TEXT DEFAULT 'video',
            category TEXT DEFAULT 'Umumiy',
            is_series INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            rating_sum INTEGER DEFAULT 0,
            rating_count INTEGER DEFAULT 0,
            added_by INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    try:
        cursor.execute('ALTER TABLE movies ADD COLUMN is_series INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE movies ADD COLUMN file_id TEXT NOT NULL DEFAULT ""')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE movies ADD COLUMN is_ongoing INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE movies ADD COLUMN poster_file_id TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass

    # Qo'shimcha adminlar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extra_admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Serial qismlari jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS series_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            episode_num INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            file_type TEXT DEFAULT 'video',
            UNIQUE(code, episode_num)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_code TEXT NOT NULL,
            rating INTEGER NOT NULL,
            rated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, movie_code)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_code TEXT NOT NULL,
            action TEXT NOT NULL,
            action_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE NOT NULL,
            channel_name TEXT NOT NULL,
            channel_url TEXT NOT NULL,
            added_by INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ╔══════════════════════════════════════════════════════════════╗
# ║              💾 SOZLAMALAR                                    ║
# ╚══════════════════════════════════════════════════════════════╝

def get_setting(key: str, default: str = None) -> Optional[str]:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        cursor.execute('SELECT value FROM settings WHERE key=?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        conn.close()
        return default

def set_setting(key: str, value: str):
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)', (key, value))
    conn.commit()
    conn.close()

# ╔══════════════════════════════════════════════════════════════╗
# ║              🔄 BACKUP / RESTORE                             ║
# ╚══════════════════════════════════════════════════════════════╝

def backup_data():
    """Barcha ma'lumotlarni Telegram kanalga saqlash"""
    backup_chat = get_setting('backup_chat_id') or BACKUP_CHAT_ID
    if not backup_chat:
        return False
    try:
        conn = sqlite3.connect('kino_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT code, title, description, file_id, file_type, category, is_series, added_by FROM movies')
        movies = [dict(zip(['code','title','description','file_id','file_type','category','is_series','added_by'], r)) for r in cursor.fetchall()]
        cursor.execute('SELECT code, episode_num, file_id, file_type FROM series_episodes')
        episodes = [dict(zip(['code','episode_num','file_id','file_type'], r)) for r in cursor.fetchall()]
        cursor.execute('SELECT channel_id, channel_name, channel_url FROM channels')
        channels = [dict(zip(['channel_id','channel_name','channel_url'], r)) for r in cursor.fetchall()]
        conn.close()

        data_json = json.dumps({'movies': movies, 'episodes': episodes, 'channels': channels}, ensure_ascii=False, indent=2)
        file_obj = io.BytesIO(data_json.encode('utf-8'))
        file_obj.name = 'kino_bot_backup.json'

        msg = bot.send_document(
            backup_chat,
            file_obj,
            caption='#BACKUP_KINO_BOT\nAvtomatik zaxira nusxa'
        )
        try:
            bot.pin_chat_message(backup_chat, msg.message_id, disable_notification=True)
        except Exception:
            pass
        logger.info("✅ Backup saqlandi!")
        return True
    except Exception as e:
        logger.error(f"❌ Backup xatosi: {e}")
        return False

def restore_data():
    """Telegram kanaldagi pinned xabardan ma'lumotlarni tiklash"""
    backup_chat = get_setting('backup_chat_id') or BACKUP_CHAT_ID
    if not backup_chat:
        return False
    try:
        chat = bot.get_chat(backup_chat)
        pinned = chat.pinned_message
        if not pinned or not pinned.document:
            logger.info("ℹ️ Backup topilmadi.")
            return False

        file_info = bot.get_file(pinned.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        data = json.loads(downloaded.decode('utf-8'))

        conn = sqlite3.connect('kino_bot.db')
        cursor = conn.cursor()
        restored_movies = 0
        restored_eps = 0

        for m in data.get('movies', []):
            try:
                cursor.execute('''INSERT OR IGNORE INTO movies
                    (code, title, description, file_id, file_type, category, is_series, added_by)
                    VALUES (?,?,?,?,?,?,?,?)''',
                    (m['code'], m['title'], m.get('description',''), m.get('file_id',''),
                     m.get('file_type','video'), m.get('category','Umumiy'),
                     m.get('is_series',0), m.get('added_by',0)))
                restored_movies += cursor.rowcount
            except Exception:
                pass

        for e in data.get('episodes', []):
            try:
                cursor.execute('INSERT OR IGNORE INTO series_episodes (code, episode_num, file_id, file_type) VALUES (?,?,?,?)',
                               (e['code'], e['episode_num'], e['file_id'], e.get('file_type','video')))
                restored_eps += cursor.rowcount
            except Exception:
                pass

        for ch in data.get('channels', []):
            try:
                cursor.execute('INSERT OR IGNORE INTO channels (channel_id, channel_name, channel_url) VALUES (?,?,?)',
                               (ch['channel_id'], ch['channel_name'], ch['channel_url']))
            except Exception:
                pass

        conn.commit()
        conn.close()
        logger.info(f"✅ Restore: {restored_movies} kino, {restored_eps} qism tiklandi!")
        return True
    except Exception as e:
        logger.error(f"❌ Restore xatosi: {e}")
        return False

# ╔══════════════════════════════════════════════════════════════╗
# ║              📡 KANAL FUNKSIYALARI                            ║
# ╚══════════════════════════════════════════════════════════════╝

def get_channels() -> list:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id, channel_name, channel_url FROM channels')
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "url": r[2]} for r in rows]

def add_channel(channel_id: str, channel_name: str, channel_url: str, added_by: int) -> bool:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO channels (channel_id, channel_name, channel_url, added_by) VALUES (?, ?, ?, ?)',
            (channel_id, channel_name, channel_url, added_by)
        )
        conn.commit()
        logger.info(f"✅ Yangi kanal qo'shildi: {channel_id}")
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def remove_channel(channel_id: str) -> bool:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

# ╔══════════════════════════════════════════════════════════════╗
# ║               👤 FOYDALANUVCHI FUNKSIYALARI                  ║
# ╚══════════════════════════════════════════════════════════════╝

def get_user(user_id: int) -> Optional[dict]:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        columns = ['id', 'user_id', 'username', 'full_name', 'status', 'status_expires_at',
                   'referral_code', 'referred_by', 'referral_count', 'bonus_points',
                   'last_bonus_date', 'spam_count', 'last_spam_time', 'registered_at']
        return dict(zip(columns, row))
    return None

def register_user(user_id: int, username: str, full_name: str, referred_by: int = None) -> bool:
    import random, string
    referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (user_id, username, full_name, referral_code, referred_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, full_name, referral_code, referred_by))
        if referred_by:
            cursor.execute('''
                UPDATE users SET referral_count = referral_count + 1,
                bonus_points = bonus_points + 50 WHERE user_id = ?
            ''', (referred_by,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_user_status(user_id: int, status: str, days: int = 0) -> bool:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    expires_at = None
    if status == 'premium' and days > 0:
        expires_at = (datetime.now() + timedelta(days=days)).isoformat()
    cursor.execute(
        'UPDATE users SET status = ?, status_expires_at = ? WHERE user_id = ?',
        (status, expires_at, user_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_all_users() -> list:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_users_count() -> dict:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT status, COUNT(*) FROM users GROUP BY status')
    counts = dict(cursor.fetchall())
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    conn.close()
    counts['total'] = total
    return counts

def check_spam(user_id: int) -> bool:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT spam_count, last_spam_time FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    spam_count, last_spam_time = row
    current_time = time.time()
    if current_time - last_spam_time > 60:
        conn = sqlite3.connect('kino_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET spam_count = 1, last_spam_time = ? WHERE user_id = ?',
                       (current_time, user_id))
        conn.commit()
        conn.close()
        return False
    if spam_count >= 10:
        return True
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET spam_count = spam_count + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return False

# ╔══════════════════════════════════════════════════════════════╗
# ║                🎬 KINO FUNKSIYALARI                          ║
# ╚══════════════════════════════════════════════════════════════╝

def get_movie(code: str) -> Optional[dict]:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM movies WHERE code = ?', (code.strip(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        columns = ['id', 'code', 'title', 'description', 'file_id', 'file_type',
                   'category', 'is_series', 'views', 'rating_sum', 'rating_count',
                   'added_by', 'added_at', 'is_ongoing', 'poster_file_id']
        return dict(zip(columns, row[:len(columns)]))
    return None

def add_movie_db(code: str, title: str, description: str, file_id: str,
                 file_type: str, category: str, is_series: int, added_by: int) -> bool:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO movies (code, title, description, file_id, file_type,
                               category, is_series, added_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (code, title, description, file_id, file_type, category, is_series, added_by))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_movie(code: str) -> bool:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM series_episodes WHERE code = ?', (code,))
    cursor.execute('DELETE FROM movies WHERE code = ?', (code,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def increment_views(code: str):
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE movies SET views = views + 1 WHERE code = ?', (code,))
    conn.commit()
    conn.close()

def get_popular_movies(limit: int = 10) -> list:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT code, title, views, category FROM movies ORDER BY views DESC LIMIT ?', (limit,))
    movies = cursor.fetchall()
    conn.close()
    return movies

def get_latest_movies(limit: int = 10) -> list:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT code, title, added_at, category FROM movies ORDER BY added_at DESC LIMIT ?', (limit,))
    movies = cursor.fetchall()
    conn.close()
    return movies

def get_movies_by_category(category: str) -> list:
    """Janr bo'yicha qidirish — ko'p janrli kino/seriallarni ham topadi"""
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT code, title, views FROM movies WHERE category LIKE ?',
        (f'%{category}%',)
    )
    movies = cursor.fetchall()
    conn.close()
    return movies

def search_movies(query: str) -> list:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT code, title, category FROM movies WHERE title LIKE ? OR description LIKE ?',
                   (f'%{query}%', f'%{query}%'))
    movies = cursor.fetchall()
    conn.close()
    return movies

def get_all_categories() -> list:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category, COUNT(*) as cnt FROM movies GROUP BY category')
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_genre_movie_count(genre: str) -> int:
    """Berilgan janrga tegishli kino/serial sonini hisoblash"""
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM movies WHERE category LIKE ?', (f'%{genre}%',))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def rate_movie(user_id: int, movie_code: str, rating: int) -> str:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO ratings (user_id, movie_code, rating) VALUES (?, ?, ?)',
                       (user_id, movie_code, rating))
        cursor.execute('UPDATE movies SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE code = ?',
                       (rating, movie_code))
        conn.commit()
        return "added"
    except sqlite3.IntegrityError:
        cursor.execute('SELECT rating FROM ratings WHERE user_id = ? AND movie_code = ?',
                       (user_id, movie_code))
        old_rating = cursor.fetchone()[0]
        cursor.execute('UPDATE ratings SET rating = ? WHERE user_id = ? AND movie_code = ?',
                       (rating, user_id, movie_code))
        cursor.execute('UPDATE movies SET rating_sum = rating_sum - ? + ? WHERE code = ?',
                       (old_rating, rating, movie_code))
        conn.commit()
        return "updated"
    finally:
        conn.close()

# ╔══════════════════════════════════════════════════════════════╗
# ║              📺 SERIAL FUNKSIYALARI                           ║
# ╚══════════════════════════════════════════════════════════════╝

def add_series_episode(code: str, episode_num: int, file_id: str, file_type: str = 'video') -> bool:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO series_episodes (code, episode_num, file_id, file_type)
            VALUES (?, ?, ?, ?)
        ''', (code, episode_num, file_id, file_type))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_series_episodes(code: str) -> list:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT episode_num, file_id, file_type FROM series_episodes WHERE code = ? ORDER BY episode_num', (code,))
    rows = cursor.fetchall()
    conn.close()
    return [{'episode_num': r[0], 'file_id': r[1], 'file_type': r[2]} for r in rows]

def get_series_episode(code: str, episode_num: int) -> Optional[dict]:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT episode_num, file_id, file_type FROM series_episodes WHERE code = ? AND episode_num = ?',
                   (code, episode_num))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'episode_num': row[0], 'file_id': row[1], 'file_type': row[2]}
    return None

def set_movie_poster(code: str, file_id: str):
    conn = sqlite3.connect('kino_bot.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('UPDATE movies SET poster_file_id = ? WHERE code = ?', (file_id, code))
    conn.commit()
    conn.close()

def set_movie_ongoing(code: str, is_ongoing: int):
    conn = sqlite3.connect('kino_bot.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('UPDATE movies SET is_ongoing = ? WHERE code = ?', (is_ongoing, code))
    conn.commit()
    conn.close()

def notify_ongoing_new_episode(code: str, title: str, episode_num: int, total: int):
    """Yangi qism chiqqanini barcha foydalanuvchilarga xabar berish (fon oqimida)"""
    import threading
    def _send():
        users = get_all_users()
        deep_link = f"https://t.me/{BOT_USERNAME}?start=movie_{code}"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("▶️ Ko'rish", url=deep_link))
        text = (
            f"🔔 <b>Yangi qism chiqdi!</b>\n\n"
            f"📺 <b>{title}</b>\n"
            f"▶️ <b>{episode_num}-qism</b> qo'shildi!\n"
            f"🎞 Jami: <b>{total} qism</b>\n\n"
            f"👇 Ko'rish uchun bosing!"
        )
        for uid in users:
            try:
                bot.send_message(uid, text, reply_markup=kb)
                time.sleep(0.05)
            except Exception:
                pass
    t = threading.Thread(target=_send, daemon=True)
    t.start()

def get_series_episodes_count(code: str) -> int:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM series_episodes WHERE code = ?', (code,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ╔══════════════════════════════════════════════════════════════╗
# ║              🏆 BONUS FUNKSIYALARI                           ║
# ╚══════════════════════════════════════════════════════════════╝

def claim_daily_bonus(user_id: int) -> tuple:
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_bonus_date, bonus_points FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False, 0, "Foydalanuvchi topilmadi"
    last_bonus_date, current_points = row
    today = datetime.now().strftime('%Y-%m-%d')
    if last_bonus_date == today:
        next_bonus = datetime.now().replace(hour=0, minute=0, second=0) + timedelta(days=1)
        time_left = next_bonus - datetime.now()
        hours = int(time_left.seconds / 3600)
        minutes = int((time_left.seconds % 3600) / 60)
        return False, current_points, f"{hours} soat {minutes} daqiqadan so'ng"
    bonus = 100
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET bonus_points = bonus_points + ?, last_bonus_date = ? WHERE user_id = ?',
                   (bonus, today, user_id))
    conn.commit()
    conn.close()
    return True, current_points + bonus, str(bonus)

# ╔══════════════════════════════════════════════════════════════╗
# ║              ✅ OBUNA TEKSHIRISH                              ║
# ╚══════════════════════════════════════════════════════════════╝

def check_subscription(user_id: int) -> tuple:
    channels = get_channels()
    if not channels:
        return True, []
    not_subscribed = []
    for channel in channels:
        try:
            member = bot.get_chat_member(channel['id'], user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(channel)
        except Exception as e:
            logger.error(f"Kanal tekshirishda xato ({channel['id']}): {e}")
            not_subscribed.append(channel)
    return len(not_subscribed) == 0, not_subscribed

# ╔══════════════════════════════════════════════════════════════╗
# ║              🎨 KLAVIATURA FUNKSIYALARI                      ║
# ╚══════════════════════════════════════════════════════════════╝

def get_main_keyboard(user_status: str = 'user') -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("🎬 Anime Izlash"),
        KeyboardButton("🔍 Qidiruv")
    )
    keyboard.add(
        KeyboardButton("⭐ Mashhur Animlar"),
        KeyboardButton("🆕 Yangi Animlar")
    )
    keyboard.add(
        KeyboardButton("📂 Janrlar"),
        KeyboardButton("📞 Bog'lanish")
    )
    return keyboard

def user_id_is_admin_check(status: str) -> bool:
    return False

def get_main_keyboard_for_user(user_id: int, user_status: str = 'user') -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("🎬 Anime Izlash"),
        KeyboardButton("🔍 Qidiruv")
    )
    keyboard.add(
        KeyboardButton("⭐ Mashhur Animlar"),
        KeyboardButton("🆕 Yangi Animlar")
    )
    keyboard.add(
        KeyboardButton("📂 Janrlar"),
        KeyboardButton("📞 Bog'lanish")
    )
    if is_admin(user_id):
        keyboard.add(KeyboardButton("⚙️ Admin Panel"))
    return keyboard

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("➕ Anime Qo'shish"),
        KeyboardButton("🗑️ Anime O'chirish")
    )
    keyboard.add(
        KeyboardButton("➕ Qism Qo'shish"),
        KeyboardButton("📢 Kanalga Post")
    )
    keyboard.add(
        KeyboardButton("📊 Statistika"),
        KeyboardButton("👥 Foydalanuvchilar")
    )
    keyboard.add(
        KeyboardButton("📡 Kanal Sozlash"),
        KeyboardButton("📣 Broadcast")
    )
    keyboard.add(
        KeyboardButton("✏️ Start Matni"),
        KeyboardButton("✏️ Bog'lanish Matni")
    )
    keyboard.add(
        KeyboardButton("🔄 Ongoing Boshqarish"),
        KeyboardButton("💾 Backup")
    )
    keyboard.add(
        KeyboardButton("👥 Adminlar"),
        KeyboardButton("🔙 Orqaga")
    )
    return keyboard

def get_subscription_keyboard(channels: list) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    for channel in channels:
        keyboard.add(InlineKeyboardButton(
            f"📢 {channel['name']}",
            url=channel['url']
        ))
    keyboard.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription"))
    return keyboard

def get_rating_keyboard(movie_code: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = [
        InlineKeyboardButton(f"{'⭐' * i}", callback_data=f"rate_{movie_code}_{i}")
        for i in range(1, 6)
    ]
    keyboard.add(*buttons)
    return keyboard

EPISODES_PER_PAGE = 12

def get_episodes_keyboard(code: str, total_episodes: int, viewer_id: int = None, page: int = 0) -> InlineKeyboardMarkup:
    """Serial qismlari uchun inline tugmalar — sahifalash bilan (har sahifada 12 ta).
    Admin bo'lsa — keyingi qismni tezkor qo'shish tugmasi ham ko'rinadi."""
    keyboard = InlineKeyboardMarkup(row_width=4)
    start = page * EPISODES_PER_PAGE + 1
    end = min(start + EPISODES_PER_PAGE - 1, total_episodes)

    buttons = []
    for i in range(start, end + 1):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f"ep_{code}_{i}"))
    if buttons:
        keyboard.add(*buttons)

    # Sahifalash tugmalari
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Ortga", callback_data=f"epg_{code}_{page - 1}"))
    if end < total_episodes:
        nav.append(InlineKeyboardButton(f"Keyingisi ▶️", callback_data=f"epg_{code}_{page + 1}"))
    if nav:
        keyboard.add(*nav)

    # Admin uchun keyingi qismni tezkor qo'shish tugmasi
    if viewer_id and viewer_id in ADMIN_IDS:
        next_ep = total_episodes + 1
        keyboard.add(InlineKeyboardButton(
            f"➕ {next_ep}-qism qo'shish",
            callback_data=f"admin_quickadd_{code}"
        ))
    return keyboard

def show_channels_menu(user_id: int):
    channels = get_channels()
    keyboard = InlineKeyboardMarkup(row_width=1)
    if not channels:
        text = (
            "📡 <b>MAJBURIY KANALLAR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "ℹ️ Hozircha hech qanday kanal qo'shilmagan.\n\n"
            "➕ <b>Yangi kanal qo'shish</b> tugmasini bosing:"
        )
    else:
        text = "📡 <b>MAJBURIY KANALLAR</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch['name']}\n   🆔 <code>{ch['id']}</code>\n   🔗 {ch['url']}\n\n"
            keyboard.add(InlineKeyboardButton(
                f"🗑️ O'chirish: {ch['name']}",
                callback_data=f"chremove_{ch['id']}"
            ))
    keyboard.add(InlineKeyboardButton("➕ Yangi Kanal Qo'shish", callback_data="chadd_start"))
    bot.send_message(user_id, text, reply_markup=keyboard)

def get_category_keyboard() -> InlineKeyboardMarkup:
    """Barcha belgilangan janrlarni ko'rsatadi, har birida mavjud kino soni bilan"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for genre in GENRES:
        count = get_genre_movie_count(genre)
        label = f"{genre} ({count})" if count > 0 else genre
        buttons.append(InlineKeyboardButton(label, callback_data=f"category_{genre}"))
    keyboard.add(*buttons)
    return keyboard

# ╔══════════════════════════════════════════════════════════════╗
# ║              🎭 KO'P JANR TANLASH YORDAMCHI FUNKSIYA         ║
# ╚══════════════════════════════════════════════════════════════╝

# Har bir admin uchun tanlangan janrlar ro'yxatini saqlash
genre_selections = {}

def build_genre_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Janr tanlash klaviaturasini yaratadi. Tanlangan janrlar ✅ bilan belgilanadi."""
    selected = genre_selections.get(user_id, [])
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for genre in GENRES:
        mark = "✅ " if genre in selected else ""
        buttons.append(InlineKeyboardButton(
            f"{mark}{genre}",
            callback_data=f"admin_cat_{genre}"
        ))
    keyboard.add(*buttons)
    # Tayyor tugmasi
    selected_text = f"Tanlangan: {len(selected)} ta" if selected else "Hali tanlanmagan"
    keyboard.add(InlineKeyboardButton(
        f"✅ Tayyor ({selected_text})",
        callback_data="admin_genre_done"
    ))
    return keyboard

# ╔══════════════════════════════════════════════════════════════╗
# ║              📨 XABAR YUBORISH FUNKSIYALARI                   ║
# ╚══════════════════════════════════════════════════════════════╝

def send_movie(chat_id: int, movie: dict, user_status: str = 'user'):
    """Kino yoki serial yuborish"""

    rating = 0
    if movie['rating_count'] > 0:
        rating = movie['rating_sum'] / movie['rating_count']
    stars = '⭐' * round(rating) if rating > 0 else '❌ Baholanmagan'
    rating_keyboard = get_rating_keyboard(movie['code'])

    # ── SERIAL ──────────────────────────────────────────────────
    if movie.get('is_series'):
        episodes = get_series_episodes(movie['code'])
        total = len(episodes)

        if not episodes:
            bot.send_message(chat_id, "❌ Bu serial uchun qismlar hali qo'shilmagan.")
            return

        ongoing_badge = " 🔄" if movie.get('is_ongoing') else ""
        ongoing_line = "🔄 <b>Holati:</b> Davom etmoqda\n" if movie.get('is_ongoing') else ""
        poster_id = movie.get('poster_file_id') or ''

        caption = (
            f"📺 <b>{movie['title']}{ongoing_badge}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Tavsif:</b> {movie['description'] or 'Mavjud emas'}\n"
            f"📂 <b>Kategoriya:</b> {movie['category']}\n"
            f"🔢 <b>Kod:</b> <code>{movie['code']}</code>\n"
            f"🎞 <b>Jami qismlar:</b> {total} qism\n"
            f"{ongoing_line}"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📺 Quyidagi raqamlardan kerakli qismni tanlang:"
        )

        ep_keyboard = get_episodes_keyboard(movie['code'], total, viewer_id=chat_id, page=0)

        try:
            if poster_id:
                bot.send_photo(chat_id, photo=poster_id, caption=caption,
                               reply_markup=ep_keyboard, protect_content=True)
            else:
                ep1 = episodes[0]
                if ep1['file_type'] == 'video':
                    bot.send_video(chat_id, video=ep1['file_id'], caption=caption,
                                   reply_markup=ep_keyboard, protect_content=True)
                elif ep1['file_type'] == 'document':
                    bot.send_document(chat_id, document=ep1['file_id'], caption=caption,
                                      reply_markup=ep_keyboard, protect_content=True)
                else:
                    bot.send_message(chat_id, caption, reply_markup=ep_keyboard)

            increment_views(movie['code'])
            logger.info(f"✅ Serial yuborildi: [{movie['code']}] {movie['title']} -> {chat_id}")
        except Exception as e:
            logger.error(f"❌ Serial yuborishda xato: {e}")
            bot.send_message(chat_id, "❌ Serialni yuborishda xatolik yuz berdi.")
        return

    # ── KINO ────────────────────────────────────────────────────
    caption = (
        f"🎬 <b>{movie['title']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Tavsif:</b> {movie['description'] or 'Mavjud emas'}\n"
        f"📂 <b>Kategoriya:</b> {movie['category']}\n"
        f"🔢 <b>Kod:</b> <code>{movie['code']}</code>\n"
        f"👁️ <b>Ko'rishlar:</b> {movie['views']}\n"
        f"⭐ <b>Reyting:</b> {stars} ({rating:.1f}/5.0)\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

    try:
        if movie['file_type'] == 'video':
            bot.send_video(chat_id, video=movie['file_id'], caption=caption, reply_markup=rating_keyboard, protect_content=True)
        elif movie['file_type'] == 'document':
            bot.send_document(chat_id, document=movie['file_id'], caption=caption, reply_markup=rating_keyboard, protect_content=True)
        elif movie['file_type'] == 'photo':
            bot.send_photo(chat_id, photo=movie['file_id'], caption=caption, reply_markup=rating_keyboard, protect_content=True)
        else:
            bot.send_message(chat_id, caption, reply_markup=rating_keyboard)

        increment_views(movie['code'])
        logger.info(f"✅ Kino yuborildi: [{movie['code']}] {movie['title']} -> {chat_id}")
    except Exception as e:
        logger.error(f"❌ Kino yuborishda xato: {e}")
        bot.send_message(chat_id, "❌ Kinoni yuborishda xatolik yuz berdi.")

def send_series_episode(chat_id: int, movie: dict, episode_num: int):
    """Serial ma'lum bir qismini yuborish"""
    episodes = get_series_episodes(movie['code'])
    total = len(episodes)

    ep = get_series_episode(movie['code'], episode_num)
    if not ep:
        bot.send_message(chat_id, f"❌ {episode_num}-qism topilmadi!")
        return

    caption = (
        f"📺 <b>{movie['title']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"▶️ <b>{episode_num}-qism</b> / Jami: {total} qism\n"
        f"🔢 <b>Kod:</b> <code>{movie['code']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 Boshqa qismni tanlang:"
    )

    ep_keyboard = get_episodes_keyboard(movie['code'], total, viewer_id=chat_id, page=(episode_num - 1) // EPISODES_PER_PAGE)

    try:
        if ep['file_type'] == 'video':
            bot.send_video(chat_id, video=ep['file_id'], caption=caption, reply_markup=ep_keyboard, protect_content=True)
        elif ep['file_type'] == 'document':
            bot.send_document(chat_id, document=ep['file_id'], caption=caption, reply_markup=ep_keyboard, protect_content=True)
        else:
            bot.send_message(chat_id, caption, reply_markup=ep_keyboard)
        logger.info(f"✅ Serial qism yuborildi: [{movie['code']}] {episode_num}-qism -> {chat_id}")
    except Exception as e:
        logger.error(f"❌ Serial qism yuborishda xato: {e}")
        bot.send_message(chat_id, "❌ Qismni yuborishda xatolik yuz berdi.")

# ╔══════════════════════════════════════════════════════════════╗
# ║              🎮 HOLATLAR BOSHQARISH (STATE)                   ║
# ╚══════════════════════════════════════════════════════════════╝

user_states = {}

def set_state(user_id: int, state: str, data: dict = None):
    user_states[user_id] = {'state': state, 'data': data or {}}

def get_state(user_id: int) -> dict:
    return user_states.get(user_id, {})

def clear_state(user_id: int):
    user_states.pop(user_id, None)

# ╔══════════════════════════════════════════════════════════════╗
# ║                  📩 KOMANDALAR                               ║
# ╚══════════════════════════════════════════════════════════════╝

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username or ''
    full_name = message.from_user.full_name or 'Anonim'

    # Deep link parametrini ajratib olish
    deep_link_code = None
    referred_by = None
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.startswith('ref_'):
            try:
                referred_by = int(param.replace('ref_', ''))
                if referred_by == user_id:
                    referred_by = None
            except ValueError:
                pass
        elif param.startswith('movie_'):
            deep_link_code = param.replace('movie_', '')
        else:
            # Oddiy kod ham bo'lishi mumkin (masalan: start=101)
            deep_link_code = param

    user = get_user(user_id)
    if not user:
        register_user(user_id, username, full_name, referred_by)
        user = get_user(user_id)
        if referred_by:
            try:
                bot.send_message(
                    referred_by,
                    f"🎉 <b>Yangi referal!</b>\n"
                    f"👤 {full_name} sizning havolangiz orqali ro'yxatdan o'tdi!\n"
                    f"💰 +50 bonus ball qo'shildi!"
                )
            except Exception:
                pass

    is_subscribed, not_subscribed = check_subscription(user_id)
    if not is_subscribed:
        keyboard = get_subscription_keyboard(not_subscribed)
        # Deep link bo'lsa obuna tekshirilgandan keyin shu kinoni yuborsin
        if deep_link_code:
            set_state(user_id, 'pending_movie', {'code': deep_link_code})
        bot.send_message(
            user_id,
            f"👋 Salom, <b>{full_name}</b>!\n\n"
            f"🎌 <b>ANIMEBUM</b>ga xush kelibsiz!\n\n"
            f"⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz shart:\n\n"
            + "\n".join([f"➡️ {ch['name']}" for ch in not_subscribed]) +
            f"\n\n✅ Obuna bo'lgandan so'ng <b>Tekshirish</b> tugmasini bosing.",
            reply_markup=keyboard
        )
        return

    user_status = user.get('status', 'user')
    keyboard = get_main_keyboard_for_user(user_id, user_status)

    # Deep link orqali kelgan bo'lsa — to'g'ridan kino yubor
    if deep_link_code:
        movie = get_movie(deep_link_code)
        if movie:
            bot.send_message(
                user_id,
                f"👋 Xush kelibsiz, <b>{full_name}</b>! 🎬",
                reply_markup=keyboard
            )
            send_movie(user_id, movie, user_status)
            return
        else:
            bot.send_message(
                user_id,
                f"❌ <code>{deep_link_code}</code> kodli kino topilmadi.",
                reply_markup=keyboard
            )
            return

    default_start = (
        "🎌 <b>ANIMEBUM BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Xush kelibsiz, {name}!\n\n"
        "🎬 Eng sara kinolar, seriallar va anime olami!\n\n"
        "📺 Yangi filmlar va seriallar\n"
        "🎭 Eng qiziqarli anime to'plamlari\n"
        "🤖 Maxsus bot orqali qulay foydalanish\n\n"
        "Kanalga obuna bo'ling va eng yaxshi kontentni birinchi bo'lib tomosha qiling!\n"
        "📢 Kanal: t.me/animebum_1\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎌 <b>Anime kodini kiriting!</b>"
    )
    start_template = get_setting('start_text') or default_start
    welcome_text = start_template.replace('{name}', f'<b>{full_name}</b>')

    bot.send_message(user_id, welcome_text, reply_markup=keyboard)

@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = (
        f"❓ <b>BOT HAQIDA YORDAM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎬 <b>Kino olish:</b>\n"
        f"Kino kodini yozing (masalan: <code>101</code>)\n\n"
        f"📺 <b>Serial olish:</b>\n"
        f"Serial kodini yozing → 1-qism + barcha qismlar tugmalari chiqadi.\n"
        f"Kerakli qism raqamini bosing!\n\n"
        f"🔍 <b>Qidiruv:</b>\n"
        f"Kino nomini yozing yoki /search buyrug'ini ishlating\n\n"
        f"⭐ <b>Mashhur kinolar:</b>\n"
        f"<code>Mashhur Kinolar</code> tugmasini bosing\n\n"
        f"🎁 <b>Kunlik Bonus:</b>\n"
        f"Har kuni 100 ball olasiz!\n\n"
        f"👥 <b>Referal:</b>\n"
        f"Havolangizni ulashing va har bir do'stingiz uchun 50 ball oling!\n\n"
        f"📩 Savol va takliflar uchun: /contact"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['profile'])
def profile_handler(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(user_id, "❌ Siz hali ro'yxatdan o'tmagansiz. /start bosing.")
        return

    status_emoji = {'user': '👤', 'premium': '💎', 'admin': '👑'}.get(user['status'], '👤')
    status_name = {'user': 'Standard', 'premium': 'Premium', 'admin': 'Admin'}.get(user['status'], 'Standard')

    profile_text = (
        f"👤 <b>PROFILIM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>ID:</b> <code>{user['user_id']}</code>\n"
        f"👤 <b>Ism:</b> {user['full_name']}\n"
        f"📱 <b>Username:</b> @{user['username'] or 'Mavjud emas'}\n"
        f"{status_emoji} <b>Status:</b> {status_name}\n"
        f"💰 <b>Bonus ball:</b> {user['bonus_points']}\n"
        f"👥 <b>Referallar:</b> {user['referral_count']} kishi\n"
        f"📅 <b>Ro'yxatdan:</b> {user['registered_at'][:10]}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Referal havola:</b>\n"
        f"<code>https://t.me/{BOT_USERNAME}?start=ref_{user['user_id']}</code>"
    )

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎁 Kunlik Bonus", callback_data="daily_bonus"))
    keyboard.add(InlineKeyboardButton("👥 Referal Tizim", callback_data="referral_info"))
    bot.send_message(user_id, profile_text, reply_markup=keyboard)

@bot.message_handler(commands=['bonus'])
def bonus_command(message):
    user_id = message.from_user.id
    success, points, info = claim_daily_bonus(user_id)
    if success:
        bot.send_message(
            user_id,
            f"🎁 <b>Kunlik Bonus!</b>\n\n✅ Siz {info} ball oldingiz!\n💰 Jami ballingiz: <b>{points}</b>\n\n⏰ Ertaga yana qaytib keling!"
        )
    else:
        bot.send_message(
            user_id,
            f"⏰ <b>Kunlik Bonus</b>\n\n❌ Siz bugun allaqachon bonus oldingiz!\n⏳ Keyingi bonus: <b>{info}</b>\n💰 Hozirgi ballingiz: <b>{points}</b>"
        )

@bot.message_handler(commands=['referral'])
def referral_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(user_id, "❌ /start bosing.")
        return
    referral_text = (
        f"👥 <b>REFERAL TIZIM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 Har bir ro'yxatdan o'tgan do'stingiz uchun <b>50 ball</b> olasiz!\n\n"
        f"📊 <b>Sizning statistikangiz:</b>\n"
        f"👤 Jami referallar: <b>{user['referral_count']}</b> kishi\n"
        f"💰 Referal bonus: <b>{user['referral_count'] * 50}</b> ball\n\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>https://t.me/{BOT_USERNAME}?start=ref_{user['user_id']}</code>"
    )
    bot.send_message(user_id, referral_text)

@bot.message_handler(commands=['search'])
def search_command(message):
    user_id = message.from_user.id
    if len(message.text.split()) > 1:
        query = ' '.join(message.text.split()[1:])
        do_search(user_id, query)
    else:
        set_state(user_id, 'searching')
        bot.send_message(
            user_id,
            "🔍 <b>Kino Qidirish</b>\n\nQidirmoqchi bo'lgan kino nomini yozing:",
            reply_markup=types.ForceReply()
        )

def do_search(user_id: int, query: str):
    results = search_movies(query)
    if not results:
        bot.send_message(
            user_id,
            f"🔍 '<b>{query}</b>' bo'yicha hech narsa topilmadi.\n\n💡 Boshqa kalit so'z bilan urinib ko'ring."
        )
        return
    text = f"🔍 '<b>{query}</b>' bo'yicha natijalar:\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    keyboard = InlineKeyboardMarkup(row_width=2)
    for i, movie in enumerate(results[:10], 1):
        code, title, category = movie
        text += f"{i}. 🎬 <b>{title}</b>\n   📂 {category} | 🔢 Kod: <code>{code}</code>\n\n"
        label = f"🎬 {title[:25]}..." if len(title) > 25 else f"🎬 {title}"
        keyboard.add(InlineKeyboardButton(label, callback_data=f"get_movie_{code}"))
    bot.send_message(user_id, text, reply_markup=keyboard)

# ╔══════════════════════════════════════════════════════════════╗
# ║               👑 ADMIN KOMANDALAR                            ║
# ╚══════════════════════════════════════════════════════════════╝

def get_extra_admins() -> list:
    conn = sqlite3.connect('kino_bot.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, full_name, added_at FROM extra_admins ORDER BY added_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [{'user_id': r[0], 'username': r[1], 'full_name': r[2], 'added_at': r[3]} for r in rows]

def add_extra_admin(user_id: int, username: str = '', full_name: str = '') -> bool:
    if user_id in ADMIN_IDS:
        return False
    conn = sqlite3.connect('kino_bot.db', timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT OR REPLACE INTO extra_admins (user_id, username, full_name) VALUES (?, ?, ?)',
                       (user_id, username or '', full_name or ''))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def remove_extra_admin(user_id: int) -> bool:
    conn = sqlite3.connect('kino_bot.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM extra_admins WHERE user_id = ?', (user_id,))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

def is_super_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def is_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    conn = sqlite3.connect('kino_bot.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM extra_admins WHERE user_id = ?', (user_id,))
    found = cursor.fetchone() is not None
    conn.close()
    return found

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    counts = get_users_count()
    admin_text = (
        f"👑 <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"👤 Jami foydalanuvchilar: <b>{counts.get('total', 0)}</b>\n"
        f"👤 Oddiy: <b>{counts.get('user', 0)}</b>\n\n"
        f"🎌 <b>Boshqarish:</b>\n"
        f"➕ Anime qo'shish: /addmovie\n"
        f"🗑️ Anime o'chirish: /deletemovie\n"
        f"➕ Qism qo'shish: /addepisode\n"
        f"📢 Kanalga post: /postchannel\n"
        f"📣 Broadcast: /broadcast\n"
        f"📡 Kanal sozlash: /setchannel\n"
        f"💾 Backup: /setbackup\n"
        f"✏️ Start matni: <b>Start Matni</b> tugmasi\n"
        f"✏️ Bog'lanish matni: <b>Bog'lanish Matni</b> tugmasi\n"
    )
    bot.send_message(user_id, admin_text, reply_markup=get_admin_keyboard())

@bot.message_handler(commands=['addmovie'])
def add_movie_command(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    set_state(user_id, 'add_movie_code')
    bot.send_message(
        user_id,
        "➕ <b>Yangi Anime / Serial Qo'shish</b>\n\n"
        "❗ Istalgan qadamda <b>orqaga</b> yozing — oldingi bosqichga qaytish\n"
        "❗ Ko'pchilik maydonlar uchun <b>skip</b> yozing — o'tkazib yuborish\n\n"
        "1️⃣ Kodini kiriting (masalan: <code>101</code>):",
        reply_markup=types.ForceReply()
    )

@bot.message_handler(commands=['deletemovie'])
def delete_movie_command(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    set_state(user_id, 'delete_movie')
    bot.send_message(
        user_id,
        "🗑️ <b>Kino / Serial O'chirish</b>\n\nO'chirmoqchi bo'lgan kodini kiriting:",
        reply_markup=types.ForceReply()
    )

@bot.message_handler(commands=['addepisode'])
def add_episode_command(message):
    """Mavjud serialga yangi qism qo'shish"""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    set_state(user_id, 'add_episode_code')
    bot.send_message(
        user_id,
        "➕ <b>Serialga Qism Qo'shish</b>\n\n"
        "Qaysi serial kodiga qism qo'shmoqchisiz?\n"
        "Kod yuboring (masalan: <code>101</code>):",
        reply_markup=types.ForceReply()
    )

@bot.message_handler(commands=['setbackup'])
def set_backup_command(message):
    """Backup kanalini sozlash"""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    current = get_setting('backup_chat_id', 'Belgilanmagan')
    set_state(user_id, 'set_backup_chat')
    bot.send_message(
        user_id,
        "💾 <b>Backup Kanal Sozlash</b>\n\n"
        f"Hozirgi kanal: <code>{current}</code>\n\n"
        "Backup saqlanadigan kanal/chat ID sini yuboring:\n"
        "Misol: <code>@mening_backup_kanal</code> yoki <code>-1001234567890</code>\n\n"
        "⚠️ Botni o'sha kanalga admin qilib qo'shing!",
        reply_markup=types.ForceReply()
    )

@bot.message_handler(commands=['postmovie', 'postchannel'])
def post_channel_command(message):
    """Kanalga bevosita rasm + YUKLAB OLISH tugmasi yuborish"""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return

    anime_ch = get_setting('post_channel_id')
    drama_ch = get_setting('post_channel_drama_id')

    if not anime_ch and not drama_ch:
        bot.send_message(
            user_id,
            "⚠️ Hali hech qanday post kanali sozlanmagan!\n\n"
            "/setpostchannel @animebum_1 — Anime kanali\n"
            "/setdramachannel @drama_kanal — Drama kanali"
        )
        return

    parts = message.text.split()
    code = parts[1].strip() if len(parts) >= 2 else None

    # Agar ikki kanal ham bor — avval qaysi kanalga so'ra
    if anime_ch and drama_ch:
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton(f"📺 Anime kanali ({anime_ch})", callback_data="postchan_anime"))
        kb.add(InlineKeyboardButton(f"🎭 Drama kanali ({drama_ch})", callback_data="postchan_drama"))
        if code:
            set_state(user_id, 'post_channel_select_pending', {'code': code})
        bot.send_message(user_id, "📢 <b>Qaysi kanalga post qilasiz?</b>", reply_markup=kb)
        return

    # Faqat bitta kanal bor — to'g'ri davom et
    post_ch = anime_ch or drama_ch
    label = "📺 Anime kanali" if anime_ch else "🎭 Drama kanali"

    if not code:
        set_state(user_id, 'post_channel_ask_code', {'channel': post_ch, 'channel_label': label})
        bot.send_message(user_id,
            f"📢 Kanal: {label} (<code>{post_ch}</code>)\n\n"
            f"Qaysi anime/serial kodini post qilmoqchisiz?\nKodini kiriting:")
        return

    movie = get_movie(code)
    if not movie:
        bot.send_message(user_id, f"❌ <code>{code}</code> kodli anime topilmadi!")
        return

    set_state(user_id, 'post_channel_photo', {'code': code, 'channel': post_ch})
    bot.send_message(
        user_id,
        f"🎌 <b>{movie['title']}</b>\n"
        f"📢 Kanal: {label}\n\n"
        f"📸 Post uchun <b>RASM</b> yuboring:\n"
        f"(yoki <code>skip</code> yozing — rasmsiz post yuborish)"
    )

@bot.message_handler(commands=['setpostchannel'])
def set_post_channel_command(message):
    """Post kanalini sozlash"""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        current = get_setting('post_channel_id', 'Belgilanmagan')
        bot.send_message(
            user_id,
            f"📢 <b>Post Kanali Sozlash</b>\n\n"
            f"Hozirgi kanal: <code>{current}</code>\n\n"
            f"Ishlatish: <code>/setpostchannel @animebum_1</code>\n"
            f"yoki: <code>/setpostchannel -1001234567890</code>\n\n"
            f"⚠️ Botni o'sha kanalga admin qilib qo'shing!"
        )
        return
    ch_id = parts[1].strip()
    set_setting('post_channel_id', ch_id)
    bot.send_message(
        user_id,
        f"✅ <b>Post kanali saqlandi!</b>\n\n"
        f"Kanal: <code>{ch_id}</code>\n\n"
        f"Endi /postchannel buyrug'i shu kanalga post yuboradi."
    )

@bot.message_handler(commands=['setdramachannel'])
def set_drama_channel_command(message):
    """Drama post kanalini sozlash"""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        current = get_setting('post_channel_drama_id', 'Belgilanmagan')
        bot.send_message(
            user_id,
            f"🎭 <b>Drama Post Kanali Sozlash</b>\n\n"
            f"Hozirgi drama kanali: <code>{current}</code>\n\n"
            f"Ishlatish: <code>/setdramachannel @drama_kanal</code>\n"
            f"yoki: <code>/setdramachannel -1001234567890</code>\n\n"
            f"⚠️ Botni o'sha kanalga admin qilib qo'shing!"
        )
        return
    ch_id = parts[1].strip()
    set_setting('post_channel_drama_id', ch_id)
    bot.send_message(
        user_id,
        f"✅ <b>Drama post kanali saqlandi!</b>\n\n"
        f"Kanal: <code>{ch_id}</code>\n\n"
        f"Endi drama postlari shu kanalga chiqadi."
    )

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    set_state(user_id, 'broadcast')
    bot.send_message(
        user_id,
        "📢 <b>Broadcast</b>\n\n"
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabarni yuboring.\n\n"
        "📝 Matn, 🖼 Rasm, 🎬 Video, 🎵 Audio, 📄 Hujjat — barchasi qabul qilinadi.",
        reply_markup=types.ForceReply()
    )

@bot.message_handler(commands=['setstatus'])
def set_status_command(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    parts = message.text.split()
    if len(parts) == 3:
        try:
            target_id = int(parts[1])
            new_status = parts[2].lower()
            if new_status not in ['user', 'premium', 'admin']:
                bot.send_message(user_id, "❌ Noto'g'ri status! (user/premium/admin)")
                return
            if update_user_status(target_id, new_status):
                bot.send_message(user_id, f"✅ Foydalanuvchi {target_id} statusiga <b>{new_status}</b> berildi!")
                try:
                    bot.send_message(target_id, f"🎉 <b>Tabriklaymiz!</b>\nSizga <b>{new_status}</b> statusi berildi!")
                except Exception:
                    pass
            else:
                bot.send_message(user_id, "❌ Foydalanuvchi topilmadi!")
        except ValueError:
            bot.send_message(user_id, "❌ Noto'g'ri format! /setstatus USER_ID STATUS")
    else:
        set_state(user_id, 'set_status_id')
        bot.send_message(
            user_id,
            "💎 <b>Status Berish</b>\n\nFormat: /setstatus USER_ID STATUS\nMasalan: /setstatus 123456789 premium\n\nYoki foydalanuvchi ID sini kiriting:",
            reply_markup=types.ForceReply()
        )

@bot.message_handler(commands=['stats'])
def stats_command(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sizda admin huquqlari yo'q!")
        return
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM movies WHERE is_series = 0")
    total_movies = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM movies WHERE is_series = 1")
    total_series = cursor.fetchone()[0]
    cursor.execute('SELECT SUM(views) FROM movies')
    total_views = cursor.fetchone()[0] or 0
    cursor.execute('SELECT code, title, views FROM movies ORDER BY views DESC LIMIT 3')
    top_movies = cursor.fetchall()
    conn.close()
    top_text = "\n".join([f"  {i+1}. {m[1]} - {m[2]} marta" for i, m in enumerate(top_movies)])
    stats_text = (
        f"📊 <b>BOT STATISTIKASI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Foydalanuvchilar:</b> <b>{total_users}</b>\n\n"
        f"🎬 <b>Kinolar:</b> <b>{total_movies}</b>\n"
        f"📺 <b>Seriallar:</b> <b>{total_series}</b>\n"
        f"👁️ <b>Jami ko'rishlar:</b> <b>{total_views}</b>\n\n"
        f"🏆 <b>Top 3:</b>\n{top_text or '  Hali korish yoq'}"
    )
    bot.send_message(user_id, stats_text)

# ╔══════════════════════════════════════════════════════════════╗
# ║            📨 XABAR HANDLERLARI (HOLATLAR)                   ║
# ╚══════════════════════════════════════════════════════════════╝

@bot.message_handler(content_types=['text'])
def text_handler(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if check_spam(user_id):
        bot.send_message(user_id, "⚠️ <b>Spam aniqlandi!</b>\n\nSiz juda ko'p xabar yubordingiz. Iltimos, 1 daqiqa kuting.")
        return

    is_subscribed, not_subscribed = check_subscription(user_id)
    if not is_subscribed:
        keyboard = get_subscription_keyboard(not_subscribed)
        bot.send_message(
            user_id,
            "⚠️ <b>Obuna bo'lmadingiz!</b>\n\n"
            "Botdan foydalanish uchun avval quyidagi kanallarga obuna bo'ling:",
            reply_markup=keyboard
        )
        return

    user = get_user(user_id)
    if not user:
        register_user(user_id, message.from_user.username or '', message.from_user.full_name or '')
        user = get_user(user_id)

    user_status = user.get('status', 'user')
    state = get_state(user_id)

    # ── HOLATLAR ─────────────────────────────────────────────────

    if state.get('state') == 'searching':
        clear_state(user_id)
        do_search(user_id, text)
        return

    if state.get('state') == 'broadcast' and is_admin(user_id):
        clear_state(user_id)
        do_broadcast(user_id, message)
        return

    if state.get('state') == 'delete_movie' and is_admin(user_id):
        clear_state(user_id)
        if delete_movie(text):
            bot.send_message(user_id, f"✅ <code>{text}</code> kodi o'chirildi!")
        else:
            bot.send_message(user_id, f"❌ <code>{text}</code> kodli kino/serial topilmadi!")
        return

    if state.get('state') == 'add_movie_code' and is_admin(user_id):
        if text.lower() in ('orqaga', 'bekor'):
            clear_state(user_id)
            bot.send_message(user_id, "❌ Bekor qilindi.", reply_markup=get_admin_keyboard())
            return
        if get_movie(text):
            bot.send_message(user_id, f"❌ <code>{text}</code> kodli anime allaqachon mavjud!\nBoshqa kod kiriting:")
            return
        set_state(user_id, 'add_movie_title', {'code': text})
        bot.send_message(user_id, f"✅ Kod: <code>{text}</code>\n\n2️⃣ Nomini kiriting:")
        return

    if state.get('state') == 'add_movie_title' and is_admin(user_id):
        if text.lower() in ('orqaga', 'bekor'):
            set_state(user_id, 'add_movie_code')
            bot.send_message(user_id, "⬅️ 1️⃣ Kodini qayta kiriting:")
            return
        data = state.get('data', {})
        data['title'] = text
        set_state(user_id, 'add_movie_description', data)
        bot.send_message(user_id, f"✅ Nom: <b>{text}</b>\n\n3️⃣ Tavsifini kiriting\n(<code>skip</code> — o'tkazib yuborish):")
        return

    if state.get('state') == 'add_movie_description' and is_admin(user_id):
        if text.lower() in ('orqaga', 'bekor'):
            data = state.get('data', {})
            set_state(user_id, 'add_movie_title', data)
            bot.send_message(user_id, f"⬅️ 2️⃣ Nomini qayta kiriting (hozirgi: <b>{data.get('title','')}</b>):")
            return
        data = state.get('data', {})
        data['description'] = '' if text.lower() == 'skip' else text
        set_state(user_id, 'add_movie_year', data)
        bot.send_message(
            user_id,
            f"4️⃣ Yilini kiriting (masalan: <code>2024</code>)\n(<code>skip</code> — o'tkazib yuborish):"
        )
        return

    if state.get('state') == 'add_movie_year' and is_admin(user_id):
        if text.lower() in ('orqaga', 'bekor'):
            data = state.get('data', {})
            set_state(user_id, 'add_movie_description', data)
            bot.send_message(user_id, "⬅️ 3️⃣ Tavsifini qayta kiriting (yoki <code>skip</code>):")
            return
        data = state.get('data', {})
        data['year'] = '' if text.lower() == 'skip' else text
        set_state(user_id, 'add_movie_lang', data)
        bot.send_message(
            user_id,
            f"5️⃣ Tilini kiriting (masalan: <code>O'zbek tilida</code>)\n(<code>skip</code> — o'tkazib yuborish):"
        )
        return

    if state.get('state') == 'add_movie_lang' and is_admin(user_id):
        if text.lower() in ('orqaga', 'bekor'):
            data = state.get('data', {})
            set_state(user_id, 'add_movie_year', data)
            bot.send_message(user_id, "⬅️ 4️⃣ Yilini qayta kiriting (yoki <code>skip</code>):")
            return
        data = state.get('data', {})
        data['lang'] = '' if text.lower() == 'skip' else text
        set_state(user_id, 'add_movie_category', data)
        # Ko'p janr tanlash klaviaturasini ko'rsatish
        genre_selections[user_id] = []
        keyboard = build_genre_keyboard(user_id)
        bot.send_message(
            user_id,
            "6️⃣ <b>Janrlarni tanlang</b> (bir yoki bir nechta):\n\n"
            "✅ = tanlangan, yana bossangiz — bekor qilinadi.\n"
            "Tayyor bo'lganda <b>✅ Tayyor</b> tugmasini bosing:",
            reply_markup=keyboard
        )
        return

    if state.get('state') == 'add_episode_code' and is_admin(user_id):
        movie = get_movie(text)
        if not movie:
            bot.send_message(user_id, f"❌ <code>{text}</code> kodli serial topilmadi!")
            clear_state(user_id)
            return
        if not movie.get('is_series'):
            bot.send_message(user_id, f"❌ <code>{text}</code> kod — serial emas, oddiy kino!")
            clear_state(user_id)
            return
        existing = get_series_episodes_count(text)
        set_state(user_id, 'add_episode_num', {'code': text, 'title': movie['title'], 'existing': existing})
        bot.send_message(
            user_id,
            f"📺 <b>{movie['title']}</b>\n"
            f"Hozir: <b>{existing} qism</b> mavjud\n\n"
            f"Nechchi-qism qo'shmoqchisiz? Raqam yuboring:\n"
            f"Misol: <code>{existing + 1}</code>"
        )
        return

    if state.get('state') == 'add_episode_num' and is_admin(user_id):
        if not text.isdigit() or int(text) < 1:
            bot.send_message(user_id, "❌ To'g'ri raqam kiriting!")
            return
        ep_num = int(text)
        data = state.get('data', {})
        data['episode_num'] = ep_num
        set_state(user_id, 'add_episode_file', data)
        bot.send_message(
            user_id,
            f"✅ {ep_num}-qism uchun video faylni yuboring:"
        )
        return

    if state.get('state') == 'post_channel_ask_code' and is_admin(user_id):
        code = text.strip()
        movie = get_movie(code)
        if not movie:
            bot.send_message(user_id, f"❌ <code>{code}</code> kodli anime topilmadi!\nQayta kiriting:")
            return
        state_data = state.get('data') or {}
        post_ch = state_data.get('channel') or get_setting('post_channel_id')
        label = state_data.get('channel_label', '📢 Kanal')
        if not post_ch:
            clear_state(user_id)
            bot.send_message(user_id, "⚠️ Post kanali hali sozlanmagan!\n/setpostchannel @animebum_1")
            return
        set_state(user_id, 'post_channel_photo', {'code': code, 'channel': post_ch})
        bot.send_message(
            user_id,
            f"🎌 <b>{movie['title']}</b>\n"
            f"📢 Kanal: {label}\n\n"
            f"📸 Post uchun <b>RASM</b> yuboring:\n"
            f"(yoki <code>skip</code> yozing — rasmsiz post yuborish)"
        )
        return

    if state.get('state') == 'post_channel_photo' and is_admin(user_id):
        if text.lower() == 'skip':
            data = state.get('data', {})
            code = data.get('code')
            channel = data.get('channel')
            clear_state(user_id)
            movie = get_movie(code)
            if not movie:
                bot.send_message(user_id, "❌ Anime topilmadi!")
                return
            _send_post_to_channel(user_id, movie, channel, photo_file_id=None)
        return

    if state.get('state') == 'add_admin_id' and is_super_admin(user_id):
        uid_text = text.strip()
        try:
            new_admin_id = int(uid_text)
        except ValueError:
            bot.send_message(user_id, "❌ ID raqam bo'lishi kerak! Masalan: <code>123456789</code>")
            return
        if new_admin_id == user_id or new_admin_id in ADMIN_IDS:
            bot.send_message(user_id, "⚠️ Bu foydalanuvchi allaqachon bosh admin!")
            clear_state(user_id)
            return
        ok = add_extra_admin(new_admin_id)
        clear_state(user_id)
        if ok:
            bot.send_message(user_id, f"✅ <b>Admin qo'shildi!</b>\n\nID: <code>{new_admin_id}</code>\n\nEndi u ham admin panelga kira oladi.")
            try:
                bot.send_message(new_admin_id, "🎉 Sizga <b>admin</b> huquqi berildi!\n\n/admin buyrug'i bilan panel ochishingiz mumkin.")
            except Exception:
                pass
        else:
            bot.send_message(user_id, "❌ Qo'shishda xatolik yuz berdi.")
        return

    if state.get('state') == 'set_backup_chat' and is_admin(user_id):
        chat_id = text.strip()
        set_setting('backup_chat_id', chat_id)
        clear_state(user_id)
        bot.send_message(
            user_id,
            f"✅ <b>Backup kanal saqlandi!</b>\n\n"
            f"Kanal: <code>{chat_id}</code>\n\n"
            f"Endi har safar kino/serial qo'shilganda backup avtomatik saqlanadi.\n"
            f"Bot qayta ishlaganda o'zi tiklanadi!"
        )
        backup_data()
        return

    if state.get('state') == 'edit_start_text' and is_admin(user_id):
        new_text = message.text.strip()
        set_setting('start_text', new_text)
        clear_state(user_id)
        preview = new_text.replace('{name}', '<b>Avaz</b>')
        bot.send_message(
            user_id,
            f"✅ <b>Start xabari saqlandi!</b>\n\n"
            f"📋 <b>Ko'rinishi:</b>\n{preview}",
            reply_markup=get_admin_keyboard()
        )
        return

    if state.get('state') == 'edit_contact_text' and is_admin(user_id):
        new_text = message.text.strip()
        set_setting('contact_text', new_text)
        clear_state(user_id)
        bot.send_message(
            user_id,
            f"✅ <b>Bog'lanish xabari saqlandi!</b>\n\n"
            f"📋 <b>Ko'rinishi:</b>\n{new_text}",
            reply_markup=get_admin_keyboard()
        )
        return

    if state.get('state') == 'add_series_count' and is_admin(user_id):
        if not text.isdigit() or int(text) < 1:
            bot.send_message(user_id, "❌ To'g'ri raqam kiriting!")
            return
        data = state.get('data', {})
        data['total_episodes'] = int(text)
        data['current_episode'] = 1
        is_ongoing = data.get('is_ongoing', 0)
        # Serialni bazaga qo'shish (file_id bo'sh, is_series=1)
        add_movie_db(
            code=data['code'],
            title=data['title'],
            description=data.get('description', ''),
            file_id='',
            file_type='video',
            category=data.get('category', 'Umumiy'),
            is_series=1,
            added_by=user_id
        )
        if is_ongoing:
            set_movie_ongoing(data['code'], 1)
        set_state(user_id, 'add_series_file', data)
        ongoing_note = "\n🔄 <b>Ongoing</b> — yangi qismlar chiqqanda obunachilarga xabar yuboriladi!" if is_ongoing else ""
        bot.send_message(
            user_id,
            f"📺 <b>{data['title']}</b> — {data['total_episodes']} qism{ongoing_note}\n\n"
            f"1️⃣ 1-qism faylini yuboring (video):"
        )
        return

    if state.get('state') == 'add_channel_id' and is_admin(user_id):
        ch_id = text.strip()
        if not ch_id.startswith('@') and not ch_id.startswith('-'):
            ch_id = '@' + ch_id
        set_state(user_id, 'add_channel_name', {'channel_id': ch_id})
        bot.send_message(user_id, f"✅ Kanal ID: <code>{ch_id}</code>\n\n2️⃣ Kanal nomini kiriting (masalan: <b>📢 Asosiy Kanal</b>):")
        return

    if state.get('state') == 'add_channel_name' and is_admin(user_id):
        data = state.get('data', {})
        data['channel_name'] = text.strip()
        set_state(user_id, 'add_channel_url', data)
        bot.send_message(user_id, f"✅ Nomi: <b>{text}</b>\n\n3️⃣ Kanal havolasini kiriting (masalan: <code>https://t.me/kanal</code>):")
        return

    if state.get('state') == 'add_channel_url' and is_admin(user_id):
        data = state.get('data', {})
        ch_url = text.strip()
        if not ch_url.startswith('http'):
            ch_url = 'https://t.me/' + ch_url.lstrip('@')
        success = add_channel(data['channel_id'], data['channel_name'], ch_url, user_id)
        clear_state(user_id)
        if success:
            bot.send_message(
                user_id,
                f"✅ <b>Kanal qo'shildi!</b>\n\n🆔 <code>{data['channel_id']}</code>\n📢 {data['channel_name']}\n🔗 {ch_url}\n\n⚠️ Botni shu kanalga admin qilib qo'shing!"
            )
            show_channels_menu(user_id)
        else:
            bot.send_message(user_id, f"❌ Bu kanal allaqachon qo'shilgan!")
        return

    if state.get('state') == 'set_status_id' and is_admin(user_id):
        try:
            target_id = int(text)
            set_state(user_id, 'set_status_value', {'target_id': target_id})
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("👤 Standard", callback_data=f"setstatus_{target_id}_user"),
                InlineKeyboardButton("💎 Premium", callback_data=f"setstatus_{target_id}_premium"),
                InlineKeyboardButton("👑 Admin", callback_data=f"setstatus_{target_id}_admin")
            )
            bot.send_message(user_id, f"👤 Foydalanuvchi: <code>{target_id}</code>\n\nStatusni tanlang:", reply_markup=keyboard)
        except ValueError:
            bot.send_message(user_id, "❌ Noto'g'ri ID!")
            clear_state(user_id)
        return

    # ── TUGMALAR ─────────────────────────────────────────────────

    if text == "🎬 Anime Izlash":
        bot.send_message(user_id, "🎌 <b>Anime Kodini Kiriting</b>\n\nAnime yoki serial kodini yozing (masalan: <code>101</code>):")
        return

    if text == "🔍 Qidiruv":
        set_state(user_id, 'searching')
        bot.send_message(user_id, "🔍 <b>Anime Qidirish</b>\n\nQidirmoqchi bo'lgan anime nomini yozing:")
        return

    if text == "⭐ Mashhur Animlar":
        movies = get_popular_movies(10)
        if not movies:
            bot.send_message(user_id, "📭 Hali anime yo'q.")
            return
        text_msg = "⭐ <b>ENG MASHHUR ANIMLAR</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        keyboard = InlineKeyboardMarkup(row_width=1)
        for i, (code, title, views, category) in enumerate(movies, 1):
            text_msg += f"{i}. 🎌 <b>{title}</b>\n   👁️ {views} | 📂 {category} | 🔢 <code>{code}</code>\n\n"
            keyboard.add(InlineKeyboardButton(f"▶️ {title[:30]}", callback_data=f"get_movie_{code}"))
        bot.send_message(user_id, text_msg, reply_markup=keyboard)
        return

    if text == "🆕 Yangi Animlar":
        movies = get_latest_movies(10)
        if not movies:
            bot.send_message(user_id, "📭 Hali anime yo'q.")
            return
        text_msg = "🆕 <b>YANGI ANIMLAR</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        keyboard = InlineKeyboardMarkup(row_width=1)
        for i, (code, title, added_at, category) in enumerate(movies, 1):
            date_str = added_at[:10] if added_at else 'N/A'
            text_msg += f"{i}. 🎌 <b>{title}</b>\n   📅 {date_str} | 📂 {category} | 🔢 <code>{code}</code>\n\n"
            keyboard.add(InlineKeyboardButton(f"▶️ {title[:30]}", callback_data=f"get_movie_{code}"))
        bot.send_message(user_id, text_msg, reply_markup=keyboard)
        return

    if text == "📂 Janrlar":
        keyboard = get_category_keyboard()
        bot.send_message(user_id, "📂 <b>JANRLAR</b>\n\nQuyidagi janrlardan birini tanlang:", reply_markup=keyboard)
        return

    if text == "📞 Bog'lanish":
        default_contact = (
            "📞 <b>BOG'LANISH</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 Savol va takliflar uchun:\n\n"
            "👤 Admin: @animebum_1\n\n"
            "📢 Kanal: t.me/animebum_1\n\n"
            "🕐 Tez orada javob beramiz!"
        )
        contact_text = get_setting('contact_text') or default_contact
        bot.send_message(user_id, contact_text)
        return

    if text == "⚙️ Admin Panel" and is_admin(user_id):
        admin_panel(message)
        return

    if text == "🔙 Orqaga":
        keyboard = get_main_keyboard_for_user(user_id, user_status)
        bot.send_message(user_id, "🏠 Bosh sahifa", reply_markup=keyboard)
        return

    # Admin tugmalari
    if is_admin(user_id):
        if text == "➕ Anime Qo'shish":
            add_movie_command(message)
            return
        if text == "🗑️ Anime O'chirish":
            delete_movie_command(message)
            return
        if text == "📊 Statistika":
            stats_command(message)
            return
        if text == "👥 Foydalanuvchilar":
            counts = get_users_count()
            bot.send_message(
                user_id,
                f"👥 <b>FOYDALANUVCHILAR</b>\n\n"
                f"Jami: <b>{counts.get('total', 0)}</b>\n"
                f"Oddiy: <b>{counts.get('user', 0)}</b>"
            )
            return
        if text == "📣 Broadcast":
            broadcast_command(message)
            return
        if text == "📡 Kanal Sozlash":
            show_channels_menu(user_id)
            return
        if text == "➕ Qism Qo'shish":
            add_episode_command(message)
            return
        if text == "📢 Kanalga Post":
            anime_ch = get_setting('post_channel_id')
            drama_ch = get_setting('post_channel_drama_id')
            if not anime_ch and not drama_ch:
                bot.send_message(user_id,
                    "⚠️ Hali hech qanday post kanali sozlanmagan!\n\n"
                    "/setpostchannel @animebum_1 — Anime kanali\n"
                    "/setdramachannel @drama_kanal — Drama kanali")
                return
            kb = InlineKeyboardMarkup(row_width=1)
            if anime_ch:
                kb.add(InlineKeyboardButton(f"📺 Anime kanali ({anime_ch})", callback_data="postchan_anime"))
            if drama_ch:
                kb.add(InlineKeyboardButton(f"🎭 Drama kanali ({drama_ch})", callback_data="postchan_drama"))
            bot.send_message(user_id, "📢 <b>Qaysi kanalga post qilasiz?</b>", reply_markup=kb)
            return
        if text == "👥 Adminlar":
            if not is_super_admin(user_id):
                bot.send_message(user_id, "❌ Bu bo'lim faqat bosh admin uchun!")
                return
            admins = get_extra_admins()
            kb = InlineKeyboardMarkup(row_width=1)
            for a in admins:
                name = a['full_name'] or a['username'] or str(a['user_id'])
                kb.add(InlineKeyboardButton(
                    f"❌ {name} [{a['user_id']}] — O'chirish",
                    callback_data=f"remove_admin_{a['user_id']}"
                ))
            kb.add(InlineKeyboardButton("➕ Yangi admin qo'shish", callback_data="add_admin_start"))
            msg = "👥 <b>ADMINLAR RO'YXATI</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            msg += f"👑 Bosh admin: <code>{ADMIN_IDS[0]}</code> (siz)\n\n"
            if admins:
                msg += f"📋 Qo'shimcha adminlar ({len(admins)} ta):\n"
                for a in admins:
                    name = a['full_name'] or a['username'] or '—'
                    msg += f"• {name} — <code>{a['user_id']}</code>\n"
            else:
                msg += "📭 Hali qo'shimcha admin yo'q.\n"
            msg += "\n➕ Admin qo'shish uchun tugmani bosing."
            bot.send_message(user_id, msg, reply_markup=kb)
            return
        if text == "🔄 Ongoing Boshqarish":
            conn = sqlite3.connect('kino_bot.db', timeout=30)
            cursor = conn.cursor()
            cursor.execute("SELECT code, title, is_ongoing FROM movies WHERE is_series = 1 AND is_ongoing = 1 ORDER BY added_at DESC")
            serials = cursor.fetchall()
            conn.close()
            if not serials:
                bot.send_message(user_id, "📭 Hozirda ongoing serial yo'q.")
                return
            kb = InlineKeyboardMarkup(row_width=1)
            for code, title, is_ongoing in serials:
                label = f"🔄 {title[:35]} [{code}]"
                kb.add(InlineKeyboardButton(label, callback_data=f"ongoing_toggle_{code}"))
            bot.send_message(
                user_id,
                f"🔄 <b>ONGOING SERIALLAR</b> ({len(serials)} ta)\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Serialga bosib yangi qism qo'shing yoki tugallangan qiling:\n\n",
                reply_markup=kb
            )
            return
        if text == "💾 Backup":
            bot.send_message(user_id, "⏳ Backup saqlanmoqda...")
            if backup_data():
                bot.send_message(user_id, "✅ <b>Backup muvaffaqiyatli saqlandi!</b>")
            else:
                bot.send_message(
                    user_id,
                    "❌ Backup kanal sozlanmagan!\n\n"
                    "/setbackup buyrug'i bilan kanal belgilang."
                )
            return
        if text == "✏️ Start Matni":
            current = get_setting('start_text') or '(standart matn)'
            set_state(user_id, 'edit_start_text')
            bot.send_message(
                user_id,
                "✏️ <b>START XABARI TAHRIRLASH</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Foydalanuvchi ismi uchun <code>{name}</code> yozing.\n\n"
                f"📋 <b>Hozirgi matn:</b>\n{current}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "✍️ Yangi start xabarini yozing:",
                reply_markup=types.ForceReply()
            )
            return
        if text == "✏️ Bog'lanish Matni":
            current = get_setting('contact_text') or '(standart matn)'
            set_state(user_id, 'edit_contact_text')
            bot.send_message(
                user_id,
                "✏️ <b>BOG'LANISH XABARI TAHRIRLASH</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📋 <b>Hozirgi matn:</b>\n{current}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "✍️ Yangi bog'lanish xabarini yozing:",
                reply_markup=types.ForceReply()
            )
            return

    # Kino kodi qidirish
    if text.isdigit() or text.replace(' ', '').isdigit():
        movie = get_movie(text.strip())
        if movie:
            send_movie(user_id, movie, user_status)
        else:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔍 Qidirish", callback_data="start_search"))
            bot.send_message(
                user_id,
                f"❌ <b>{text}</b> kodli kino topilmadi!\n\n"
                f"💡 Kodni to'g'ri kiritganingizni tekshiring.",
                reply_markup=keyboard
            )
        return

    # Matn bo'lsa qidirish
    results = search_movies(text)
    if results and len(text) > 2:
        do_search(user_id, text)
    else:
        bot.send_message(
            user_id,
            f"❓ <b>Kino kodi kiriting!</b>\n\nKino kodini yozing (masalan: <code>101</code>)\nYoki kino nomini yozib qidiring."
        )

# ╔══════════════════════════════════════════════════════════════╗
# ║              📁 FAYL HANDLERLARI (VIDEO, HUJJAT)             ║
# ╚══════════════════════════════════════════════════════════════╝

@bot.message_handler(content_types=['video', 'document', 'photo', 'audio', 'voice', 'animation', 'sticker'])
def file_handler(message):
    user_id = message.from_user.id
    state = get_state(user_id)

    # ── BROADCAST — HAR QANDAY KONTENT ───────────────────────────
    if state.get('state') == 'broadcast' and is_admin(user_id):
        clear_state(user_id)
        do_broadcast(user_id, message)
        return

    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Faqat adminlar fayl yuborishi mumkin.")
        return

    # ── KINO FAYLI ───────────────────────────────────────────────
    if state.get('state') == 'add_movie_file':
        data = state.get('data', {})
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_type = 'video'
        elif message.content_type == 'document':
            file_id = message.document.file_id
            file_type = 'document'
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_type = 'photo'
        else:
            bot.send_message(user_id, "❌ Noto'g'ri fayl turi!")
            return

        success = add_movie_db(
            code=data['code'],
            title=data['title'],
            description=data.get('description', ''),
            file_id=file_id,
            file_type=file_type,
            category=data.get('category', 'Umumiy'),
            is_series=0,
            added_by=user_id
        )
        clear_state(user_id)
        if success:
            bot.send_message(
                user_id,
                f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
                f"🔢 Kod: <code>{data['code']}</code>\n"
                f"🎬 Nom: <b>{data['title']}</b>\n"
                f"📂 Kategoriya: {data.get('category', 'Umumiy')}"
            )
        else:
            bot.send_message(user_id, f"❌ Xatolik! <code>{data['code']}</code> kodli kino allaqachon mavjud.")
        return

    # ── SERIAL QISMLARI ───────────────────────────────────────────
    if state.get('state') == 'add_series_file':
        data = state.get('data', {})
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_type = 'video'
        elif message.content_type == 'document':
            file_id = message.document.file_id
            file_type = 'document'
        else:
            current_ep = data.get('current_episode', 1)
            bot.send_message(user_id, f"❌ Iltimos {current_ep}-qism uchun video fayl yuboring!")
            return

        current_ep = data.get('current_episode', 1)
        total_eps = data.get('total_episodes', 1)

        add_series_episode(data['code'], current_ep, file_id, file_type)

        if current_ep >= total_eps:
            clear_state(user_id)
            bot.send_message(
                user_id,
                f"✅ <b>Serial to'liq saqlandi!</b>\n\n"
                f"🔢 Kod: <code>{data['code']}</code>\n"
                f"📺 Nom: <b>{data['title']}</b>\n"
                f"🎞 Qismlar: <b>{total_eps} ta</b>\n\n"
                f"Endi foydalanuvchilar <code>{data['code']}</code> yozib serialni olishlari mumkin!"
            )
            backup_data()
        else:
            next_ep = current_ep + 1
            data['current_episode'] = next_ep
            set_state(user_id, 'add_series_file', data)
            bot.send_message(
                user_id,
                f"✅ {current_ep}-qism saqlandi.\n\n"
                f"▶️ {next_ep}-qism faylini yuboring: ({next_ep}/{total_eps})"
            )
        return

    # ── /ADDEPISODE ORQALI YAKKA QISM QO'SHISH ───────────────────
    if state.get('state') == 'add_episode_file' and is_admin(user_id):
        data = state.get('data', {})
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_type = 'video'
        elif message.content_type == 'document':
            file_id = message.document.file_id
            file_type = 'document'
        else:
            ep_num = data.get('episode_num', '?')
            bot.send_message(user_id, f"❌ {ep_num}-qism uchun video fayl yuboring!")
            return

        ep_num = data.get('episode_num', 1)
        code = data.get('code')
        title = data.get('title', code)

        add_series_episode(code, ep_num, file_id, file_type)
        total_now = get_series_episodes_count(code)
        clear_state(user_id)

        movie_check = get_movie(code)
        is_ongoing = movie_check and movie_check.get('is_ongoing')
        poster_id = movie_check.get('poster_file_id') if movie_check else None

        bot.send_message(
            user_id,
            f"✅ <b>{ep_num}-qism qo'shildi!</b>\n\n"
            f"📺 Serial: <b>{title}</b>\n"
            f"🔢 Kod: <code>{code}</code>\n"
            f"🎞 Jami qismlar: <b>{total_now} ta</b>"
            + ("\n\n🔔 Barcha obunachilarga xabar yuborilmoqda...\n📢 Kanalga post chiqmoqda..." if is_ongoing else "")
        )
        if is_ongoing:
            notify_ongoing_new_episode(code, title, ep_num, total_now)
            # Kanalga eski poster bilan avtomatik post
            post_ch = get_setting('post_channel_id')
            if post_ch and movie_check:
                try:
                    if poster_id:
                        _send_post_to_channel_ongoing(movie_check, post_ch, ep_num, total_now)
                    else:
                        bot.send_message(user_id, "⚠️ Poster yo'q — kanalga post chiqarilmadi. Avval kanalga post qiling (rasm bilan).")
                except Exception as pe:
                    logger.error(f"Auto post xatosi: {pe}")
        backup_data()
        return

    # ── KANALGA POST UCHUN RASM ───────────────────────────────────
    if state.get('state') == 'post_channel_photo' and is_admin(user_id):
        if message.content_type != 'photo':
            bot.send_message(user_id, "❌ Iltimos rasm yuboring (yoki skip yozing)!")
            return
        data = state.get('data', {})
        code = data.get('code')
        channel = data.get('channel')
        clear_state(user_id)
        photo_file_id = message.photo[-1].file_id
        movie = get_movie(code)
        if not movie:
            bot.send_message(user_id, "❌ Anime topilmadi!")
            return
        _send_post_to_channel(user_id, movie, channel, photo_file_id=photo_file_id)
        return

# ╔══════════════════════════════════════════════════════════════╗
# ║              📲 CALLBACK QUERY HANDLERLARI                   ║
# ╚══════════════════════════════════════════════════════════════╝

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data

    try:
        # Obuna tekshirish
        if data == "check_subscription":
            is_subscribed, not_subscribed = check_subscription(user_id)
            if is_subscribed:
                bot.answer_callback_query(call.id, "✅ Ajoyib! Siz barcha kanallarga obuna bo'lgansiz!")
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass

                # Deep link orqali kelgan bo'lsa — pending kinoni yubor
                pending_state = get_state(user_id)
                if pending_state and pending_state.get('state') == 'pending_movie':
                    pending_code = pending_state.get('data', {}).get('code')
                    clear_state(user_id)
                    user = get_user(user_id)
                    user_status = user.get('status', 'user') if user else 'user'
                    if pending_code:
                        movie = get_movie(pending_code)
                        if movie:
                            send_movie(user_id, movie, user_status)
                            return
                else:
                    class FakeMsg:
                        pass
                    fake = FakeMsg()
                    fake.from_user = call.from_user
                    fake.text = '/start'
                    fake.chat = call.message.chat
                    start_handler(fake)
            else:
                bot.answer_callback_query(call.id, "❌ Obuna bo'lmadingiz! Avval kanallarga obuna bo'ling.")
                keyboard = get_subscription_keyboard(not_subscribed)
                try:
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyboard)
                except Exception:
                    pass
            return

        # Serial sahifasini almashtirish (Keyingisi/Ortga)
        if data.startswith("epg_"):
            rest = data[4:]  # "101_1"
            page = int(rest.rsplit("_", 1)[1])
            code = rest.rsplit("_", 1)[0]
            movie = get_movie(code)
            if movie:
                total = get_series_episodes_count(code)
                ep_keyboard = get_episodes_keyboard(code, total, viewer_id=user_id, page=page)
                bot.answer_callback_query(call.id)
                try:
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=ep_keyboard)
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Serial topilmadi!")
            return

        # Serial qismini yuborish
        if data.startswith("ep_"):
            parts = data.split("_", 2)
            code = parts[1]
            episode_num = int(parts[2])
            movie = get_movie(code)
            if movie:
                bot.answer_callback_query(call.id, f"⏳ {episode_num}-qism yuklanmoqda...")
                send_series_episode(user_id, movie, episode_num)
            else:
                bot.answer_callback_query(call.id, "❌ Serial topilmadi!")
            return

        # Kino olish (inline)
        if data.startswith("get_movie_"):
            code = data.replace("get_movie_", "")
            movie = get_movie(code)
            user = get_user(user_id)
            user_status = user.get('status', 'user') if user else 'user'
            if movie:
                send_movie(user_id, movie, user_status)
                bot.answer_callback_query(call.id)
            else:
                bot.answer_callback_query(call.id, "❌ Kino topilmadi!")
            return

        # Kategoriya kinolar
        if data.startswith("category_"):
            category = data.replace("category_", "")
            movies = get_movies_by_category(category)
            if not movies:
                bot.answer_callback_query(call.id, f"❌ '{category}' janrida kino yo'q!")
                return
            text_msg = f"📂 <b>{category}</b> janri\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            for code, title, views in movies:
                text_msg += f"🎬 <b>{title}</b>\n   👁️ {views} | 🔢 <code>{code}</code>\n\n"
                keyboard.add(InlineKeyboardButton(f"▶️ {title[:30]}", callback_data=f"get_movie_{code}"))
            bot.answer_callback_query(call.id)
            bot.send_message(user_id, text_msg, reply_markup=keyboard)
            return

        # Admin — ko'p janr tanlash (toggle)
        if data.startswith("admin_cat_") and is_admin(user_id):
            genre = data.replace("admin_cat_", "")
            state = get_state(user_id)
            if state.get('state') == 'add_movie_category':
                if user_id not in genre_selections:
                    genre_selections[user_id] = []
                selected = genre_selections[user_id]
                if genre in selected:
                    selected.remove(genre)
                    bot.answer_callback_query(call.id, f"❌ {genre} olib tashlandi")
                else:
                    selected.append(genre)
                    bot.answer_callback_query(call.id, f"✅ {genre} tanlandi")
                # Klaviaturani yangilash
                new_keyboard = build_genre_keyboard(user_id)
                try:
                    bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=new_keyboard
                    )
                except Exception:
                    pass
            return

        # Admin — janr tanlovini tasdiqlash
        if data == "admin_genre_done" and is_admin(user_id):
            state = get_state(user_id)
            if state.get('state') == 'add_movie_category':
                selected = genre_selections.get(user_id, [])
                if not selected:
                    bot.answer_callback_query(call.id, "⚠️ Kamida bitta janr tanlang!")
                    return
                movie_data = state.get('data', {})
                category_str = ", ".join(selected)
                movie_data['category'] = category_str
                bot.answer_callback_query(call.id, f"✅ Janrlar saqlandi: {category_str}")
                # Kino yoki serial tanlash
                kb = InlineKeyboardMarkup(row_width=2)
                kb.add(
                    InlineKeyboardButton("🎬 Kino (bitta fayl)", callback_data="admin_type_movie"),
                    InlineKeyboardButton("📺 Serial (ko'p qism)", callback_data="admin_type_series")
                )
                set_state(user_id, 'add_movie_type', movie_data)
                genre_selections.pop(user_id, None)
                try:
                    bot.edit_message_text(
                        f"✅ Janrlar: <b>{category_str}</b>\n\n7️⃣ Bu kino yoki serialmi?",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=kb
                    )
                except Exception:
                    bot.send_message(
                        user_id,
                        f"✅ Janrlar: <b>{category_str}</b>\n\n7️⃣ Bu kino yoki serialmi?",
                        reply_markup=kb
                    )
            return

        # Admin kino/serial turi tanlash
        if data.startswith("admin_type_") and is_admin(user_id):
            state = get_state(user_id)
            movie_data = state.get('data', {})
            ctype = data.replace("admin_type_", "")

            if ctype == 'movie':
                set_state(user_id, 'add_movie_file', movie_data)
                bot.answer_callback_query(call.id, "✅ Kino tanlandi")
                bot.send_message(user_id, "6️⃣ Kino faylini yuboring (video):")
            else:
                # Serial — hali davom etmoqdami?
                kb = InlineKeyboardMarkup(row_width=2)
                kb.add(
                    InlineKeyboardButton("🔄 Ha, ongoing", callback_data="admin_ongoing_yes"),
                    InlineKeyboardButton("✅ Yo'q, tugallangan", callback_data="admin_ongoing_no")
                )
                set_state(user_id, 'add_series_ongoing', movie_data)
                bot.answer_callback_query(call.id, "✅ Serial tanlandi")
                bot.send_message(
                    user_id,
                    "6️⃣ Bu serial hali <b>davom etmoqdami?</b>\n\n"
                    "🔄 <b>Ha, ongoing</b> — yangi qismlar chiqa beradi\n"
                    "✅ <b>Yo'q</b> — barcha qismlar tayyor",
                    reply_markup=kb
                )
            return

        # Ongoing holati tanlash
        if data in ("admin_ongoing_yes", "admin_ongoing_no") and is_admin(user_id):
            state = get_state(user_id)
            if state.get('state') == 'add_series_ongoing':
                movie_data = state.get('data', {})
                movie_data['is_ongoing'] = 1 if data == "admin_ongoing_yes" else 0
                ongoing_text = "🔄 Ongoing (yangi qismlar chiqadi)" if movie_data['is_ongoing'] else "✅ Tugallangan"
                set_state(user_id, 'add_series_count', movie_data)
                bot.answer_callback_query(call.id, f"✅ {ongoing_text}")
                bot.send_message(
                    user_id,
                    f"Holat: <b>{ongoing_text}</b>\n\n"
                    f"6️⃣ Hozircha nechta qism bor? Raqam yuboring:\n"
                    f"Misol: <code>6</code>"
                )
            return

        # Admin — tezkor keyingi qism qo'shish (serial ko'rish sahifasidagi tugma)
        if data.startswith("admin_quickadd_") and is_admin(user_id):
            code = data.replace("admin_quickadd_", "")
            movie = get_movie(code)
            if not movie:
                bot.answer_callback_query(call.id, "❌ Serial topilmadi!")
                return
            existing = get_series_episodes_count(code)
            next_ep = existing + 1
            set_state(user_id, 'add_episode_file', {
                'code': code,
                'title': movie['title'],
                'episode_num': next_ep
            })
            bot.answer_callback_query(call.id, f"➕ {next_ep}-qism qo'shilmoqda...")
            bot.send_message(
                user_id,
                f"➕ <b>{movie['title']}</b>\n\n"
                f"Hozir: <b>{existing} qism</b> mavjud\n\n"
                f"<b>{next_ep}-qism</b> faylini yuboring (video):"
            )
            return

        # Reyting berish
        if data.startswith("rate_"):
            parts = data.split("_")
            movie_code = parts[1]
            rating = int(parts[2])
            result = rate_movie(user_id, movie_code, rating)
            stars = "⭐" * rating
            if result == "added":
                bot.answer_callback_query(call.id, f"✅ Baholadingiz: {stars}")
            else:
                bot.answer_callback_query(call.id, f"✅ Bahoyingiz yangilandi: {stars}")
            return

        # Admin status berish
        if data.startswith("setstatus_") and is_admin(user_id):
            parts = data.split("_")
            target_id = int(parts[1])
            new_status = parts[2]
            status_names = {'user': 'Standard', 'premium': 'Premium', 'admin': 'Admin'}
            if new_status == 'premium':
                kb = InlineKeyboardMarkup(row_width=3)
                kb.add(
                    InlineKeyboardButton("7 kun", callback_data=f"setdays_{target_id}_7"),
                    InlineKeyboardButton("30 kun", callback_data=f"setdays_{target_id}_30"),
                    InlineKeyboardButton("90 kun", callback_data=f"setdays_{target_id}_90"),
                )
                kb.add(InlineKeyboardButton("♾️ Cheksiz", callback_data=f"setdays_{target_id}_0"))
                bot.answer_callback_query(call.id)
                try:
                    bot.edit_message_text(
                        f"💎 Foydalanuvchi <code>{target_id}</code> uchun Premium muddati:",
                        call.message.chat.id, call.message.message_id, reply_markup=kb
                    )
                except Exception:
                    pass
                return
            if update_user_status(target_id, new_status, days=0):
                bot.answer_callback_query(call.id, f"✅ Status berildi: {status_names[new_status]}")
                clear_state(user_id)
                try:
                    bot.send_message(target_id, f"🎉 Sizga <b>{status_names[new_status]}</b> statusi berildi!")
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Foydalanuvchi topilmadi!")
            return

        if data.startswith("setdays_") and is_admin(user_id):
            parts = data.split("_")
            target_id = int(parts[1])
            days = int(parts[2])
            if update_user_status(target_id, 'premium', days=days):
                duration_text = f"{days} kun" if days > 0 else "Cheksiz ♾️"
                bot.answer_callback_query(call.id, "✅ Premium berildi!")
                clear_state(user_id)
                try:
                    bot.send_message(target_id, f"🎉 <b>💎 Premium</b> status berildi!\nMuddati: <b>{duration_text}</b>")
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Foydalanuvchi topilmadi!")
            return

        # Kunlik bonus
        if data == "daily_bonus":
            success, points, info = claim_daily_bonus(user_id)
            if success:
                bot.answer_callback_query(call.id, f"🎁 +{info} ball!")
                bot.send_message(user_id, f"🎁 <b>Kunlik Bonus!</b>\n\n✅ +{info} ball oldingiz!\n💰 Jami: <b>{points}</b>")
            else:
                bot.answer_callback_query(call.id, f"⏰ {info}dan so'ng qaytib keling!")
            return

        if data == "referral_info":
            referral_command(call.message)
            bot.answer_callback_query(call.id)
            return

        if data == "chadd_start" and is_admin(user_id):
            set_state(user_id, 'add_channel_id')
            bot.answer_callback_query(call.id)
            bot.send_message(
                user_id,
                "➕ <b>Yangi Majburiy Kanal Qo'shish</b>\n\n"
                "1️⃣ Kanal ID sini kiriting:\n\n"
                "📌 Misollar:\n  • <code>@kanal_username</code>\n  • <code>-1001234567890</code>\n\n"
                "⚠️ Botni avval shu kanalga <b>admin</b> qilib qo'shing!"
            )
            return

        if data.startswith("chremove_") and is_admin(user_id):
            ch_id = data.replace("chremove_", "", 1)
            if remove_channel(ch_id):
                bot.answer_callback_query(call.id, f"✅ Kanal o'chirildi!")
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
                show_channels_menu(user_id)
            else:
                bot.answer_callback_query(call.id, "❌ Kanal topilmadi!")
            return

        if data == "start_search":
            set_state(user_id, 'searching')
            bot.answer_callback_query(call.id)
            bot.send_message(user_id, "🔍 Qidirmoqchi bo'lgan kino nomini yozing:")
            return

        # Kanal tanlash (Anime yoki Drama)
        if data in ("postchan_anime", "postchan_drama") and is_admin(user_id):
            if data == "postchan_anime":
                ch = get_setting('post_channel_id')
                label = "📺 Anime kanali"
            else:
                ch = get_setting('post_channel_drama_id')
                label = "🎭 Drama kanali"
            if not ch:
                bot.answer_callback_query(call.id, "❌ Bu kanal hali sozlanmagan!")
                return
            bot.answer_callback_query(call.id, f"✅ {label} tanlandi")
            # Agar oldin kod berilgan bo'lsa (post_channel_select_pending state)
            cur_state = get_state(user_id)
            pending_code = None
            if cur_state and cur_state.get('state') == 'post_channel_select_pending':
                pending_code = (cur_state.get('data') or {}).get('code')
            if pending_code:
                movie = get_movie(pending_code)
                if not movie:
                    clear_state(user_id)
                    bot.send_message(user_id, f"❌ <code>{pending_code}</code> kodli anime topilmadi!")
                    return
                set_state(user_id, 'post_channel_photo', {'code': pending_code, 'channel': ch})
                bot.send_message(
                    user_id,
                    f"🎌 <b>{movie['title']}</b>\n"
                    f"📢 Kanal: {label}\n\n"
                    f"📸 Post uchun <b>RASM</b> yuboring:\n"
                    f"(yoki <code>skip</code> yozing — rasmsiz post yuborish)"
                )
            else:
                set_state(user_id, 'post_channel_ask_code', {'channel': ch, 'channel_label': label})
                bot.send_message(
                    user_id,
                    f"📢 <b>{label}</b>: <code>{ch}</code>\n\n"
                    f"Qaysi anime/serial kodini post qilmoqchisiz?\n"
                    f"Kodini kiriting (masalan: <code>A12</code> yoki <code>D5</code>):"
                )
            return

        # Admin qo'shish — ID so'rash
        if data == "add_admin_start" and is_super_admin(user_id):
            set_state(user_id, 'add_admin_id')
            bot.answer_callback_query(call.id)
            bot.send_message(
                user_id,
                "👤 <b>Yangi admin qo'shish</b>\n\n"
                "Adminlik bermoqchi bo'lgan odamning <b>Telegram ID</b>sini yuboring.\n\n"
                "📌 ID ni bilish uchun u kishi @userinfobot ga yozsin yoki sizga forward qilsin.\n\n"
                "Masalan: <code>123456789</code>"
            )
            return

        # Adminni o'chirish
        if data.startswith("remove_admin_") and is_super_admin(user_id):
            target_id = int(data.replace("remove_admin_", ""))
            ok = remove_extra_admin(target_id)
            if ok:
                bot.answer_callback_query(call.id, "✅ Admin o'chirildi")
                try:
                    bot.send_message(target_id, "ℹ️ Sizning admin huquqingiz olib qo'yildi.")
                except Exception:
                    pass
                # Ro'yxatni yangilash
                admins = get_extra_admins()
                kb = InlineKeyboardMarkup(row_width=1)
                for a in admins:
                    name = a['full_name'] or a['username'] or str(a['user_id'])
                    kb.add(InlineKeyboardButton(
                        f"❌ {name} [{a['user_id']}] — O'chirish",
                        callback_data=f"remove_admin_{a['user_id']}"
                    ))
                kb.add(InlineKeyboardButton("➕ Yangi admin qo'shish", callback_data="add_admin_start"))
                msg = "👥 <b>ADMINLAR RO'YXATI</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                msg += f"👑 Bosh admin: <code>{ADMIN_IDS[0]}</code> (siz)\n\n"
                if admins:
                    msg += f"📋 Qo'shimcha adminlar ({len(admins)} ta):\n"
                    for a in admins:
                        name = a['full_name'] or a['username'] or '—'
                        msg += f"• {name} — <code>{a['user_id']}</code>\n"
                else:
                    msg += "📭 Hali qo'shimcha admin yo'q.\n"
                msg += "\n➕ Admin qo'shish uchun tugmani bosing."
                try:
                    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=kb)
                except Exception:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Admin topilmadi!")
            return

        # Ongoing ro'yxatiga qaytish
        if data == "ongoing_list" and is_admin(user_id):
            conn = sqlite3.connect('kino_bot.db', timeout=30)
            cursor = conn.cursor()
            cursor.execute("SELECT code, title, is_ongoing FROM movies WHERE is_series = 1 AND is_ongoing = 1 ORDER BY added_at DESC")
            serials = cursor.fetchall()
            conn.close()
            kb = InlineKeyboardMarkup(row_width=1)
            for sc, st, sio in serials:
                lb = f"🔄 {st[:35]} [{sc}]"
                kb.add(InlineKeyboardButton(lb, callback_data=f"ongoing_toggle_{sc}"))
            bot.answer_callback_query(call.id)
            try:
                bot.edit_message_text(
                    "🔄 <b>ONGOING BOSHQARISH</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "🔄 = Ongoing  |  ✅ = Tugallangan\n\nSerialga bosing:",
                    call.message.chat.id, call.message.message_id, reply_markup=kb
                )
            except Exception:
                pass
            return

        # Ongoing serial tafsiloti
        if data.startswith("ongoing_toggle_") and is_admin(user_id):
            code = data.replace("ongoing_toggle_", "")
            movie = get_movie(code)
            if not movie:
                bot.answer_callback_query(call.id, "❌ Serial topilmadi!")
                return
            ep_count = get_series_episodes_count(code)
            is_ongoing = movie.get('is_ongoing', 0)
            status = "🔄 Ongoing" if is_ongoing else "✅ Tugallangan"
            poster_str = "✅ Bor" if movie.get('poster_file_id') else "❌ Yo'q (avval kanalga post qiling)"
            toggle_label = "✅ Tugallangan qilish" if is_ongoing else "🔄 Ongoing qilish"
            kb = InlineKeyboardMarkup(row_width=1)
            kb.add(InlineKeyboardButton("➕ Yangi qism qo'shish", callback_data=f"ongoing_addepisode_{code}"))
            kb.add(InlineKeyboardButton(toggle_label, callback_data=f"ongoing_setstatus_{code}"))
            kb.add(InlineKeyboardButton("◀️ Ro'yxatga qaytish", callback_data="ongoing_list"))
            bot.answer_callback_query(call.id)
            try:
                bot.edit_message_text(
                    f"📺 <b>{movie['title']}</b>\n"
                    f"🔢 Kod: <code>{code}</code>\n"
                    f"📊 Holat: {status}\n"
                    f"🎞 Qismlar: <b>{ep_count} ta</b>\n"
                    f"🖼 Poster: {poster_str}",
                    call.message.chat.id, call.message.message_id, reply_markup=kb
                )
            except Exception:
                bot.send_message(
                    user_id,
                    f"📺 <b>{movie['title']}</b> | {status} | {ep_count} qism",
                    reply_markup=kb
                )
            return

        # Ongoing holatini toggle
        if data.startswith("ongoing_setstatus_") and is_admin(user_id):
            code = data.replace("ongoing_setstatus_", "")
            movie = get_movie(code)
            if not movie:
                bot.answer_callback_query(call.id, "❌ Serial topilmadi!")
                return
            new_val = 0 if movie.get('is_ongoing') else 1
            set_movie_ongoing(code, new_val)
            status_text = "🔄 Ongoing qilindi" if new_val else "✅ Tugallangan qilindi"
            bot.answer_callback_query(call.id, status_text)
            # Tafsilot sahifasini yangilash
            ep_count = get_series_episodes_count(code)
            is_ongoing = new_val
            status = "🔄 Ongoing" if is_ongoing else "✅ Tugallangan"
            poster_str = "✅ Bor" if movie.get('poster_file_id') else "❌ Yo'q (avval kanalga post qiling)"
            toggle_label = "✅ Tugallangan qilish" if is_ongoing else "🔄 Ongoing qilish"
            kb = InlineKeyboardMarkup(row_width=1)
            kb.add(InlineKeyboardButton("➕ Yangi qism qo'shish", callback_data=f"ongoing_addepisode_{code}"))
            kb.add(InlineKeyboardButton(toggle_label, callback_data=f"ongoing_setstatus_{code}"))
            kb.add(InlineKeyboardButton("◀️ Ro'yxatga qaytish", callback_data="ongoing_list"))
            try:
                bot.edit_message_text(
                    f"📺 <b>{movie['title']}</b>\n"
                    f"🔢 Kod: <code>{code}</code>\n"
                    f"📊 Holat: {status}\n"
                    f"🎞 Qismlar: <b>{ep_count} ta</b>\n"
                    f"🖼 Poster: {poster_str}",
                    call.message.chat.id, call.message.message_id, reply_markup=kb
                )
            except Exception:
                pass
            return

        # Ongoing serialga yangi qism qo'shish (paneldan)
        if data.startswith("ongoing_addepisode_") and is_admin(user_id):
            code = data.replace("ongoing_addepisode_", "")
            movie = get_movie(code)
            if not movie:
                bot.answer_callback_query(call.id, "❌ Serial topilmadi!")
                return
            existing = get_series_episodes_count(code)
            next_ep = existing + 1
            set_state(user_id, 'add_episode_file', {
                'code': code,
                'title': movie['title'],
                'episode_num': next_ep
            })
            bot.answer_callback_query(call.id, f"➕ {next_ep}-qism qo'shilmoqda...")
            bot.send_message(
                user_id,
                f"➕ <b>{movie['title']}</b>\n\n"
                f"Hozir: <b>{existing} qism</b> mavjud\n\n"
                f"📹 <b>{next_ep}-qism</b> faylini yuboring (video):"
            )
            return

    except Exception as e:
        logger.error(f"❌ Callback xatosi: {e}")
        try:
            bot.answer_callback_query(call.id, "❌ Xatolik yuz berdi!")
        except Exception:
            pass

# ╔══════════════════════════════════════════════════════════════╗
# ║              📢 KANALGA POST YUBORISH                        ║
# ╚══════════════════════════════════════════════════════════════╝

def _send_post_to_channel_ongoing(movie: dict, channel: str, episode_num: int, total: int):
    """Ongoing serialga yangi qism qo'shilganda kanalga eski poster bilan avtomatik post"""
    try:
        bot_info = bot.get_me()
        bot_username = bot_info.username
        code = movie['code']
        poster_id = movie.get('poster_file_id') or ''
        if not poster_id:
            return
        deep_link = f"https://t.me/{bot_username}?start=movie_{code}"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("▶️ Ko'rish / Watch", url=deep_link))
        caption = (
            f"🔔 <b>Yangi qism chiqdi!</b>\n\n"
            f"🎌 <b>{movie['title']}</b>\n\n"
            f"▶️ <b>{episode_num}-qism</b> qo'shildi!\n"
            f"🎞 Jami: <b>{total} qism</b>\n\n"
            f"👇 Ko'rish uchun bosing!"
        )
        bot.send_photo(channel, photo=poster_id, caption=caption, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"_send_post_to_channel_ongoing xatosi: {e}")


def _send_post_to_channel(admin_id: int, movie: dict, channel: str, photo_file_id: Optional[str] = None):
    """Kanalga rasm+tugma yoki faqat tugmali post yuborish"""
    try:
        bot_info = bot.get_me()
        bot_username = bot_info.username
        code = movie['code']
        deep_link = f"https://t.me/{bot_username}?start=movie_{code}"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📥 YUKLAB OLISH 🎬", url=deep_link))

        desc = movie.get('description') or ''
        cat = movie.get('category', '')
        if movie.get('is_series'):
            ep_count = get_series_episodes_count(code)
            caption = (
                f"🎌 <b>{movie['title']}</b>\n\n"
                + (f"📝 {desc}\n" if desc else "")
                + (f"📂 Janr: {cat}\n" if cat else "")
                + f"🎞 Qismlar: <b>{ep_count} ta</b>\n\n"
                f"👇 Ko'rish uchun bosing!"
            )
        else:
            caption = (
                f"🎬 <b>{movie['title']}</b>\n\n"
                + (f"📝 {desc}\n" if desc else "")
                + (f"📂 Janr: {cat}\n" if cat else "")
                + "\n👇 Ko'rish uchun bosing!"
            )

        if photo_file_id:
            bot.send_photo(channel, photo=photo_file_id, caption=caption, reply_markup=keyboard)
            set_movie_poster(code, photo_file_id)
        else:
            bot.send_message(channel, caption, reply_markup=keyboard)

        bot.send_message(
            admin_id,
            f"✅ <b>Post kanalga yuborildi!</b>\n\n"
            f"📢 Kanal: <code>{channel}</code>\n"
            f"🎌 Anime: <b>{movie['title']}</b>"
        )
    except Exception as e:
        bot.send_message(admin_id, f"❌ Post yuborishda xato: {e}")


@bot.message_handler(content_types=['photo'], func=lambda m: True)
def photo_handler(message):
    """Rasm qabul qilish — postchannel uchun"""
    user_id = message.from_user.id
    state = get_state(user_id)

    # Broadcast uchun rasm
    if state and state.get('state') == 'broadcast' and is_admin(user_id):
        clear_state(user_id)
        do_broadcast(user_id, message)
        return

    if state and state.get('state') == 'post_channel_photo' and is_admin(user_id):
        data = state.get('data', {})
        code = data.get('code')
        channel = data.get('channel')
        clear_state(user_id)
        photo_file_id = message.photo[-1].file_id  # eng yuqori sifat
        movie = get_movie(code)
        if not movie:
            bot.send_message(user_id, "❌ Anime topilmadi!")
            return
        _send_post_to_channel(user_id, movie, channel, photo_file_id=photo_file_id)


# ╔══════════════════════════════════════════════════════════════╗
# ║              📢 BROADCAST FUNKSIYASI                         ║
# ╚══════════════════════════════════════════════════════════════╝

def do_broadcast(admin_id: int, source_message):
    """Barcha foydalanuvchilarga har qanday xabar (matn, rasm, video, audio...)ni yuborish"""
    users = get_all_users()
    total = len(users)
    success = 0
    failed = 0
    bot.send_message(admin_id, f"📢 <b>Broadcast boshlandi...</b>\n👥 Jami: <b>{total}</b>")
    for uid in users:
        try:
            bot.copy_message(
                chat_id=uid,
                from_chat_id=source_message.chat.id,
                message_id=source_message.message_id
            )
            success += 1
            time.sleep(0.05)
        except Exception as e:
            failed += 1
    bot.send_message(
        admin_id,
        f"✅ <b>Broadcast yakunlandi!</b>\n\n✅ Muvaffaqiyatli: <b>{success}</b>\n❌ Xatolik: <b>{failed}</b>"
    )

# ╔══════════════════════════════════════════════════════════════╗
# ║                    🚀 ASOSIY FUNKSIYA                        ║
# ╚══════════════════════════════════════════════════════════════╝

def main():
    global BOT_USERNAME
    logger.info("🚀 ANIMEBUM BOT ishga tushmoqda...")

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
        logger.critical("❌ BOT_TOKEN o'rnatilmagan!")
        return

    # Keep-alive server ni fon threadida ishga tushirish
    t = threading.Thread(target=run_keep_alive, daemon=True)
    t.start()
    logger.info("🌐 Keep-alive server ishga tushdi!")

    create_database()

    # Agar hech kanal yo'q bo'lsa — @animebum_1 ni avtomatik qo'shish
    conn = sqlite3.connect('kino_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM channels')
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            'INSERT OR IGNORE INTO channels (channel_id, channel_name, channel_url, added_by) VALUES (?, ?, ?, ?)',
            ('@animebum_1', 'Asosiy kanal', 'https://t.me/animebum_1', ADMIN_IDS[0])
        )
        conn.commit()
        logger.info("✅ Default kanal qo'shildi: @animebum_1")
    conn.close()

    try:
        me = bot.get_me()
        BOT_USERNAME = me.username or BOT_USERNAME
        logger.info(f"🤖 Bot ulandi: @{BOT_USERNAME} ({me.first_name})")
    except Exception as e:
        logger.critical(f"❌ Bot ulanishda xato: {e}")
        return

    # Backup kanalidan ma'lumotlarni tiklash (hosting restart bo'lganda)
    logger.info("🔄 Backup ma'lumotlari tiklanmoqda...")
    if restore_data():
        logger.info("✅ Ma'lumotlar muvaffaqiyatli tiklandi!")
    else:
        logger.info("ℹ️ Tiklash o'tkazib yuborildi (backup yo'q yoki sozlanmagan).")

    logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")
    logger.info(f"👑 Admin ID lari: {ADMIN_IDS}")

    while True:
        try:
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=30,
                logger_level=logging.INFO,
                skip_pending=True
            )
        except KeyboardInterrupt:
            logger.info("👋 Bot to'xtatildi.")
            break
        except Exception as e:
            logger.error(f"⚠️ Bot xatosi: {e}. 5 soniyadan keyin qayta urinib ko'rilmoqda...")
            time.sleep(5)

if __name__ == '__main__':
    main()
