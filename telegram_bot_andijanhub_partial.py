import logging
import sqlite3
import re
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

LANGUAGE, VERIFY_CHANNEL, MAIN_MENU, NOTIFICATION_PREFS, SETTINGS = range(5)
CHANNEL_USERNAME = "AndijanHub"
CHANNEL_LINK = "https://t.me/AndijanHub"
DB_NAME = 'bot_database.db'

NOTIFICATION_MESSAGES = {
    'en': {
        'ec': "Hey! You have a new opportunity on extracurricular activities.",
        'edu': "Hey! You have a new educational opportunity.",
        'int': "Hey! You have a new internship opportunity.",
        'olym': "Hey! You have a new Olympiad opportunity.",
        'all': "Hey! You have a new opportunity!",
        'button': "Click here to go to the post!"
    },
    'ru': {
        'ec': "Привет! У вас появилась новая возможность для внеклассных мероприятий.",
        'edu': "Привет! У вас появилась новая образовательная возможность.",
        'int': "Привет! У вас появилась новая возможность для стажировки.",
        'olym': "Привет! У вас появилась новая возможность участвовать в олимпиаде.",
        'all': "Привет! У вас появилась новая возможность!",
        'button': "Нажмите здесь, чтобы перейти к посту!"
    },
    'uz': {
        'ec': "Salom! Sizda maktabdandasturi uchun yangi imkoniyat mavjud.",
        'edu': "Salom! Sizda yangi ta'lim imkoniyati mavjud.",
        'int': "Salom! Sizda yangi stajirovka imkoniyati mavjud.",
        'olym': "Salom! Sizda yangi olimpiada imkoniyati mavjud.",
        'all': "Salom! Sizda yangi imkoniyat mavjud!",
        'button': "Postga o'tish uchun shu erni bosing!"
    }
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT,
            last_verified REAL,
            verification_cooldown REAL,
            is_verified INTEGER DEFAULT 0,
            internships INTEGER DEFAULT 1,
            extracurriculars INTEGER DEFAULT 1,
            educational_opportunities INTEGER DEFAULT 1,
            notified_posts TEXT DEFAULT '',
            olympiads INTEGER DEFAULT 1
        )
    ''')
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN olympiads INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

def get_user_data(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'user_id': result[0],
            'language': result[1],
            'last_verified': result[2],
            'verification_cooldown': result[3],
            'is_verified': bool(result[4]),
            'internships': bool(result[5]),
            'extracurriculars': bool(result[6]),
            'educational_opportunities': bool(result[7]),
            'notified_posts': result[8] or '',
            'olympiads': bool(result[9]) if len(result) > 9 else True
        }
    return None

def update_user_data(user_id, updates):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone()
    if exists:
        set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
        query = f"UPDATE users SET {set_clause} WHERE user_id = ?"
        values = list(updates.values()) + [user_id]
    else:
        columns = ['user_id'] + list(updates.keys())
        placeholders = ', '.join(['?'] * len(columns))
        query = f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})"
        values = [user_id] + list(updates.values())
    cursor.execute(query, values)
    conn.commit()
    conn.close()

def mark_post_notified(user_id, post_id):
    user_data = get_user_data(user_id)
    if user_data:
        notified_posts = user_data['notified_posts'].split(',')
        if str(post_id) not in notified_posts:
            notified_posts.append(str(post_id))
            update_user_data(user_id, {'notified_posts': ','.join(notified_posts)})

def is_post_notified(user_id, post_id):
    user_data = get_user_data(user_id)
    return str(post_id) in (user_data['notified_posts'] or '').split(',') if user_data else False
