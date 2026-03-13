import calendar
from datetime import date

from . import get_db

# ── Dashboard constants ───────────────────────────────────────────────────────

SIGNALERING_ACHTERUITGANG_DREMPEL = -1.0


def get_periode_range(periode):
    """Return (start_date, end_date) as date objects, or (None, None) for 'alles'.

    periode: 'kwartaal' | 'jaar' | 'alles'
    """
    today = date.today()
    if periode == 'kwartaal':
        q = (today.month - 1) // 3          # 0-indexed quarter
        start_month = q * 3 + 1
        end_month = start_month + 2
        start = date(today.year, start_month, 1)
        end = date(today.year, end_month, calendar.monthrange(today.year, end_month)[1])
        return start, end
    if periode == 'jaar':
        return date(today.year, 1, 1), date(today.year, 12, 31)
    return None, None                        # 'alles'


# ── Spinnenweb helpers ────────────────────────────────────────────────────────

SW_QUESTIONS = {
    'Lichaamsfuncties': [
        (1,  'Ik voel mij gezond'),
        (2,  'Ik voel mij fit'),
        (3,  'Ik heb geen klachten en pijn'),
        (4,  'Ik slaap goed'),
        (5,  'Ik eet goed'),
        (6,  'Ik ben tevreden over mijn seksualiteit'),
        (7,  'Ik herstel snel na inspanning'),
        (8,  'Ik kan makkelijk bewegen'),
    ],
    'Mentaal welbevinden': [
        (9,  'Ik kan dingen goed onthouden'),
        (10, 'Ik kan mij goed concentreren'),
        (11, 'Ik kan zien, horen, praten, lezen'),
        (12, 'Ik voel mij vrolijk'),
        (13, 'Ik accepteer mijzelf zoals ik ben'),
        (14, 'Ik zoek naar oplossingen om moeilijke situaties te veranderen'),
        (15, 'Ik heb controle over mijn leven'),
    ],
    'Zingeving': [
        (16, 'Ik heb een zinvol leven'),
        (17, "Ik heb 's morgens zin in de dag"),
        (18, 'Ik heb idealen die ik graag wil bereiken'),
        (19, 'Ik heb vertrouwen in mijn eigen toekomst'),
        (20, 'Ik accepteer het leven zoals het komt'),
        (21, 'Ik ben dankbaar voor wat het leven mij biedt'),
        (22, 'Ik wil mijn hele leven blijven leren'),
    ],
    'Kwaliteit van leven': [
        (23, 'Ik geniet van mijn leven'),
        (24, 'Ik ben gelukkig'),
        (25, 'Ik zit lekker in mijn vel'),
        (26, 'Ik ervaar evenwicht in mijn leven'),
        (27, 'Ik voel mij veilig'),
        (28, 'Ik ben tevreden over de intimiteit in mijn leven'),
        (29, 'Ik ben tevreden over waar ik woon en met wie'),
        (30, 'Ik heb genoeg geld om mijn rekeningen te betalen'),
    ],
    'Meedoen': [
        (31, 'Ik heb goed contact met andere mensen'),
        (32, 'Andere mensen nemen mij serieus'),
        (33, 'Ik heb mensen met wie ik leuke dingen kan doen'),
        (34, 'Ik heb mensen die mij steunen als dat nodig is'),
        (35, 'Ik heb het gevoel dat ik erbij hoor in mijn omgeving'),
        (36, 'Ik heb werk of andere bezigheden die ik zinvol vind'),
        (37, 'Ik ben geïnteresseerd in wat er in de maatschappij gebeurt'),
    ],
    'Dagelijks functioneren': [
        (38, 'Ik kan goed voor mijzelf zorgen'),
        (39, 'Ik weet wat ik wel kan en wat ik niet kan'),
        (40, 'Ik weet hoe ik mijn gezondheid kan verzorgen'),
        (41, 'Ik kan goed plannen wat ik op een dag moet doen'),
        (42, 'Ik kan goed omgaan met het geld dat ik elke maand krijg'),
        (43, 'Ik kan werken of vrijwilligerswerk doen'),
        (44, 'Ik weet hoe ik zonodig hulp kan krijgen van officiële instanties'),
    ],
}


SW_COLS = [f'sw_q{i}' for i in range(1, 45)]


def calc_sw_scores(row):
    """Calculate per-dimension averages from a DB row. Returns dict."""
    scores = {}
    for dim, questions in SW_QUESTIONS.items():
        vals = [row[f'sw_q{n}'] for (n, _) in questions if row[f'sw_q{n}'] is not None]
        scores[dim] = round(sum(vals) / len(vals), 1) if vals else None
    return scores


# ── Clients ───────────────────────────────────────────────────────────────────

def get_all_clients():
    conn = get_db()
    rows = conn.execute("SELECT * FROM clients ORDER BY aangemaakt_op DESC").fetchall()
    conn.close()
    return rows


def get_client(client_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    conn.close()
    return row


def get_clients_by_first_name(first_name):
    """Return all clients whose first name (before any space) matches first_name (case-insensitive)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM clients WHERE voornaam = ? OR voornaam LIKE ? COLLATE NOCASE",
        (first_name, first_name + ' %')
    ).fetchall()
    conn.close()
    return rows


def add_client(voornaam):
    conn = get_db()
    cur = conn.execute("INSERT INTO clients (voornaam) VALUES (?)", (voornaam.strip(),))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def delete_client(client_id):
    conn = get_db()
    for tbl in ('vragenlijst_1', 'vragenlijst_2', 'vragenlijst_3'):
        conn.execute(f"DELETE FROM {tbl} WHERE client_id = ?", (client_id,))
    conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()


# ── Generic VL helpers ────────────────────────────────────────────────────────

def _get_vl(table, client_id):
    conn = get_db()
    row = conn.execute(f"SELECT * FROM {table} WHERE client_id = ?", (client_id,)).fetchone()
    conn.close()
    return row


def _upsert_vl(table, client_id, data):
    """Insert or update a vragenlijst row for a client."""
    conn = get_db()
    existing = conn.execute(f"SELECT id FROM {table} WHERE client_id = ?", (client_id,)).fetchone()
    if existing:
        sets = ', '.join(f"{k} = :{k}" for k in data)
        conn.execute(f"UPDATE {table} SET {sets}, ingevuld_op = CURRENT_TIMESTAMP WHERE client_id = :client_id",
                     {**data, 'client_id': client_id})
    else:
        cols = 'client_id, ' + ', '.join(data.keys())
        vals = ':client_id, ' + ', '.join(f':{k}' for k in data)
        conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({vals})", {**data, 'client_id': client_id})
    conn.commit()
    conn.close()


# ── Vragenlijst 1 ─────────────────────────────────────────────────────────────

def get_vl1(client_id):
    return _get_vl('vragenlijst_1', client_id)


def save_vl1(client_id, data):
    _upsert_vl('vragenlijst_1', client_id, data)


# ── Vragenlijst 2 ─────────────────────────────────────────────────────────────

def get_vl2(client_id):
    return _get_vl('vragenlijst_2', client_id)


def save_vl2(client_id, data):
    _upsert_vl('vragenlijst_2', client_id, data)


# ── Vragenlijst 3 ─────────────────────────────────────────────────────────────

def get_vl3(client_id):
    return _get_vl('vragenlijst_3', client_id)


def save_vl3(client_id, data):
    _upsert_vl('vragenlijst_3', client_id, data)


# ── Export ────────────────────────────────────────────────────────────────────

def get_all_for_export():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            c.id, c.voornaam, c.aangemaakt_op,
            v1.verwijzer, v1.geslacht, v1.leeftijdscategorie,
            v1.woonsituatie, v1.werkstatus, v1.eerder_hulp,
            v1.huisartsbezoeken AS ha_bezoeken_vl1,
            v2.hoofdreden, v2.uitstroom_naar,
            v2.datum_verwijzing, v2.datum_intake, v2.datum_start_activiteit,
            v2.contactmomenten_ff, v2.contactmomenten_tel,
            v2.uitval_ja_nee, v2.uitval_reden,
            v2.doorverwezen_ja_nee, v2.doorverwezen_naar,
            v2.terugkoppeling,
            v3.continuering, v3.reden_stoppen,
            v3.behoefte_ondersteuning, v3.tevredenheidscijfer,
            v3.huisartsbezoeken AS ha_bezoeken_vl3
        FROM clients c
        LEFT JOIN vragenlijst_1 v1 ON v1.client_id = c.id
        LEFT JOIN vragenlijst_2 v2 ON v2.client_id = c.id
        LEFT JOIN vragenlijst_3 v3 ON v3.client_id = c.id
        ORDER BY c.aangemaakt_op DESC
    """).fetchall()

    # Also fetch spinnenweb scores for VL1 and VL3
    sw_vl1 = {r['client_id']: r for r in conn.execute(
        "SELECT client_id, " + ', '.join(SW_COLS) + " FROM vragenlijst_1"
    ).fetchall()}
    sw_vl3 = {r['client_id']: r for r in conn.execute(
        "SELECT client_id, " + ', '.join(SW_COLS) + " FROM vragenlijst_3"
    ).fetchall()}

    conn.close()
    return rows, sw_vl1, sw_vl3
