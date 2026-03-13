from datetime import date
from app.models import get_dashboard_data, get_periode_range, SIGNALERING_ACHTERUITGANG_DREMPEL


def test_get_periode_range_alles():
    start, end = get_periode_range('alles')
    assert start is None
    assert end is None


def test_get_periode_range_jaar():
    start, end = get_periode_range('jaar')
    today = date.today()
    assert start == date(today.year, 1, 1)
    assert end == date(today.year, 12, 31)


def test_get_periode_range_kwartaal():
    start, end = get_periode_range('kwartaal')
    today = date.today()
    q = (today.month - 1) // 3
    assert start.month == q * 3 + 1
    assert start.day == 1
    assert start.year == today.year
    assert end.year == today.year
    assert end >= today  # end is always in the future or today within same quarter


def test_signalering_drempel_is_minus_one():
    assert SIGNALERING_ACHTERUITGANG_DREMPEL == -1.0


def test_get_dashboard_data_no_clients(db):
    data = get_dashboard_data('alles')
    assert data['kpis']['totaal'] == 0
    assert data['kpis']['actief'] == 0
    assert data['sw_n'] == 0
    assert data['signalen'] == []
    assert data['doorstroom']['gem_verwijzing_intake'] is None


def test_kpis_basic(db, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Insert 3 clients
    conn.execute("INSERT INTO clients (voornaam) VALUES ('Anna')")
    conn.execute("INSERT INTO clients (voornaam) VALUES ('Bert')")
    conn.execute("INSERT INTO clients (voornaam) VALUES ('Clara')")
    conn.commit()
    ids = [r['id'] for r in conn.execute("SELECT id FROM clients").fetchall()]
    # Anna: VL1 only (actief)
    conn.execute("INSERT INTO vragenlijst_1 (client_id, verwijzer) VALUES (?, 'Huisarts')", (ids[0],))
    # Bert: VL1 + VL2 uitgevallen
    conn.execute("INSERT INTO vragenlijst_1 (client_id, verwijzer) VALUES (?, 'Huisarts')", (ids[1],))
    conn.execute("INSERT INTO vragenlijst_2 (client_id, uitval_ja_nee) VALUES (?, 'ja')", (ids[1],))
    # Clara: all 3 (afgerond)
    conn.execute("INSERT INTO vragenlijst_1 (client_id, verwijzer) VALUES (?, 'Ziekenhuis')", (ids[2],))
    conn.execute("INSERT INTO vragenlijst_2 (client_id, uitval_ja_nee) VALUES (?, 'nee')", (ids[2],))
    conn.execute("INSERT INTO vragenlijst_3 (client_id, tevredenheidscijfer) VALUES (?, 8)", (ids[2],))
    conn.commit()
    conn.close()

    data = get_dashboard_data('alles')
    assert data['kpis']['totaal'] == 3
    assert data['kpis']['uitgevallen'] == 1
    assert data['kpis']['afgerond'] == 1
    assert data['kpis']['actief'] == 1
    assert data['kpis']['gem_tevredenheid'] == 8.0


def test_signaal_lang_wachtend(db, db_path):
    import sqlite3
    from datetime import timedelta
    conn = sqlite3.connect(db_path)
    old_date = (date.today() - timedelta(days=100)).isoformat()
    conn.execute(
        "INSERT INTO clients (voornaam, aangemaakt_op) VALUES ('Oud', ?)", (old_date,)
    )
    conn.commit()
    conn.close()

    data = get_dashboard_data('alles')
    assert any(s['type'] == 'wachtend' for s in data['signalen'])


def test_signaal_ondersteuningsbehoefte_via_vl3(db, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO clients (voornaam) VALUES ('Eva')")
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO vragenlijst_1 (client_id) VALUES (?)", (cid,))
    conn.execute(
        "INSERT INTO vragenlijst_3 (client_id, behoefte_ondersteuning) VALUES (?, ?)",
        (cid, 'Ja, ik zou graag opnieuw contact met de welzijnscoach')
    )
    conn.commit()
    conn.close()

    data = get_dashboard_data('alles')
    signaal = next((s for s in data['signalen'] if s['type'] == 'ondersteuning'), None)
    assert signaal is not None
    assert signaal['reden'] == 'Ja, ik zou graag opnieuw contact met de welzijnscoach'


def test_uitval_is_geen_aandacht_vereist_signaal(db, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO clients (voornaam) VALUES ('Finn')")
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO vragenlijst_1 (client_id) VALUES (?)", (cid,))
    conn.execute("INSERT INTO vragenlijst_2 (client_id, uitval_ja_nee) VALUES (?, 'ja')", (cid,))
    conn.commit()
    conn.close()

    data = get_dashboard_data('alles')
    assert not any(s['type'] == 'uitgevallen' for s in data['signalen'])


def test_signaal_achteruitgang(db, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO clients (voornaam) VALUES ('Demi')")
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # VL1: all 8s for Lichaamsfuncties (q1-q8), rest 7
    sw_vl1 = {f'sw_q{i}': 8 for i in range(1, 9)}
    sw_vl1.update({f'sw_q{i}': 7 for i in range(9, 45)})
    cols = ', '.join(sw_vl1.keys())
    vals = ', '.join('?' * len(sw_vl1))
    conn.execute(
        f"INSERT INTO vragenlijst_1 (client_id, {cols}) VALUES (?, {vals})",
        [cid] + list(sw_vl1.values())
    )
    # VL3: Lichaamsfuncties drops to 5 (delta = -3.0), rest 7
    sw_vl3 = {f'sw_q{i}': 5 for i in range(1, 9)}
    sw_vl3.update({f'sw_q{i}': 7 for i in range(9, 45)})
    cols3 = ', '.join(sw_vl3.keys())
    vals3 = ', '.join('?' * len(sw_vl3))
    conn.execute(
        f"INSERT INTO vragenlijst_3 (client_id, {cols3}) VALUES (?, {vals3})",
        [cid] + list(sw_vl3.values())
    )
    conn.commit()
    conn.close()

    data = get_dashboard_data('alles')
    assert any(s['type'] == 'achteruitgang' for s in data['signalen'])


def test_verwijzers_counted(db, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    for naam, verw in [('A', 'Huisarts'), ('B', 'Huisarts'), ('C', 'Ziekenhuis')]:
        conn.execute("INSERT INTO clients (voornaam) VALUES (?)", (naam,))
        cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO vragenlijst_1 (client_id, verwijzer, huisartsenpraktijk) VALUES (?, ?, 'Praktijk A')",
            (cid, verw)
        )
    conn.commit()
    conn.close()

    data = get_dashboard_data('alles')
    huisarts_entry = next((v for v in data['verwijzers'] if v['naam'] == 'Huisarts'), None)
    assert huisarts_entry is not None
    assert huisarts_entry['count'] == 2


def test_doorverwijzing_lowercase_values_counted(db, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO clients (voornaam) VALUES ('A')")
    cid1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO vragenlijst_2 (client_id, doorverwezen_ja_nee) VALUES (?, 'ja')", (cid1,))
    conn.execute("INSERT INTO clients (voornaam) VALUES ('B')")
    cid2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO vragenlijst_2 (client_id, doorverwezen_ja_nee) VALUES (?, 'nee')", (cid2,))
    conn.commit()
    conn.close()

    data = get_dashboard_data('alles')
    assert data['uitstroom']['doorverwezen_ja'] == 1
    assert data['uitstroom']['doorverwezen_nee'] == 1


def test_dashboard_status_filter_and_radar_filter(db, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Actief dossier zonder VL3
    conn.execute("INSERT INTO clients (voornaam) VALUES ('Actief')")
    actief_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO vragenlijst_1 (client_id, verwijzer) VALUES (?, 'Huisarts')", (actief_id,))
    conn.execute("INSERT INTO vragenlijst_2 (client_id, hoofdreden) VALUES (?, 'Eenzaamheid')", (actief_id,))

    # Afgerond dossier met beide metingen
    conn.execute("INSERT INTO clients (voornaam) VALUES ('Afgerond')")
    afgerond_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    vl1_vals = {f'sw_q{i}': 4 for i in range(1, 45)}
    vl3_vals = {f'sw_q{i}': 6 for i in range(1, 45)}
    cols = ', '.join(vl1_vals.keys())
    placeholders = ', '.join('?' * len(vl1_vals))
    conn.execute(
        f"INSERT INTO vragenlijst_1 (client_id, verwijzer, {cols}) VALUES (?, 'Wijkteam', {placeholders})",
        [afgerond_id] + list(vl1_vals.values())
    )
    conn.execute(
        "INSERT INTO vragenlijst_2 (client_id, hoofdreden) VALUES (?, 'Stress of overbelasting')",
        (afgerond_id,)
    )
    cols3 = ', '.join(vl3_vals.keys())
    placeholders3 = ', '.join('?' * len(vl3_vals))
    conn.execute(
        f"INSERT INTO vragenlijst_3 (client_id, continuering, {cols3}) VALUES (?, 'ja_actief', {placeholders3})",
        [afgerond_id] + list(vl3_vals.values())
    )

    conn.commit()
    conn.close()

    actief = get_dashboard_data('alles', status='actief')
    assert actief['kpis']['totaal'] == 1
    assert actief['filters']['status'] == 'actief'

    radar = get_dashboard_data('alles', radar_group='continuering', radar_value='ja_actief')
    assert radar['sw_n'] == 1
    assert radar['filters']['radar_scope_label'] == 'Continuering: Nog actief'


def test_dashboard_kpi_naar_activiteit_and_contacturen_only_completed(db, db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)

    conn.execute("INSERT INTO clients (voornaam) VALUES ('Loopt')")
    actief_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO vragenlijst_1 (client_id) VALUES (?)", (actief_id,))
    conn.execute(
        "INSERT INTO vragenlijst_2 (client_id, datum_start_activiteit, contactmomenten_ff, contactmomenten_tel, uitval_ja_nee) "
        "VALUES (?, '2026-01-10', 10, 4, 'nee')",
        (actief_id,)
    )

    conn.execute("INSERT INTO clients (voornaam) VALUES ('Klaar')")
    afgerond_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO vragenlijst_1 (client_id) VALUES (?)", (afgerond_id,))
    conn.execute(
        "INSERT INTO vragenlijst_2 (client_id, datum_start_activiteit, contactmomenten_ff, contactmomenten_tel, uitval_ja_nee) "
        "VALUES (?, '2026-01-08', 6, 2, 'nee')",
        (afgerond_id,)
    )
    conn.execute("INSERT INTO vragenlijst_3 (client_id, continuering) VALUES (?, 'ja_actief')", (afgerond_id,))

    conn.commit()
    conn.close()

    data = get_dashboard_data('alles')
    assert data['kpis']['naar_activiteit'] == 1
    assert data['contactmomenten']['afgerond_n'] == 1
    assert data['contactmomenten']['gem_ff'] == 6.0
    assert data['contactmomenten']['gem_tel'] == 2.0


def test_dashboard_radar_filter_groups_limited(db):
    data = get_dashboard_data('alles')
    radar_groups = [item['value'] for item in data['filters']['radar_group_options']]
    assert radar_groups == ['alle', 'geslacht', 'hoofdreden', 'continuering']
