# Kréta iCal - Iskolai dolgozatok naptárba szinkronizálása

## 📝 Leírás
Ez a projekt automatikusan szinkronizálja a Kréta rendszerben bejelentett dolgozatokat egy iCalendar (.ics) naptárba. A naptárat bármely modern naptáralkalmazás (pl. Google Calendar, Apple Calendar, Outlook) képes kezelni, így mindig naprakész leszel a közelgő dolgozataiddal kapcsolatban.

## 🌟 Főbb jellemzők
- Automatikus frissítés minden újraindításnál (a https://kreta.herowarriors.hu/ oldalt használva 12 óránként)
- Támogatja több felhasználó egyidejű használatát
- Offline működés és adatbázisban történő tárolás
- Egyszerű webes felület
- Iskola kereső integrálva
- Dashboard felület a dolgozatok kezeléséhez
- Google fiókkal történő bejelentkezés
- Egyéni dolgozatok hozzáadása
- Dolgozatok ki/bekapcsolása a naptárban
- Dolgozatok szerkesztése és törlése

## 📋 Előfeltételek
- Python 3.9+
- pip
- Szükséges Python csomagok:
  - Flask
  - requests
  - beautifulsoup4
  - icalendar
  - python-dotenv
  - zoneinfo
  - google-auth
  - google-auth-oauthlib

## 🛠️ Telepítés
1. Klónozd a repository-t:
```bash
git clone https://github.com/herowarriors0/Kreta-iCal.git
cd Kreta-iCal
```

2. Telepítsd a csomagokat:
```bash
pip install -r requirements.txt
```

3. Hozd létre a .env fájlt az alábbi tartalommal:
```bash
API_KEY=kreta_api_kulcs_ide
GOOGLE_CLIENT_ID=google_client_id_ide
GOOGLE_CLIENT_SECRET=google_client_secret_ide
```

## ⚙️ Konfiguráció
1. A `tests_ical.py` fájl mellé helyezd el a `.env` fájlt a szükséges környezeti változókkal
2. Az alkalmazás automatikusan létrehozza az adatbázist (users.db) az első indításkor
3. Google OAuth beállítása:
   - Hozz létre egy projektet a [Google Cloud Console](https://console.cloud.google.com/)-ban
   - Engedélyezd az OAuth 2.0 hitelesítést
   - Add hozzá az engedélyezett átirányítási URI-kat:
     - Fejlesztéshez: `http://localhost:8080/oauth2callback` (ha ezt szeretnéd használni, állítsd át a Flask környezetet fejlesztőire Windows: `set FLASK_ENV=development`, Unix/Linux: `export FLASK_ENV=development`)
   - Másold be a Client ID-t és Client Secret-et a .env fájlba

## 🚀 Használat
1. Indítsd el a szervert:
```bash
python tests_ical.py
```

2. Nyisd meg a böngésződben: `http://localhost:8080`

3. Add meg a Kréta belépési adataidat és válaszd ki az iskoládat

4. Másold ki a generált naptár URL-t és add hozzá a kedvenc naptáralkalmazásodhoz

5. A Dashboard-on keresztül:
   - Kapcsold össze Google fiókoddal a könnyebb bejelentkezéshez
   - Kezeld a dolgozataidat (ki/bekapcsolás, szerkesztés, törlés)
   - Adj hozzá egyéni dolgozatokat
   - Tekintsd meg az összes közelgő dolgozatot

## 🔒 Fontos megjegyzések
- A rendszer semmilyen formában nem tárolja a jelszavadat!
- A .env fájlt és az users.db-t soha ne oszd meg másokkal!
- A Google bejelentkezés biztonságos OAuth 2.0 protokollt használ
- Fejlesztői módban (`FLASK_ENV=development`) a Google bejelentkezés HTTP-n keresztül is működik

## 📜 Licenc
MIT Licenc - Részletekért lásd a LICENSE fájlt

⚠️ **FIGYELEM**: Ez egy nem hivatalos projekt, és semmilyen kapcsolatban nem áll a Kréta rendszer készítőivel. Használata kizárólag saját felelősségedre történik.
