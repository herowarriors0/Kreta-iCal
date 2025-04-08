from requests import Session
from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import json
import icalendar
import threading
import time
from flask import Flask, Response, request, render_template, session, redirect, url_for, jsonify
from zoneinfo import ZoneInfo
from hashlib import sha256
import sqlite3
from functools import lru_cache
from dotenv import load_dotenv
import os
from google_auth import (
    setup_google_auth_db, get_google_flow, login_required,
    get_user_by_google_id, link_google_account,
    get_test_preferences, update_test_preference,
    add_custom_test, get_custom_tests, cleanup_expired_tests
)
from google.oauth2.credentials import Credentials

load_dotenv()

if os.getenv('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def login(UserName: str, Password: str, InstituteCode: str) -> dict:
    with Session() as session:
        url = "https://idp.e-kreta.hu/Account/Login?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fprompt%3Dlogin%26nonce%3DwylCrqT4oN6PPgQn2yQB0euKei9nJeZ6_ffJ-VpSKZU%26response_type%3Dcode%26code_challenge_method%3DS256%26scope%3Dopenid%2520email%2520offline_access%2520kreta-ellenorzo-webapi.public%2520kreta-eugyintezes-webapi.public%2520kreta-fileservice-webapi.public%2520kreta-mobile-global-webapi.public%2520kreta-dkt-webapi.public%2520kreta-ier-webapi.public%26code_challenge%3DHByZRRnPGb-Ko_wTI7ibIba1HQ6lor0ws4bcgReuYSQ%26redirect_uri%3Dhttps%253A%252F%252Fmobil.e-kreta.hu%252Fellenorzo-student%252Fprod%252Foauthredirect%26client_id%3Dkreta-ellenorzo-student-mobile-ios%26state%3Dkreten_student_mobile%26suppressed_prompt%3Dlogin"
        response = session.request("GET", url)

        soup = bs(response.text, 'html.parser')
        rvt = soup.find('input', {'name': '__RequestVerificationToken'})['value']

        payload = {
            "ReturnUrl": "/connect/authorize/callback?prompt=login&nonce=wylCrqT4oN6PPgQn2yQB0euKei9nJeZ6_ffJ-VpSKZU&response_type=code&code_challenge_method=S256&scope=openid%20email%20offline_access%20kreta-ellenorzo-webapi.public%20kreta-eugyintezes-webapi.public%20kreta-fileservice-webapi.public%20kreta-mobile-global-webapi.public%20kreta-dkt-webapi.public%20kreta-ier-webapi.public&code_challenge=HByZRRnPGb-Ko_wTI7ibIba1HQ6lor0ws4bcgReuYSQ&redirect_uri=https%3A%2F%2Fmobil.e-kreta.hu%2Fellenorzo-student%2Fprod%2Foauthredirect&client_id=kreta-ellenorzo-student-mobile-ios&state=kreten_student_mobile&suppressed_prompt=login",
            "IsTemporaryLogin": False,
            "UserName": UserName,
            "Password": Password,
            "InstituteCode": InstituteCode,
            "loginType": "InstituteLogin",
            "__RequestVerificationToken": rvt
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        response = session.request("POST", "https://idp.e-kreta.hu/account/login", headers=headers, data=payload, allow_redirects=False)
        if response.status_code != 200:
            raise Exception("Login failed check your credentials")

        response = session.request("GET", "https://idp.e-kreta.hu/connect/authorize/callback?prompt=login&nonce=wylCrqT4oN6PPgQn2yQB0euKei9nJeZ6_ffJ-VpSKZU&response_type=code&code_challenge_method=S256&scope=openid%20email%20offline_access%20kreta-ellenorzo-webapi.public%20kreta-eugyintezes-webapi.public%20kreta-fileservice-webapi.public%20kreta-mobile-global-webapi.public%20kreta-dkt-webapi.public%20kreta-ier-webapi.public&code_challenge=HByZRRnPGb-Ko_wTI7ibIba1HQ6lor0ws4bcgReuYSQ&redirect_uri=https%3A%2F%2Fmobil.e-kreta.hu%2Fellenorzo-student%2Fprod%2Foauthredirect&client_id=kreta-ellenorzo-student-mobile-ios&state=kreten_student_mobile&suppressed_prompt=login", allow_redirects=False)
        url = urlparse(response.headers['location'])
        code = parse_qs(url.query)['code'][0]

        data = {
            "code": code,
            "code_verifier": "DSpuqj_HhDX4wzQIbtn8lr8NLE5wEi1iVLMtMK0jY6c",
            "redirect_uri": "https://mobil.e-kreta.hu/ellenorzo-student/prod/oauthredirect",
            "client_id": "kreta-ellenorzo-student-mobile-ios",
            "grant_type": "authorization_code"
        }
        response = session.request("POST", "https://idp.e-kreta.hu/connect/token", data=data)

    return response.json()

def refresh_token(refresh_token: str, institute_code: str) -> dict:
    with Session() as session:
        payload = {
            "institute_code": institute_code,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": "kreta-ellenorzo-student-mobile-ios"
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        response = session.post("https://idp.e-kreta.hu/connect/token", data=payload, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.text}")
            
        return response.json()

def get_announced_tests(access_token: str, institute_code: str) -> list:
    with Session() as session:
        date_from = datetime.now().strftime("%Y-%m-%d")
        date_to = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        url = f"https://{institute_code}.e-kreta.hu/ellenorzo/v3/sajat/BejelentettSzamonkeresek"
        url += f"?datumTol={date_from}&datumIg={date_to}"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'apiKey': os.getenv('API_KEY') 
        }
        
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to get tests: {response.text}")
            
        return response.json()

def get_schools():
    with Session() as session:
        url = "https://kretaglobalapi.e-kreta.hu/intezmenyek/kreta/publikus"
        headers = {
            'api-version': 'v1'
        }
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return []

class TestManager:
    def __init__(self, user_manager):
        self.tests = []
        self.last_update = None
        self.update_lock = threading.Lock()
        self.existing_test_ids = set()
        self.user_manager = user_manager
        
    def start_periodic_updates(self, user_id, institute_code):
        self.user_id = user_id
        self.institute_code = institute_code
        
        self._do_update()
        
    def _do_update(self):
        try:
            with self.update_lock:
                print("Getting access token...")
                access_token = self.user_manager.get_access_token(self.user_id)
                print("Getting tests...")
                new_tests = get_announced_tests(access_token, self.institute_code)
                
                current_test_ids = set()
                updated_tests = []
                
                for test in new_tests:
                    test_id = f"{test['Datum']}-{test['TantargyNeve']}-{test['Temaja']}"
                    current_test_ids.add(test_id)
                    
                    if test_id not in self.existing_test_ids:
                        updated_tests.append(test)
                        self.existing_test_ids.add(test_id)
                
                for test in self.tests:
                    test_id = f"{test['Datum']}-{test['TantargyNeve']}-{test['Temaja']}"
                    if test_id not in current_test_ids:
                        updated_tests.append(test)
                
                self.tests = updated_tests
                self.last_update = datetime.now()
                print(f"Found {len(self.tests)} tests (including preserved ones)")
                
                for test in self.tests:
                    utc_date = datetime.fromisoformat(test['Datum'].replace('Z', '+00:00'))
                    local_date = utc_date.astimezone(ZoneInfo("Europe/Budapest"))
                    print(f"Test: {test['TantargyNeve']} on {local_date.strftime('%Y-%m-%d %H:%M')} (Budapest time)")
        except Exception as e:
            print(f"Error updating tests: {e}")
    
    def generate_ical(self):
        cal = icalendar.Calendar()
        cal.add('prodid', '-//Kreta Test Calendar//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        
        with self.update_lock:
            print(f"Generating calendar with {len(self.tests)} tests")
            
            preferences = get_test_preferences(self.user_id)
            
            for test in self.tests:
                try: 
                    test_id = f"{test['Datum']}-{test['TantargyNeve']}-{test['Temaja']}"
                    
                    if not preferences.get(test_id, True):
                        print(f"Skipping disabled test: {test['TantargyNeve']}")
                        continue
                    
                    event = icalendar.Event()
                    
                    utc_date = datetime.fromisoformat(test['Datum'].replace('Z', '+00:00'))
                    local_date = utc_date.astimezone(ZoneInfo("Europe/Budapest"))
                    
                    event.add('summary', icalendar.vText(f"{test['TantargyNeve']} - dolgozat"))
                    event.add('dtstart', local_date.date(), parameters={'VALUE': 'DATE'})
                    event.add('dtend', (local_date.date() + timedelta(days=1)), parameters={'VALUE': 'DATE'})
                    
                    description = f"{test['Temaja']}\n{test['Modja']['Leiras']}\n{test['RogzitoTanarNeve']}"
                    event.add('description', icalendar.vText(description))
                    
                    now = datetime.now(ZoneInfo("UTC"))
                    event.add('dtstamp', now)
                    event.add('created', now)
                    event.add('last-modified', now)
                    
                    event_id = f"{local_date.strftime('%Y%m%d')}-{test['TantargyNeve'].replace(' ', '_')}@kreta"
                    event.add('uid', event_id)
                    
                    cal.add_component(event)
                    print(f"Successfully added KRÉTA test: {test['TantargyNeve']} on {local_date.date()}")
                except Exception as e:
                    print(f"Error adding KRÉTA test to calendar: {e}")
            
            custom_tests = get_custom_tests(self.user_id)
            for test in custom_tests:
                try:
                    event = icalendar.Event()
                    
                    local_date = datetime.strptime(test['date'], '%Y-%m-%d')
                    
                    summary = f"{test['subject']} - {test['test_type']}"
                    if test['weight']:
                        summary += f" ({test['weight']})"
                    
                    event.add('summary', icalendar.vText(summary))
                    event.add('dtstart', local_date.date(), parameters={'VALUE': 'DATE'})
                    event.add('dtend', (local_date.date() + timedelta(days=1)), parameters={'VALUE': 'DATE'})
                    
                    description = test['topic']
                    if test['teacher']:
                        description += f"\n{test['teacher']}"
                    event.add('description', icalendar.vText(description))
                    
                    now = datetime.now(ZoneInfo("UTC"))
                    event.add('dtstamp', now)
                    event.add('created', now)
                    event.add('last-modified', now)
                    
                    event_id = f"{local_date.strftime('%Y%m%d')}-custom-{test['id']}@kreta"
                    event.add('uid', event_id)
                    
                    cal.add_component(event)
                    print(f"Successfully added custom test: {test['subject']} on {local_date.date()}")
                except Exception as e:
                    print(f"Error adding custom test to calendar: {e}")
        
        ical_data = cal.to_ical()
        lines = ical_data.split(b'\n')
        formatted_lines = [line.rstrip(b'\r\n') + b'\r\n' for line in lines if line]
        return b''.join(formatted_lines) + b'\r\n'

class UserManager:
    def __init__(self):
        self.test_managers = {}
        self.setup_database()
        self.schools = []
        self.refresh_all_users()
        
    def setup_database(self):
        with sqlite3.connect('users.db') as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    refresh_token TEXT,
                    institute_code TEXT,
                    last_refresh INTEGER
                )
            ''')
            
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'username' in columns:
                conn.execute('''
                    CREATE TABLE users_new (
                        id TEXT PRIMARY KEY,
                        refresh_token TEXT,
                        institute_code TEXT,
                        last_refresh INTEGER
                    )
                ''')
                
                conn.execute('''
                    INSERT INTO users_new (id, refresh_token, institute_code, last_refresh)
                    SELECT id, refresh_token, institute_code, last_refresh FROM users
                ''')
                
                conn.execute('DROP TABLE users')
                conn.execute('ALTER TABLE users_new RENAME TO users')
            
            conn.commit()
    
    def generate_user_id(self, username, institute_code):
        unique_string = f"{username}:{institute_code}".encode()
        return sha256(unique_string).hexdigest()[:16]
    
    def add_user(self, username, password, institute_code):
        user_id = self.generate_user_id(username, institute_code)
        
        with sqlite3.connect('users.db') as conn:
            existing = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
            if not existing:
                auth_data = login(username, password, institute_code)
                conn.execute(
                    'INSERT INTO users (id, refresh_token, institute_code, last_refresh) VALUES (?, ?, ?, ?)',
                    (user_id, auth_data['refresh_token'], institute_code, int(time.time()))
                )
        
        if user_id not in self.test_managers:
            tm = TestManager(self)
            tm.start_periodic_updates(user_id, institute_code)
            self.test_managers[user_id] = tm
            
        return user_id

    def get_access_token(self, user_id):
        with sqlite3.connect('users.db') as conn:
            user = conn.execute('SELECT refresh_token, institute_code, last_refresh FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                raise Exception("User not found")
                
            token, institute_code, last_refresh = user
            
            try:
                auth_data = refresh_token(token, institute_code)
                conn.execute(
                    'UPDATE users SET refresh_token = ?, last_refresh = ? WHERE id = ?',
                    (auth_data['refresh_token'], int(time.time()), user_id)
                )
                return auth_data['access_token']
            except Exception as e:
                raise Exception(f"Failed to refresh token: {e}")

    @lru_cache(maxsize=1)
    def get_schools_cached(self):
        if not self.schools:
            self.schools = get_schools()
        return self.schools

    def refresh_all_users(self):
        """Refresh all users' test managers when the script starts"""
        print("Refreshing all users' calendars...")
        with sqlite3.connect('users.db') as conn:
            users = conn.execute('SELECT id, institute_code FROM users').fetchall()
            
        for user_id, institute_code in users:
            try:
                if user_id not in self.test_managers:
                    tm = TestManager(self)
                    tm.start_periodic_updates(user_id, institute_code)
                    self.test_managers[user_id] = tm
                    print(f"Created new TestManager for user {user_id}")
            except Exception as e:
                print(f"Error refreshing user {user_id}: {e}")

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

user_manager = UserManager()
user_manager.setup_database()

setup_google_auth_db()

@app.route('/')
def home():
    schools = user_manager.get_schools_cached()
    school_data = json.dumps([{
        'code': school['azonosito'],
        'name': school['nev'],
        'city': school['telepules'],
        'search': f"{school['nev'].lower()} {school['telepules'].lower()} {school['azonosito'].lower()}"
    } for school in schools])
    
    return render_template('home.html', school_data=school_data)

@app.route('/generate', methods=['POST'])
def generate():
    username = request.form['username']
    password = request.form['password']
    institute_code = request.form['institute_code']
    
    try:
        user_id = user_manager.add_user(username, password, institute_code)
        calendar_url = f"https://kreta.herowarriors.hu/calendar/{user_id}/tests.ics"
        session['kreta_user_id'] = user_id
        return render_template('result.html', url=calendar_url)
    except Exception as e:
        error_message = "Hibás felhasználónév vagy jelszó. Kérlek ellenőrizd az adataidat!"
        if "Login failed" in str(e):
            error_message = "Hibás felhasználónév vagy jelszó. Kérlek ellenőrizd az adataidat!"
        elif "User not found" in str(e):
            error_message = "A felhasználó nem található. Kérlek próbáld újra!"
        else:
            error_message = "Váratlan hiba történt. Kérlek próbáld újra később!"
            
        return render_template('result.html', error=error_message), 400

@app.route('/calendar/<user_id>/tests.ics')
def get_user_calendar(user_id):
    cleanup_expired_tests()
    tm = user_manager.test_managers.get(user_id)
    if not tm:
        return "Calendar not found", 404
        
    try:
        calendar_data = tm.generate_ical()
        response = Response(
            calendar_data,
            mimetype='text/calendar',
            headers={
                'Content-Type': 'text/calendar; charset=utf-8',
                'Content-Disposition': 'attachment; filename=tests.ics',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        return response
    except Exception as e:
        print(f"Error generating calendar: {e}")
        return str(e), 500

@app.route('/dashboard-login')
def dashboard_login():
    return render_template('dashboard_login.html')

@app.route('/link-google')
def link_google():
    if 'kreta_user_id' not in session:
        return redirect(url_for('home'))
    
    flow = get_google_flow()
    session['linking'] = True
    authorization_url, state = flow.authorization_url(access_type='offline')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/login-with-google')
def login_with_google():
    flow = get_google_flow()
    authorization_url, state = flow.authorization_url(access_type='offline')
    session['state'] = state
    session['linking'] = False
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    if 'state' not in session:
        return redirect(url_for('home'))
        
    flow = get_google_flow()
    
    try:
        flow.fetch_token(
            authorization_response=request.url,
            state=session['state']
        )
        
        credentials = flow.credentials
        user_info = flow.oauth2session.get(
            'https://www.googleapis.com/oauth2/v1/userinfo'
        ).json()
        
        google_id = user_info['id']
        email = user_info['email']
        
        if session.get('linking'):
            if 'kreta_user_id' in session:
                link_google_account(google_id, email, session['kreta_user_id'])
                session['google_id'] = google_id
                return redirect(url_for('dashboard'))
            return redirect(url_for('home'))
        else:
            user = get_user_by_google_id(google_id)
            if user:
                session['google_id'] = google_id
                session['kreta_user_id'] = user['id'] 
                return redirect(url_for('dashboard'))
            return redirect(url_for('dashboard_login', error='not_linked'))
            
    except Exception as e:
        print(f"OAuth error: {e}")
        return redirect(url_for('dashboard_login', error='oauth_failed'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('kreta_user_id')
    if not user_id or user_id not in user_manager.test_managers:
        return redirect(url_for('dashboard_login'))
    
    tm = user_manager.test_managers[user_id]
    preferences = get_test_preferences(user_id)
    
    tests = []
    
    for test in tm.tests:
        test_id = f"{test['Datum']}-{test['TantargyNeve']}-{test['Temaja']}"
        test['enabled'] = preferences.get(test_id, True)
        test['id'] = test_id
        test['is_custom'] = False
        tests.append(test)
    
    custom_tests = get_custom_tests(user_id)
    for test in custom_tests:
        test['is_custom'] = True
        tests.append(test)
    
    tests.sort(key=lambda x: x.get('Datum', x.get('date')))
    
    return render_template('dashboard.html', tests=tests)

@app.route('/api/toggle-test', methods=['POST'])
@login_required
def toggle_test():
    data = request.get_json()
    test_id = data.get('test_id')
    enabled = data.get('enabled', True)
    
    if not test_id:
        return jsonify({'error': 'Missing test_id'}), 400
    
    update_test_preference(session['kreta_user_id'], test_id, enabled)
    return jsonify({'success': True})

@app.route('/api/add-test', methods=['POST'])
@login_required
def add_test():
    data = request.get_json()
    
    try:
        add_custom_test(
            session['kreta_user_id'],
            data['subject'],
            data['date'],
            data['topic'],
            data['test_type'],
            data.get('weight'),
            data.get('teacher')
        )
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error adding custom test: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/api/edit-test/<int:test_id>', methods=['PUT'])
@login_required
def edit_test(test_id):
    data = request.get_json()
    
    try:
        with sqlite3.connect('users.db') as conn:
            test = conn.execute(
                'SELECT * FROM custom_tests WHERE id = ? AND kreta_user_id = ?',
                (test_id, session['kreta_user_id'])
            ).fetchone()
            
            if not test:
                return jsonify({'error': 'Test not found'}), 404
            
            conn.execute('''
                UPDATE custom_tests 
                SET subject = ?, date = ?, topic = ?, test_type = ?, weight = ?, teacher = ?
                WHERE id = ?
            ''', (
                data['subject'],
                data['date'],
                data['topic'],
                data['test_type'],
                data.get('weight'),
                data.get('teacher'),
                test_id
            ))
            conn.commit()
            
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error editing custom test: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/delete-test/<int:test_id>', methods=['DELETE'])
@login_required
def delete_test(test_id):
    try:
        with sqlite3.connect('users.db') as conn:
            result = conn.execute(
                'DELETE FROM custom_tests WHERE id = ? AND kreta_user_id = ?',
                (test_id, session['kreta_user_id'])
            )
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'error': 'Test not found'}), 404
                
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting custom test: {e}")
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    try:
        print("Starting Flask server...")
        app.run(port=8080, host='localhost', debug=False)
    except Exception as e:
        print(f"Error starting server: {e}")