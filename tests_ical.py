from requests import Session
from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import json
import icalendar
import threading
import time
from flask import Flask, Response, request, render_template_string
from zoneinfo import ZoneInfo
from hashlib import sha256
import sqlite3
from functools import lru_cache
from dotenv import load_dotenv
import os

load_dotenv()

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
            print(f"Tests data: {json.dumps(self.tests, indent=2)}")
            
            for test in self.tests:
                try: 
                    event = icalendar.Event()
                    
                    utc_date = datetime.fromisoformat(test['Datum'].replace('Z', '+00:00'))
                    local_date = utc_date.astimezone(ZoneInfo("Europe/Budapest"))
                    print(f"Processing test: {test['TantargyNeve']} on {local_date}") 
                    
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
                    print(f"Successfully added event: {test['TantargyNeve']} on {local_date.date()}")
                except Exception as e:
                    print(f"Error adding test to calendar: {e}")
        
        ical_data = cal.to_ical()
        print(f"Generated iCal data: {ical_data}")
        
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

user_manager = UserManager()
user_manager.setup_database()

@app.route('/')
def home():
    schools = user_manager.get_schools_cached()
    school_data = json.dumps([{
        'code': school['azonosito'],
        'name': school['nev'],
        'city': school['telepules'],
        'search': f"{school['nev'].lower()} {school['telepules'].lower()} {school['azonosito'].lower()}"
    } for school in schools])
    
    return render_template_string('''
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Kréta Naptár Generátor</title>
            <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='favicon.ico') }}">
            <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
            <script id="school-data" type="application/json">{{ school_data|safe }}</script>
            <script src="{{ url_for('static', filename='scripts.js') }}"></script>
        </head>
        <body>
            <div class="container">
                <h1>Kréta Naptár Generátor</h1>
                <form method="post" action="/generate">
                    <div class="form-group">
                        <input type="text" name="username" placeholder="Oktatási azonosító" required>
                    </div>
                    <div class="form-group">
                        <input type="password" name="password" placeholder="Jelszó" required>
                    </div>
                    <div class="form-group search-container">
                        <input type="text" id="schoolSearch" placeholder="Iskola keresése..." autocomplete="off">
                        <input type="hidden" id="institute_code" name="institute_code" required>
                        <div id="schoolDropdown" class="dropdown"></div>
                    </div>
                    <button type="submit">Naptár Generálása</button>
                </form>
            </div>
        </body>
        </html>
    ''', school_data=school_data)

@app.route('/generate', methods=['POST'])
def generate():
    username = request.form['username']
    password = request.form['password']
    institute_code = request.form['institute_code']
    
    try:
        user_id = user_manager.add_user(username, password, institute_code)
        calendar_url = f"https://kreta.herowarriors.hu/calendar/{user_id}/tests.ics"
        
        return render_template_string('''
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Naptár Létrehozva</title>
                <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='favicon.ico') }}">
                <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
                <script>
                    function copyToClipboard(text) {
                        navigator.clipboard.writeText(text).then(function() {
                            // Show the toast message
                            var toast = document.getElementById("toast");
                            toast.classList.add("show");
                            setTimeout(function(){ toast.classList.remove("show"); }, 2000);
                        }, function(err) {
                            console.error('Could not copy text: ', err);
                        });
                    }
                </script>
            </head>
            <body>
                <div class="result-container">
                    <h1>Naptár Létrehozva!</h1>
                    <p>A naptár URL-ed elkészült. Kattints a linkre a másoláshoz:</p>
                    <div class="url-container">
                        <a href="#" onclick="copyToClipboard('{{ url }}'); return false;">{{ url }}</a>
                    </div>
                    <p>Add hozzá ezt az URL-t a naptár alkalmazásodhoz a dolgozatok követéséhez.</p>
                    <a href="/" class="back-button">Új Naptár Generálása</a>
                    <div id="toast">Kimásolva!</div>
                </div>
            </body>
            </html>
        ''', url=calendar_url)
    except Exception as e:
        error_message = "Hibás felhasználónév vagy jelszó. Kérlek ellenőrizd az adataidat!"
        if "Login failed" in str(e):
            error_message = "Hibás felhasználónév vagy jelszó. Kérlek ellenőrizd az adataidat!"
        elif "User not found" in str(e):
            error_message = "A felhasználó nem található. Kérlek próbáld újra!"
        else:
            error_message = "Váratlan hiba történt. Kérlek próbáld újra később!"
            
        return render_template_string('''
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Hiba</title>
                <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='favicon.ico') }}">
                <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
            </head>
            <body>
                <div class="result-container">
                    <h1>Hiba</h1>
                    <p>{{ error }}</p>
                    <a href="/" class="back-button">Próbáld Újra</a>
                </div>
            </body>
            </html>
        ''', error=error_message), 400

@app.route('/calendar/<user_id>/tests.ics')
def get_user_calendar(user_id):
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

if __name__ == '__main__':
    try:
        print("Starting Flask server...")
        app.run(port=8080, host='0.0.0.0', debug=False)
    except Exception as e:
        print(f"Error starting server: {e}")