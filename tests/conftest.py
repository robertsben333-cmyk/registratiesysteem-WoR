import sqlite3
import pytest
from unittest.mock import patch


SCHEMA = """
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
    sw_q1 INTEGER, sw_q2 INTEGER, sw_q3 INTEGER, sw_q4 INTEGER,
    sw_q5 INTEGER, sw_q6 INTEGER, sw_q7 INTEGER, sw_q8 INTEGER,
    sw_q9 INTEGER, sw_q10 INTEGER, sw_q11 INTEGER, sw_q12 INTEGER,
    sw_q13 INTEGER, sw_q14 INTEGER, sw_q15 INTEGER,
    sw_q16 INTEGER, sw_q17 INTEGER, sw_q18 INTEGER, sw_q19 INTEGER,
    sw_q20 INTEGER, sw_q21 INTEGER, sw_q22 INTEGER,
    sw_q23 INTEGER, sw_q24 INTEGER, sw_q25 INTEGER, sw_q26 INTEGER,
    sw_q27 INTEGER, sw_q28 INTEGER, sw_q29 INTEGER, sw_q30 INTEGER,
    sw_q31 INTEGER, sw_q32 INTEGER, sw_q33 INTEGER, sw_q34 INTEGER,
    sw_q35 INTEGER, sw_q36 INTEGER, sw_q37 INTEGER,
    sw_q38 INTEGER, sw_q39 INTEGER, sw_q40 INTEGER, sw_q41 INTEGER,
    sw_q42 INTEGER, sw_q43 INTEGER, sw_q44 INTEGER,
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
    sw_q1 INTEGER, sw_q2 INTEGER, sw_q3 INTEGER, sw_q4 INTEGER,
    sw_q5 INTEGER, sw_q6 INTEGER, sw_q7 INTEGER, sw_q8 INTEGER,
    sw_q9 INTEGER, sw_q10 INTEGER, sw_q11 INTEGER, sw_q12 INTEGER,
    sw_q13 INTEGER, sw_q14 INTEGER, sw_q15 INTEGER,
    sw_q16 INTEGER, sw_q17 INTEGER, sw_q18 INTEGER, sw_q19 INTEGER,
    sw_q20 INTEGER, sw_q21 INTEGER, sw_q22 INTEGER,
    sw_q23 INTEGER, sw_q24 INTEGER, sw_q25 INTEGER, sw_q26 INTEGER,
    sw_q27 INTEGER, sw_q28 INTEGER, sw_q29 INTEGER, sw_q30 INTEGER,
    sw_q31 INTEGER, sw_q32 INTEGER, sw_q33 INTEGER, sw_q34 INTEGER,
    sw_q35 INTEGER, sw_q36 INTEGER, sw_q37 INTEGER,
    sw_q38 INTEGER, sw_q39 INTEGER, sw_q40 INTEGER, sw_q41 INTEGER,
    sw_q42 INTEGER, sw_q43 INTEGER, sw_q44 INTEGER,
    huisartsbezoeken INTEGER,
    ingevuld_op DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / 'test.db')
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def db(db_path):
    """Patch app.models.get_db to use the temp test database."""
    def make_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    with patch('app.models.get_db', make_conn):
        yield make_conn()
