import sys
import os
import json
import random
import shutil
import string
import sqlite3
from flask import Flask
from .version import APP_NAME, APP_VERSION, UPDATE_MANIFEST_URL

# Resolve install directory: next to .exe when packaged, otherwise project root
if getattr(sys, 'frozen', False):
    INSTALL_DIR = os.path.dirname(sys.executable)
else:
    INSTALL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_storage_dir():
    """Store user data outside the install folder for packaged builds."""
    if getattr(sys, 'frozen', False):
        appdata_root = os.environ.get('APPDATA')
        if appdata_root:
            return os.path.join(appdata_root, APP_NAME)
        return os.path.join(os.path.expanduser('~'), APP_NAME)
    return INSTALL_DIR


STORAGE_DIR = _get_storage_dir()
COACH_SETTINGS_PATH = os.path.join(STORAGE_DIR, 'coach_settings.json')
DB_PATH = os.path.join(STORAGE_DIR, 'wor_data.db')
LOCAL_UPDATE_MANIFEST_PATH = os.path.join(INSTALL_DIR, 'latest.json')
if getattr(sys, 'frozen', False):
    BUNDLED_UPDATE_MANIFEST_PATH = os.path.join(sys._MEIPASS, 'latest.json')
else:
    BUNDLED_UPDATE_MANIFEST_PATH = LOCAL_UPDATE_MANIFEST_PATH

GEMEENTEN = [
    'Beesel', 'Bergen', 'Echt-Susteren', 'Gennep', 'Horst aan de Maas',
    'Leudal', 'Maasgouw', 'Nederweert', 'Roerdalen', 'Roermond',
    'Venlo', 'Venray', 'Weert',
]


def _ensure_storage_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)


def _migrate_legacy_file(filename):
    legacy_path = os.path.join(INSTALL_DIR, filename)
    target_path = os.path.join(STORAGE_DIR, filename)
    if legacy_path == target_path:
        return
    if os.path.exists(target_path) or not os.path.exists(legacy_path):
        return
    try:
        shutil.copy2(legacy_path, target_path)
    except OSError:
        pass


def prepare_storage():
    _ensure_storage_dir()
    if getattr(sys, 'frozen', False):
        for filename in ('coach_settings.json', 'wor_data.db'):
            _migrate_legacy_file(filename)


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
    app.config['APP_VERSION'] = APP_VERSION
    app.config['APP_STORAGE_DIR'] = STORAGE_DIR
    app.config['UPDATE_MANIFEST_URL'] = os.environ.get(
        'WOR_UPDATE_MANIFEST_URL',
        UPDATE_MANIFEST_URL
    ).strip()
    app.config['UPDATE_MANIFEST_PATH'] = LOCAL_UPDATE_MANIFEST_PATH
    app.config['UPDATE_MANIFEST_BUNDLED_PATH'] = BUNDLED_UPDATE_MANIFEST_PATH
    prepare_storage()
    init_db()

    from .routes import bp
    app.register_blueprint(bp)

    return app
