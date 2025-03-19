# Kréta iCal - Iskolai dolgozatok naptárba szinkronizálása

## 📝 Leírás
Ez a projekt automatikusan szinkronizálja a Kréta rendszerben bejelentett dolgozatokat egy iCalendar (.ics) naptárba. A naptárat bármely modern naptáralkalmazás (pl. Google Calendar, Apple Calendar, Outlook) képes kezelni, így mindig naprakész leszel a közelgő dolgozataiddal kapcsolatban.

## 🌟 Főbb jellemzők
- Automatikus frissítés minden újraindításnál (a https://kreta.herowarriors.hu/ oldalt használva 12 óránként)
- Támogatja több felhasználó egyidejű használatát
- Offline működés és adatbázisban történő tárolás
- Egyszerű webes felület
- Iskola kereső integrálva

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

3. Hozd létre a .env fájlt:
```bash
echo "API_KEY=kreta_api_kulcs_ide" > .env
```

## ⚙️ Konfiguráció
1. A `tests_ical.py` fájl mellé helyezd el a `.env` fájlt a megadott API kulccsal
2. Az alkalmazás automatikusan létrehozza az adatbázist (users.db) az első indításkor

## 🚀 Használat
1. Indítsd el a szervert:
```bash
python tests_ical.py
```

2. Nyisd meg a böngésződben: `http://localhost:8080`

3. Add meg a Kréta belépési adataidat és válaszd ki az iskoládat

4. Másold ki a generált naptár URL-t és add hozzá a kedvenc naptáralkalmazásodhoz

## 🔒 Fontos megjegyzések
- A rendszer semmilyen formában nem tárolja a jelszavadat!
- A .env fájlt és az users.db-t soha ne oszd meg másokkal!

## 📜 Licenc
MIT Licenc - Részletekért lásd a LICENSE fájlt

⚠️ **FIGYELEM**: Ez egy nem hivatalos projekt, és semmilyen kapcsolatban nem áll a Kréta rendszer készítőivel. Használata kizárólag saját felelősségedre történik.
