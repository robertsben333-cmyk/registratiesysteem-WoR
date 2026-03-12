import sys
import os
import json
import random
import string
import sqlite3
from flask import Flask

# Resolve base directory: next to .exe when packaged, otherwise project root
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COACH_SETTINGS_PATH = os.path.join(BASE_DIR, 'coach_settings.json')

GEMEENTEN = [
    'Beesel', 'Bergen', 'Echt-Susteren', 'Gennep', 'Horst aan de Maas',
    'Leudal', 'Maasgouw', 'Nederweert', 'Roerdalen', 'Roermond',
    'Venlo', 'Venray', 'Weert',
]


def get_coach_settings():
    """Return coach settings dict, or empty dict if not set."""
    if os.path.exists(COACH_SETTINGS_PATH):
        try:
            with open(COACH_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _generate_coach_id():
    """Generate a unique coach ID: 5 digits + 1 uppercase letter, e.g. '38291B'."""
    digits = ''.join(random.choices(string.digits, k=5))
    letter = random.choice(string.ascii_uppercase)
    return digits + letter


def save_coach_settings(naam, gemeente, uren_per_week):
    existing = get_coach_settings()
    coach_id = existing.get('coach_id') or _generate_coach_id()
    with open(COACH_SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            'coach_id': coach_id,
            'naam': naam,
            'gemeente': gemeente,
            'uren_per_week': uren_per_week,
        }, f, ensure_ascii=False)

DB_PATH = os.path.join(BASE_DIR, 'wor_data.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sw_columns(prefix='sw_q'):
    """Generate 44 spinnenweb question columns (INTEGER)."""
    return '\n'.join(f'    {prefix}{i} INTEGER,' for i in range(1, 45))


def init_db():
    conn = get_db()
    sw = _sw_columns()
    conn.executescript(f"""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voornaam TEXT NOT NULL,
            aangemaakt_op DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vragenlijst_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            verwijzer TEXT,
            huisartsenpraktijk TEXT,
            geslacht TEXT,
            leeftijdscategorie TEXT,
            woonsituatie TEXT,
            werkstatus TEXT,
            eerder_hulp TEXT,
{sw}
            huisartsbezoeken INTEGER,
            ingevuld_op DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vragenlijst_2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            hoofdreden TEXT,
            uitstroom_naar TEXT,
            geslacht TEXT,
            leeftijdscategorie TEXT,
            woonsituatie TEXT,
            werkstatus TEXT,
            datum_verwijzing DATE,
            datum_intake DATE,
            datum_start_activiteit DATE,
            contactmomenten_ff REAL,
            contactmomenten_tel REAL,
            uitval_ja_nee TEXT,
            uitval_reden TEXT,
            doorverwezen_ja_nee TEXT,
            doorverwezen_naar TEXT,
            terugkoppeling TEXT,
            ingevuld_op DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vragenlijst_3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            continuering TEXT,
            reden_stoppen TEXT,
            behoefte_ondersteuning TEXT,
            tevredenheidscijfer INTEGER,
{sw}
            huisartsbezoeken INTEGER,
            ingevuld_op DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def create_app():
    # Locate templates/static relative to this file (works both dev and packaged)
    if getattr(sys, 'frozen', False):
        # PyInstaller extracts to sys._MEIPASS
        template_folder = os.path.join(sys._MEIPASS, 'app', 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'app', 'static')
    else:
        template_folder = os.path.join(os.path.dirname(__file__), 'templates')
        static_folder = os.path.join(os.path.dirname(__file__), 'static')

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.secret_key = 'wor-registratie-2026'

    init_db()

    from .routes import bp
    app.register_blueprint(bp)

    return app
