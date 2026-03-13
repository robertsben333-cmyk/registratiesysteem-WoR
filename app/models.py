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


# ── Dashboard aggregation ─────────────────────────────────────────────────────

def _empty_dashboard_data():
    dim_names = list(SW_QUESTIONS.keys())
    return {
        'kpis': {'totaal': 0, 'actief': 0, 'afgerond': 0, 'uitgevallen': 0, 'gem_tevredenheid': None},
        'sw_vl1': [None] * 6,
        'sw_vl3': [None] * 6,
        'sw_delta': [None] * 6,
        'sw_n': 0,
        'sw_labels': dim_names,
        'verwijzers': [],
        'huisartsen': [],
        'signalen': [],
        'demografie': {'geslacht': [], 'leeftijd': []},
        'uitstroom': {'bestemmingen': [], 'doorverwezen_ja': 0, 'doorverwezen_nee': 0},
        'contactmomenten': {'gem_ff': None, 'gem_tel': None},
    }


def get_dashboard_data(periode='alles'):
    """Aggregate all dashboard data for the given period.

    Returns a dict matching the template context contract in the design spec.
    """
    from collections import Counter
    from datetime import timedelta

    start, end = get_periode_range(periode)
    conn = get_db()

    # ── 1. Filtered clients ──────────────────────────────────────────
    if start and end:
        clients = conn.execute(
            "SELECT * FROM clients WHERE date(aangemaakt_op) >= ? AND date(aangemaakt_op) <= ?",
            (start.isoformat(), end.isoformat())
        ).fetchall()
    else:
        clients = conn.execute("SELECT * FROM clients").fetchall()

    client_ids = [c['id'] for c in clients]
    if not client_ids:
        conn.close()
        return _empty_dashboard_data()

    ph = ','.join('?' * len(client_ids))

    # ── 2. VL existence + data lookup ───────────────────────────────
    vl1_ids = {r['client_id'] for r in conn.execute(
        f"SELECT client_id FROM vragenlijst_1 WHERE client_id IN ({ph})", client_ids
    ).fetchall()}

    vl2_rows = {r['client_id']: r for r in conn.execute(
        f"SELECT * FROM vragenlijst_2 WHERE client_id IN ({ph})", client_ids
    ).fetchall()}

    vl3_ids = {r['client_id'] for r in conn.execute(
        f"SELECT client_id FROM vragenlijst_3 WHERE client_id IN ({ph})", client_ids
    ).fetchall()}

    # ── 3. KPIs ─────────────────────────────────────────────────────
    uitgevallen_ids = {cid for cid, r in vl2_rows.items() if r['uitval_ja_nee'] == 'ja'}
    totaal = len(client_ids)
    uitgevallen = len(uitgevallen_ids)
    afgerond = sum(
        1 for cid in client_ids
        if cid not in uitgevallen_ids
        and cid in vl1_ids
        and cid in vl2_rows
        and cid in vl3_ids
    )
    actief = totaal - uitgevallen - afgerond

    tv_vals = [
        r['tevredenheidscijfer'] for r in conn.execute(
            f"SELECT tevredenheidscijfer FROM vragenlijst_3 "
            f"WHERE client_id IN ({ph}) AND tevredenheidscijfer IS NOT NULL",
            client_ids
        ).fetchall()
    ]
    gem_tv = round(sum(tv_vals) / len(tv_vals), 1) if tv_vals else None

    kpis = {
        'totaal': totaal,
        'actief': actief,
        'afgerond': afgerond,
        'uitgevallen': uitgevallen,
        'gem_tevredenheid': gem_tv,
    }

    # ── 4. Spinnenweb ────────────────────────────────────────────────
    sw_cols_str = ', '.join(SW_COLS)
    vl1_sw = {r['client_id']: r for r in conn.execute(
        f"SELECT client_id, {sw_cols_str} FROM vragenlijst_1 WHERE client_id IN ({ph})", client_ids
    ).fetchall()}
    vl3_sw = {r['client_id']: r for r in conn.execute(
        f"SELECT client_id, {sw_cols_str} FROM vragenlijst_3 WHERE client_id IN ({ph})", client_ids
    ).fetchall()}

    both_ids = set(vl1_sw.keys()) & set(vl3_sw.keys())
    sw_n = len(both_ids)
    dim_names = list(SW_QUESTIONS.keys())
    sw_vl1, sw_vl3, sw_delta = [], [], []

    for dim, questions in SW_QUESTIONS.items():
        q_nums = [n for n, _ in questions]
        vl1_vals, vl3_vals = [], []
        for cid in both_ids:
            r1, r3 = vl1_sw[cid], vl3_sw[cid]
            v1 = [r1[f'sw_q{n}'] for n in q_nums if r1[f'sw_q{n}'] is not None]
            v3 = [r3[f'sw_q{n}'] for n in q_nums if r3[f'sw_q{n}'] is not None]
            if v1:
                vl1_vals.append(sum(v1) / len(v1))
            if v3:
                vl3_vals.append(sum(v3) / len(v3))
        avg1 = round(sum(vl1_vals) / len(vl1_vals), 2) if vl1_vals else None
        avg3 = round(sum(vl3_vals) / len(vl3_vals), 2) if vl3_vals else None
        delta = round(avg3 - avg1, 2) if (avg1 is not None and avg3 is not None) else None
        sw_vl1.append(avg1)
        sw_vl3.append(avg3)
        sw_delta.append(delta)

    # ── 5. Verwijzers ────────────────────────────────────────────────
    vl1_ref_rows = conn.execute(
        f"SELECT verwijzer, huisartsenpraktijk FROM vragenlijst_1 WHERE client_id IN ({ph})",
        client_ids
    ).fetchall()
    verw_counts = Counter(r['verwijzer'] for r in vl1_ref_rows if r['verwijzer'])
    verwijzers = [{'naam': k, 'count': v} for k, v in verw_counts.most_common()]
    ha_counts = Counter(r['huisartsenpraktijk'] for r in vl1_ref_rows if r['huisartsenpraktijk'])
    huisartsen = [{'naam': k, 'count': v} for k, v in ha_counts.most_common()]

    # ── 6. Signalering ───────────────────────────────────────────────
    today = date.today()
    drempel_datum = today - timedelta(days=90)
    signalen_wachtend, signalen_uitgevallen, signalen_achteruitgang = [], [], []

    for c in clients:
        cid = c['id']
        naam = c['voornaam']
        if cid in vl3_ids:
            link = f'/client/{cid}/vragenlijst/3/view'
        elif cid in vl2_rows:
            link = f'/client/{cid}/vragenlijst/2/view'
        else:
            link = f'/client/{cid}/vragenlijst/1/view'

        if cid not in vl2_rows and c['aangemaakt_op']:
            aangemaakt = date.fromisoformat(c['aangemaakt_op'][:10])
            if aangemaakt <= drempel_datum:
                maanden = (today.year - aangemaakt.year) * 12 + today.month - aangemaakt.month
                signalen_wachtend.append({
                    'naam': naam,
                    'reden': f'Wacht al {maanden} maand{"en" if maanden != 1 else ""} op opvolging',
                    'link': link,
                    'type': 'wachtend',
                })

        if cid in uitgevallen_ids:
            signalen_uitgevallen.append({
                'naam': naam, 'reden': 'Uitgevallen', 'link': link, 'type': 'uitgevallen',
            })

        if cid in both_ids:
            scores1 = calc_sw_scores(vl1_sw[cid])
            scores3 = calc_sw_scores(vl3_sw[cid])
            for dim in dim_names:
                s1, s3 = scores1.get(dim), scores3.get(dim)
                if s1 is not None and s3 is not None and (s3 - s1) < SIGNALERING_ACHTERUITGANG_DREMPEL:
                    signalen_achteruitgang.append({
                        'naam': naam,
                        'reden': f'{dim}: {s3 - s1:+.1f}',
                        'link': link,
                        'type': 'achteruitgang',
                    })
                    break  # one signal per client

    signalen = signalen_wachtend + signalen_uitgevallen + signalen_achteruitgang

    # ── 7. Demografie ────────────────────────────────────────────────
    vl1_demo = conn.execute(
        f"SELECT geslacht, leeftijdscategorie FROM vragenlijst_1 WHERE client_id IN ({ph})",
        client_ids
    ).fetchall()
    geslacht_counts = Counter(r['geslacht'] for r in vl1_demo if r['geslacht'])
    leeftijd_counts = Counter(r['leeftijdscategorie'] for r in vl1_demo if r['leeftijdscategorie'])
    demografie = {
        'geslacht': [{'label': k, 'count': v} for k, v in geslacht_counts.most_common()],
        'leeftijd': [{'label': k, 'count': v} for k, v in leeftijd_counts.most_common()],
    }

    # ── 8. Uitstroom ─────────────────────────────────────────────────
    vl2_list = list(vl2_rows.values())
    bestemming_counts = Counter(r['uitstroom_naar'] for r in vl2_list if r['uitstroom_naar'])
    dv_ja = sum(1 for r in vl2_list if r['doorverwezen_ja_nee'] == 'Ja')
    dv_nee = sum(1 for r in vl2_list if r['doorverwezen_ja_nee'] == 'Nee')
    uitstroom = {
        'bestemmingen': [{'label': k, 'count': v} for k, v in bestemming_counts.most_common()],
        'doorverwezen_ja': dv_ja,
        'doorverwezen_nee': dv_nee,
    }

    # ── 9. Contactmomenten ───────────────────────────────────────────
    ff_vals = [r['contactmomenten_ff'] for r in vl2_list if r['contactmomenten_ff'] is not None]
    tel_vals = [r['contactmomenten_tel'] for r in vl2_list if r['contactmomenten_tel'] is not None]
    contactmomenten = {
        'gem_ff': round(sum(ff_vals) / len(ff_vals), 1) if ff_vals else None,
        'gem_tel': round(sum(tel_vals) / len(tel_vals), 1) if tel_vals else None,
    }

    conn.close()
    return {
        'kpis': kpis,
        'sw_vl1': sw_vl1,
        'sw_vl3': sw_vl3,
        'sw_delta': sw_delta,
        'sw_n': sw_n,
        'sw_labels': dim_names,
        'verwijzers': verwijzers,
        'huisartsen': huisartsen,
        'signalen': signalen,
        'demografie': demografie,
        'uitstroom': uitstroom,
        'contactmomenten': contactmomenten,
    }
