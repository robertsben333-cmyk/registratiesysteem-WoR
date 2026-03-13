"""
seed_demo.py — Voegt 25 fictieve WoR-deelnemers in met realistische data.

Gebruik:
    python seed_demo.py          # voegt 25 demopatients in
    python seed_demo.py --clear  # verwijdert eerst alle bestaande demopatients
"""

import os
import sys
import sqlite3
import random
import argparse
from datetime import date, timedelta

# ── DB pad (zelfde logica als de app) ────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'wor_data.db')

# Als de app eerder gedraaid heeft als frozen exe, staat de DB in %APPDATA%
APPDATA_DB = None
appdata = os.environ.get('APPDATA')
if appdata:
    appdata_db_candidate = os.path.join(appdata, 'WoR Registratie', 'wor_data.db')
    if os.path.exists(appdata_db_candidate):
        APPDATA_DB = appdata_db_candidate

if APPDATA_DB:
    DB_PATH = APPDATA_DB

print(f"Database: {DB_PATH}")

# ── Helpers ───────────────────────────────────────────────────────────────────

def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()

def sw_scores_intake(base, noise=1):
    """Genereer 44 spinnenweb-scores voor intake (laag welbevinden)."""
    r = random.Random()
    scores = []
    for _ in range(44):
        val = base + r.randint(-noise, noise)
        scores.append(max(0, min(10, val)))
    return scores

def sw_scores_followup(intake_scores, improvement):
    """Genereer follow-up scores op basis van intake + verbetering."""
    r = random.Random()
    scores = []
    for s in intake_scores:
        delta = improvement + r.randint(-1, 1)
        val = s + delta
        scores.append(max(0, min(10, val)))
    return scores

def sw_dict(prefix, scores):
    return {f'{prefix}sw_q{i+1}': scores[i] for i in range(44)}

# ── Data tabellen ─────────────────────────────────────────────────────────────

VERWIJZERS = ['Huisarts', 'Huisarts', 'Huisarts', 'POH-GGZ', 'POH-GGZ',
              'Wijkteam', 'Maatschappelijk werker', 'Fysiotherapeut']

GESLACHTEN = ['Vrouw', 'Vrouw', 'Vrouw', 'Man', 'Man', 'Anders']

LEEFTIJDEN = ['31-45', '31-45', '46-60', '46-60', '61-75', '18-30', '75+']

WOONSITUATIES = ['Alleen', 'Alleen', 'Met partner', 'Met gezin', 'Anders']

WERKSTATUSSEN = [
    'Arbeidsongeschikt', 'Gepensioneerd', 'Betaald werk (loondienst of zelfstandig)',
    'Werkzoekend', 'Vrijwilligerswerk', 'Anders'
]

EERDER_HULP = ['Nee, eerste keer', 'Nee, eerste keer', 'Nee, eerste keer',
               'Ja, andere welzijnsondersteuning']

HOOFDREDENEN = [
    'Eenzaamheid', 'Eenzaamheid',
    'Somberheid of angst', 'Somberheid of angst',
    'Stress of overbelasting', 'Stress of overbelasting',
    'Verlies van zingeving',
    'Lichamelijke klachten met sociaal component',
    'Financiële zorgen',
]

UITSTROOM_NAAR = [
    'Sport/beweeggroep', 'Sport/beweeggroep',
    'Sociale activiteit', 'Sociale activiteit',
    'Vrijwilligerswerk', 'Cursus of workshop',
    'Geen vervolgaanbod',
    'Maatschappelijke dienstverlening',
]

CONTINUERING = ['ja_actief', 'ja_actief', 'ja_actief', 'ja_ander', 'nee_gestopt']

BEHOEFTE = [
    'Nee, het gaat goed', 'Nee, het gaat goed', 'Nee, het gaat goed',
    'Ja, ik zou graag opnieuw contact met de welzijnscoach',
    'Weet ik nog niet',
]

DOORVERWEZEN_NAAR = [
    'GGZ (basis of specialistisch)', 'Schuldhulpverlening',
    'Wijkteam of sociaal team', 'Anders',
]

UITVAL_REDENEN = [
    'Persoonlijke omstandigheden', 'Geen match met aanbod',
    'Onbereikbaar geworden',
]

# 25 fictieve namen (voornaam alleen, conform het systeem)
NAMEN = [
    # Vrouw
    'Anna', 'Maria', 'Lies', 'Sofie', 'Emma',
    'Petra', 'Inge', 'Nathalie', 'Tineke', 'Marianne',
    'Hanna', 'Linda', 'Roos', 'Judith', 'Caroline',
    # Man
    'Jan', 'Pieter', 'Thomas', 'Koen', 'Dirk',
    'Martijn', 'Lucas', 'Erik', 'Henk',
    # Neutraal
    'Alex',
]

# ── Seed logica ───────────────────────────────────────────────────────────────

def seed(conn, r):
    """Voeg 25 fictieve deelnemers in."""

    # Groep A: 16 volledig (VL1 + VL2 + VL3), toegevoegd 30-70 dagen geleden
    # Groep B: 6 met VL1 + VL2, toegevoegd 15-30 dagen geleden
    # Groep C: 3 met alleen VL1, toegevoegd 1-14 dagen geleden

    profiles = (
        [(n, 'ABC') for n in NAMEN[:16]] +
        [(n, 'AB')  for n in NAMEN[16:22]] +
        [(n, 'A')   for n in NAMEN[22:25]]
    )

    for naam, group in profiles:
        # Bepaal aanmaakdatum
        if group == 'ABC':
            created_days_ago = r.randint(45, 75)
        elif group == 'AB':
            created_days_ago = r.randint(18, 35)
        else:
            created_days_ago = r.randint(2, 14)

        created_date = date.today() - timedelta(days=created_days_ago)
        created_str = created_date.isoformat() + ' 09:00:00'

        cur = conn.execute(
            "INSERT INTO clients (voornaam, aangemaakt_op) VALUES (?, ?)",
            (naam, created_str)
        )
        cid = cur.lastrowid

        # ── VL1 ────────────────────────────────────────────────────────────
        intake_base = r.randint(2, 4)
        intake_sw = sw_scores_intake(intake_base, noise=2)

        uitval = r.random() < 0.1  # 10% kans op uitval
        geslacht = r.choice(GESLACHTEN)

        vl1 = {
            'verwijzer': r.choice(VERWIJZERS),
            'huisartsenpraktijk': 'Praktijk de Maasoever' if r.random() < 0.5 else '',
            'geslacht': geslacht,
            'leeftijdscategorie': r.choice(LEEFTIJDEN),
            'woonsituatie': r.choice(WOONSITUATIES),
            'werkstatus': r.choice(WERKSTATUSSEN),
            'eerder_hulp': r.choice(EERDER_HULP),
            'huisartsbezoeken': r.randint(3, 9),
            **sw_dict('', intake_sw),
        }
        _upsert(conn, 'vragenlijst_1', cid, vl1)

        if group in ('AB', 'ABC'):
            # ── VL2 ────────────────────────────────────────────────────────
            ref_date = created_date - timedelta(days=r.randint(7, 21))
            intake_date = created_date + timedelta(days=r.randint(1, 5))
            start_date = intake_date + timedelta(days=r.randint(7, 21))

            vl2 = {
                'hoofdreden': r.choice(HOOFDREDENEN),
                'uitstroom_naar': r.choice(UITSTROOM_NAAR),
                'geslacht': geslacht,
                'leeftijdscategorie': vl1['leeftijdscategorie'],
                'woonsituatie': vl1['woonsituatie'],
                'werkstatus': vl1['werkstatus'],
                'datum_verwijzing': ref_date.isoformat(),
                'datum_intake': intake_date.isoformat(),
                'datum_start_activiteit': start_date.isoformat(),
                'contactmomenten_ff': round(r.uniform(3.0, 9.0), 1),
                'contactmomenten_tel': round(r.uniform(0.5, 3.0), 1),
                'uitval_ja_nee': 'ja' if uitval else 'nee',
                'uitval_reden': r.choice(UITVAL_REDENEN) if uitval else None,
                'doorverwezen_ja_nee': 'ja' if r.random() < 0.25 else 'nee',
                'doorverwezen_naar': r.choice(DOORVERWEZEN_NAAR) if r.random() < 0.25 else None,
                'terugkoppeling': 'Cliënt heeft goed gereageerd op het aanbod.' if r.random() < 0.6 else None,
            }
            _upsert(conn, 'vragenlijst_2', cid, vl2)

        if group == 'ABC':
            # ── VL3 ────────────────────────────────────────────────────────
            improvement = r.randint(2, 4)
            followup_sw = sw_scores_followup(intake_sw, improvement)

            continuering = r.choice(CONTINUERING)
            reden_stoppen = r.choice(['Activiteit paste toch niet bij mij', 'Praktische belemmeringen (vervoer, kosten, tijd)']) \
                if continuering in ('nee_gestopt', 'nee_nooit') else None

            vl3 = {
                'continuering': continuering,
                'reden_stoppen': reden_stoppen,
                'behoefte_ondersteuning': r.choice(BEHOEFTE),
                'tevredenheidscijfer': r.randint(7, 9),
                'huisartsbezoeken': r.randint(0, 3),
                **sw_dict('', followup_sw),
            }
            _upsert(conn, 'vragenlijst_3', cid, vl3)

    conn.commit()
    print(f"OK: {len(profiles)} deelnemers aangemaakt.")


def _upsert(conn, table, client_id, data):
    # verwijder None-waarden niet — bewaar ze als NULL
    cols = 'client_id, ' + ', '.join(data.keys())
    vals = ':client_id, ' + ', '.join(f':{k}' for k in data)
    conn.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({vals})",
        {**data, 'client_id': client_id}
    )


def clear_demo(conn):
    """Verwijder alle clients waarvan de naam voorkomt in NAMEN."""
    placeholders = ','.join('?' for _ in NAMEN)
    rows = conn.execute(
        f"SELECT id FROM clients WHERE voornaam IN ({placeholders})", NAMEN
    ).fetchall()
    ids = [r[0] for r in rows]
    if not ids:
        print("Geen demodata gevonden om te verwijderen.")
        return
    for cid in ids:
        for tbl in ('vragenlijst_1', 'vragenlijst_2', 'vragenlijst_3'):
            conn.execute(f"DELETE FROM {tbl} WHERE client_id = ?", (cid,))
        conn.execute("DELETE FROM clients WHERE id = ?", (cid,))
    conn.commit()
    print(f"OK: {len(ids)} demopatients verwijderd.")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--clear', action='store_true', help='Verwijder demodata eerst')
    parser.add_argument('--seed', type=int, default=42, help='Random seed (default: 42)')
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Database niet gevonden: {DB_PATH}")
        print("Start de app eerst zodat de database aangemaakt wordt.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    r = random.Random(args.seed)

    if args.clear:
        clear_demo(conn)

    seed(conn, r)
    conn.close()
    print("Klaar. Start de app opnieuw om de demodata te zien.")
