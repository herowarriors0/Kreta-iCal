from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import sqlite3
from functools import wraps
from flask import session, redirect, url_for, request
import os
from pathlib import Path
from datetime import datetime

GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8080/oauth2callback"],
    }
}

def setup_google_auth_db():
    with sqlite3.connect('users.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS google_auth (
                google_id TEXT PRIMARY KEY,
                kreta_user_id TEXT,
                email TEXT,
                FOREIGN KEY (kreta_user_id) REFERENCES users(id)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS test_preferences (
                kreta_user_id TEXT,
                test_id TEXT,
                enabled BOOLEAN DEFAULT 1,
                PRIMARY KEY (kreta_user_id, test_id),
                FOREIGN KEY (kreta_user_id) REFERENCES users(id)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS custom_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kreta_user_id TEXT,
                subject TEXT,
                date DATE,
                topic TEXT,
                test_type TEXT,
                weight REAL,
                teacher TEXT,
                FOREIGN KEY (kreta_user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

def get_google_flow():
    host = request.host_url.rstrip('/')
    
    config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{host}/oauth2callback"],
        }
    }
    
    flow = Flow.from_client_config(
        config,
        scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email'],
        redirect_uri=f"{host}/oauth2callback"
    )
    return flow

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'google_id' not in session:
            return redirect(url_for('dashboard_login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_by_google_id(google_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        result = conn.execute(
            'SELECT k.*, g.email FROM users k '
            'JOIN google_auth g ON k.id = g.kreta_user_id '
            'WHERE g.google_id = ?',
            (google_id,)
        ).fetchone()
        return dict(result) if result else None

def link_google_account(google_id, email, kreta_user_id):
    with sqlite3.connect('users.db') as conn:
        conn.execute(
            'INSERT OR REPLACE INTO google_auth (google_id, kreta_user_id, email) VALUES (?, ?, ?)',
            (google_id, kreta_user_id, email)
        )
        conn.commit()

def get_test_preferences(kreta_user_id):
    with sqlite3.connect('users.db') as conn:
        prefs = conn.execute(
            'SELECT test_id, enabled FROM test_preferences WHERE kreta_user_id = ?',
            (kreta_user_id,)
        ).fetchall()
        return {test_id: enabled for test_id, enabled in prefs}

def update_test_preference(kreta_user_id, test_id, enabled):
    with sqlite3.connect('users.db') as conn:
        conn.execute(
            'INSERT OR REPLACE INTO test_preferences (kreta_user_id, test_id, enabled) VALUES (?, ?, ?)',
            (kreta_user_id, test_id, enabled)
        )
        conn.commit()

def add_custom_test(kreta_user_id, subject, date, topic, test_type, weight=None, teacher=None):
    with sqlite3.connect('users.db') as conn:
        conn.execute(
            'INSERT INTO custom_tests (kreta_user_id, subject, date, topic, test_type, weight, teacher) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (kreta_user_id, subject, date, topic, test_type, weight, teacher)
        )
        conn.commit()

def get_custom_tests(kreta_user_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        current_date = datetime.now().strftime('%Y-%m-%d')
        tests = conn.execute(
            'SELECT * FROM custom_tests WHERE kreta_user_id = ? AND date >= ?',
            (kreta_user_id, current_date)
        ).fetchall()
        return [dict(test) for test in tests]

def cleanup_expired_tests():
    with sqlite3.connect('users.db') as conn:
        current_date = datetime.now().strftime('%Y-%m-%d')
        conn.execute('DELETE FROM custom_tests WHERE date < ?', (current_date,))
        conn.commit() 