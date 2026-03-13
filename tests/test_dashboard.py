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
