# Welzijnscoach Dashboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/dashboard` route that shows aggregated insights (KPIs, spinnenweb delta, verwijzers, signalering, demografie, uitstroom, contactmomenten) for the welzijnscoach, filterable by kwartaal/jaar/alles.

**Architecture:** All aggregation logic lives in `app/models.py` as `get_dashboard_data(periode)`. The route in `app/routes.py` calls this function and passes a flat context to `app/templates/dashboard.html`. The template renders all widgets with Bootstrap 5 cards and Chart.js (local static file) for the radar chart and bar charts.

**Tech Stack:** Flask 3, SQLite3 (stdlib), Bootstrap 5 (local), Chart.js v4 (`chart.umd.min.js`, local static), pytest (dev only)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `app/models.py` | Modify | Add `SIGNALERING_ACHTERUITGANG_DREMPEL`, `get_periode_range()`, `get_dashboard_data()`, `_empty_dashboard_data()` |
| `app/routes.py` | Modify | Add `/dashboard` route; import new models functions |
| `app/templates/dashboard.html` | Create | Full dashboard template: filter bar, KPI row, all 7 widgets |
| `app/templates/base.html` | Modify | Add "Dashboard" nav link |
| `tests/conftest.py` | Create | Pytest fixtures: in-memory SQLite DB wired to `app.models.get_db` |
| `tests/test_dashboard.py` | Create | Unit tests for `get_periode_range` and `get_dashboard_data` |

---

## Chunk 1: Backend Data Layer

### Task 1: Set up test infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1.1: Install pytest**

```bash
pip install pytest
```

Expected: pytest installed (check with `pytest --version`)

- [ ] **Step 1.2: Create `tests/__init__.py`**

```python
# empty
```

- [ ] **Step 1.3: Create `tests/conftest.py`**

This fixture creates a temporary SQLite DB with the full schema and patches `app.models.get_db` for every test that requests `db`.

```python
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
    conn.row_factory = sqlite3.Row
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
```

- [ ] **Step 1.4: Create skeleton `tests/test_dashboard.py`**

```python
from datetime import date
from app.models import get_periode_range, get_dashboard_data, SIGNALERING_ACHTERUITGANG_DREMPEL


def test_placeholder():
    assert True
```

- [ ] **Step 1.5: Run tests to verify setup**

```bash
cd "c:/Users/XavierFriesen/.projects SFNL/registratiesysteem WoR"
pytest tests/ -v
```

Expected: `1 passed`

- [ ] **Step 1.6: Commit**

```bash
git add tests/
git commit -m "test: add pytest infrastructure for dashboard"
```

---

### Task 2: Add `SIGNALERING_ACHTERUITGANG_DREMPEL` and `get_periode_range()` to models.py

**Files:**
- Modify: `app/models.py` (add after imports, before `SW_QUESTIONS`)
- Test: `tests/test_dashboard.py`

- [ ] **Step 2.1: Write the failing tests first**

Add to `tests/test_dashboard.py`:

```python
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
```

- [ ] **Step 2.2: Run to confirm FAIL**

```bash
pytest tests/test_dashboard.py::test_get_periode_range_alles -v
```

Expected: `ImportError` or `AttributeError` — `get_periode_range` not defined yet

- [ ] **Step 2.3: Add constant and function to `app/models.py`**

Add after `from . import get_db` at the top of the file:

```python
import calendar
from datetime import date
```

Then add these two items **before** the `SW_QUESTIONS` dict:

```python
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
```

- [ ] **Step 2.4: Run tests — expect PASS**

```bash
pytest tests/test_dashboard.py -v
```

Expected: `4 passed`

- [ ] **Step 2.5: Commit**

```bash
git add app/models.py tests/test_dashboard.py
git commit -m "feat: add dashboard period range helper and signaling threshold"
```

---

### Task 3: Add `get_dashboard_data()` and `_empty_dashboard_data()` to models.py

**Files:**
- Modify: `app/models.py` (add at the end of the file)
- Test: `tests/test_dashboard.py`

- [ ] **Step 3.1: Write failing tests**

Add to `tests/test_dashboard.py`:

```python
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
```

- [ ] **Step 3.2: Run to confirm FAIL**

```bash
pytest tests/test_dashboard.py -v -k "dashboard_data or kpis or signaal or verwijzer"
```

Expected: multiple FAILs — `get_dashboard_data` not defined yet

- [ ] **Step 3.3: Add `_empty_dashboard_data()` and `get_dashboard_data()` to `app/models.py`**

Add at the **end** of `app/models.py`:

```python
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
        sw_vl1.append(avg1 or 0)
        sw_vl3.append(avg3 or 0)
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

        if cid not in vl2_rows:
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
```

- [ ] **Step 3.4: Run all tests — expect PASS**

```bash
pytest tests/ -v
```

Expected: all tests pass (green)

- [ ] **Step 3.5: Commit**

```bash
git add app/models.py tests/test_dashboard.py
git commit -m "feat: add get_dashboard_data() aggregation function"
```

---

## Chunk 2: Route and Template

### Task 4: Add `/dashboard` route to routes.py

**Files:**
- Modify: `app/routes.py`

- [ ] **Step 4.1: Add import and route**

In `app/routes.py`, add `get_dashboard_data` to the import from `.models`:

```python
from .models import (
    get_all_clients, get_client, add_client, delete_client,
    get_clients_by_first_name,
    get_vl1, save_vl1, get_vl2, save_vl2, get_vl3, save_vl3,
    get_all_for_export, SW_QUESTIONS, calc_sw_scores,
    get_dashboard_data,
)
```

Then add the route after the `index` route (after line ~79):

```python
# ── Dashboard ─────────────────────────────────────────────────────────────────

@bp.route('/dashboard')
def dashboard():
    if not g.coach.get('naam'):
        return redirect(url_for('main.coach_setup'))
    periode = request.args.get('periode', 'alles')
    if periode not in ('kwartaal', 'jaar', 'alles'):
        periode = 'alles'
    data = get_dashboard_data(periode)
    return render_template('dashboard.html', periode=periode, **data)
```

- [ ] **Step 4.2: Verify the app starts (manual check)**

```bash
cd "c:/Users/XavierFriesen/.projects SFNL/registratiesysteem WoR"
python -c "from app import create_app; app = create_app(); print('OK')"
```

Expected: `OK` (no import errors)

- [ ] **Step 4.3: Commit**

```bash
git add app/routes.py
git commit -m "feat: add /dashboard route"
```

---

### Task 5: Create `dashboard.html` — filter bar + KPI row

**Files:**
- Create: `app/templates/dashboard.html`

- [ ] **Step 5.1: Create the template with filter bar and KPI row**

```html
{% extends 'base.html' %}
{% block title %}Dashboard — WoR Registratie{% endblock %}

{% block content %}
{# ── Sticky filter bar ─────────────────────────────────────────────────── #}
<div class="sticky-top bg-white border-bottom py-2 mb-4 shadow-sm" style="z-index:100;">
  <div class="d-flex align-items-center gap-2">
    <span class="fw-semibold me-2 text-muted small">Periode:</span>
    {% for label, value in [('Kwartaal', 'kwartaal'), ('Jaar', 'jaar'), ('Alles', 'alles')] %}
      <a href="{{ url_for('main.dashboard', periode=value) }}"
         class="btn btn-sm {% if periode == value %}btn-primary{% else %}btn-outline-secondary{% endif %}">
        {{ label }}
      </a>
    {% endfor %}
  </div>
</div>

{% if kpis.totaal == 0 %}
  <div class="alert alert-secondary">Geen data beschikbaar voor de geselecteerde periode.</div>
{% else %}

{# ── KPI row ──────────────────────────────────────────────────────────── #}
<div class="row row-cols-2 row-cols-md-5 g-3 mb-4">
  {% set kpi_items = [
    ('Totaal', kpis.totaal, 'primary'),
    ('Actief', kpis.actief, 'warning'),
    ('Afgerond', kpis.afgerond, 'success'),
    ('Uitgevallen', kpis.uitgevallen, 'danger'),
    ('Gem. tevredenheid', kpis.gem_tevredenheid if kpis.gem_tevredenheid is not none else '—', 'info'),
  ] %}
  {% for label, value, color in kpi_items %}
  <div class="col">
    <div class="card h-100 border-0 shadow-sm text-center">
      <div class="card-body py-3">
        <div class="display-6 fw-bold text-{{ color }}">{{ value }}</div>
        <div class="small text-muted mt-1">{{ label }}</div>
      </div>
    </div>
  </div>
  {% endfor %}
</div>

{# ── Row 1: Spinnenweb + Verwijzers ───────────────────────────────────── #}
<div class="row g-4 mb-4">
  {# Spinnenweb #}
  <div class="col-12 col-lg-8">
    <div class="card border-0 shadow-sm h-100">
      <div class="card-header bg-transparent fw-semibold">Spinnenweb: intake vs opvolging</div>
      <div class="card-body">
        {% if sw_n == 0 %}
          <p class="text-muted">Nog geen deelnemers met zowel intake als opvolging.</p>
        {% else %}
          <p class="text-muted small mb-3">Gebaseerd op {{ sw_n }} deelnemer{{ 's' if sw_n != 1 else '' }} met intake én opvolging.</p>
          <div class="d-flex justify-content-center mb-3">
            <canvas id="dashboardRadar" width="380" height="340"></canvas>
          </div>
          {# Delta table #}
          <table class="table table-sm table-borderless">
            <thead><tr>
              <th>Dimensie</th>
              <th class="text-end">Gem. intake</th>
              <th class="text-end">Gem. opvolging</th>
              <th class="text-end">Δ</th>
            </tr></thead>
            <tbody>
            {% for i in range(6) %}
              {% set delta = sw_delta[i] %}
              {% if delta is not none %}
                {% if delta > 0.2 %}
                  {% set cls = 'text-success fw-semibold' %}
                  {% set prefix = '+' %}
                {% elif delta < -0.2 %}
                  {% set cls = 'text-danger fw-semibold' %}
                  {% set prefix = '' %}
                {% else %}
                  {% set cls = 'text-muted' %}
                  {% set prefix = '+' if delta >= 0 else '' %}
                {% endif %}
              {% endif %}
              <tr>
                <td>{{ sw_labels[i] }}</td>
                <td class="text-end">{{ '%.1f' % sw_vl1[i] if sw_vl1[i] else '—' }}</td>
                <td class="text-end">{{ '%.1f' % sw_vl3[i] if sw_vl3[i] else '—' }}</td>
                <td class="text-end {{ cls if delta is not none else '' }}">
                  {% if delta is not none %}{{ prefix }}{{ '%.1f' % delta }}{% else %}—{% endif %}
                </td>
              </tr>
            {% endfor %}
            </tbody>
          </table>
        {% endif %}
      </div>
    </div>
  </div>

  {# Verwijzers #}
  <div class="col-12 col-lg-4">
    <div class="card border-0 shadow-sm h-100">
      <div class="card-header bg-transparent fw-semibold">Verwijzers</div>
      <div class="card-body">
        {% if not verwijzers %}
          <p class="text-muted">Geen data.</p>
        {% else %}
          <canvas id="verwijzersChart" height="180"></canvas>
          {% if huisartsen %}
            <hr class="my-3">
            <p class="fw-semibold small mb-2">Huisartsenpraktijken</p>
            <ul class="list-unstyled mb-0">
              {% for h in huisartsen %}
                <li class="d-flex justify-content-between py-1 border-bottom">
                  <span class="small">{{ h.naam }}</span>
                  <span class="badge bg-secondary rounded-pill">{{ h.count }}</span>
                </li>
              {% endfor %}
            </ul>
          {% endif %}
        {% endif %}
      </div>
    </div>
  </div>
</div>

{# ── Row 2: Signalering ───────────────────────────────────────────────── #}
<div class="row g-4 mb-4">
  <div class="col-12">
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-transparent fw-semibold">Aandacht vereist</div>
      <div class="card-body">
        {% if not signalen %}
          <div class="alert alert-success mb-0">
            <i class="me-2">✓</i> Alle deelnemers zijn op schema.
          </div>
        {% else %}
          <div class="table-responsive">
            <table class="table table-sm align-middle mb-0">
              <thead><tr>
                <th>Deelnemer</th>
                <th>Signaal</th>
                <th></th>
              </tr></thead>
              <tbody>
              {% for s in signalen %}
                {% if s.type == 'wachtend' %}{% set badge = 'warning' %}
                {% elif s.type == 'uitgevallen' %}{% set badge = 'danger' %}
                {% else %}{% set badge = 'secondary' %}{% endif %}
                <tr>
                  <td class="fw-semibold">{{ s.naam }}</td>
                  <td><span class="badge bg-{{ badge }}">{{ s.reden }}</span></td>
                  <td class="text-end">
                    <a href="{{ s.link }}" class="btn btn-sm btn-outline-primary">Bekijk dossier</a>
                  </td>
                </tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
        {% endif %}
      </div>
    </div>
  </div>
</div>

{# ── Row 3: Demografie + Uitstroom + Contactmomenten ─────────────────── #}
<div class="row g-4">
  {# Demografie #}
  <div class="col-12 col-md-4">
    <div class="card border-0 shadow-sm h-100">
      <div class="card-header bg-transparent fw-semibold">Demografie</div>
      <div class="card-body">
        {% if not demografie.geslacht and not demografie.leeftijd %}
          <p class="text-muted">Geen data.</p>
        {% else %}
          {% if demografie.geslacht %}
            <p class="small fw-semibold text-muted mb-1">Geslacht</p>
            {% set totaal_g = demografie.geslacht | sum(attribute='count') %}
            {% for item in demografie.geslacht %}
              <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="small">{{ item.label }}</span>
                <span class="small text-muted">{{ item.count }} ({{ (item.count / totaal_g * 100) | round | int }}%)</span>
              </div>
              <div class="progress mb-2" style="height:6px;">
                <div class="progress-bar" style="width:{{ (item.count / totaal_g * 100) | round | int }}%"></div>
              </div>
            {% endfor %}
          {% endif %}
          {% if demografie.leeftijd %}
            <p class="small fw-semibold text-muted mt-3 mb-1">Leeftijd</p>
            {% for item in demografie.leeftijd %}
              <div class="d-flex justify-content-between mb-1">
                <span class="small">{{ item.label }}</span>
                <span class="badge bg-secondary rounded-pill">{{ item.count }}</span>
              </div>
            {% endfor %}
          {% endif %}
        {% endif %}
      </div>
    </div>
  </div>

  {# Uitstroom #}
  <div class="col-12 col-md-4">
    <div class="card border-0 shadow-sm h-100">
      <div class="card-header bg-transparent fw-semibold">Uitstroom</div>
      <div class="card-body">
        {% if not uitstroom.bestemmingen %}
          <p class="text-muted">Geen data.</p>
        {% else %}
          <p class="small fw-semibold text-muted mb-1">Bestemming</p>
          {% for item in uitstroom.bestemmingen %}
            <div class="d-flex justify-content-between mb-1">
              <span class="small">{{ item.label }}</span>
              <span class="badge bg-secondary rounded-pill">{{ item.count }}</span>
            </div>
          {% endfor %}
          <hr class="my-3">
          <p class="small fw-semibold text-muted mb-2">Doorverwezen</p>
          <div class="d-flex gap-3">
            <div class="text-center">
              <div class="fs-4 fw-bold text-success">{{ uitstroom.doorverwezen_ja }}</div>
              <div class="small text-muted">Ja</div>
            </div>
            <div class="text-center">
              <div class="fs-4 fw-bold text-secondary">{{ uitstroom.doorverwezen_nee }}</div>
              <div class="small text-muted">Nee</div>
            </div>
          </div>
        {% endif %}
      </div>
    </div>
  </div>

  {# Contactmomenten #}
  <div class="col-12 col-md-4">
    <div class="card border-0 shadow-sm h-100">
      <div class="card-header bg-transparent fw-semibold">Contactmomenten (gem.)</div>
      <div class="card-body d-flex align-items-center justify-content-around">
        <div class="text-center">
          <div class="display-5 fw-bold text-primary">
            {{ contactmomenten.gem_ff if contactmomenten.gem_ff is not none else '—' }}
          </div>
          <div class="small text-muted mt-1">Face-to-face</div>
        </div>
        <div class="vr"></div>
        <div class="text-center">
          <div class="display-5 fw-bold text-info">
            {{ contactmomenten.gem_tel if contactmomenten.gem_tel is not none else '—' }}
          </div>
          <div class="small text-muted mt-1">Telefonisch</div>
        </div>
      </div>
    </div>
  </div>
</div>

{% endif %}{# end if kpis.totaal > 0 #}
{% endblock %}

{% block scripts %}
{% if kpis.totaal > 0 %}
<script src="{{ url_for('static', filename='chart.umd.min.js') }}"></script>
<script>
// ── Radar chart ──────────────────────────────────────────────────────────────
{% if sw_n > 0 %}
(function() {
  const ctx = document.getElementById('dashboardRadar').getContext('2d');
  new Chart(ctx, {
    type: 'radar',
    data: {
      labels: {{ sw_labels | tojson }},
      datasets: [
        {
          label: 'Intake (VL1)',
          data: {{ sw_vl1 | tojson }},
          borderColor: 'rgba(30,111,142,0.7)',
          backgroundColor: 'rgba(30,111,142,0.08)',
          borderDash: [5, 4],
          pointRadius: 3,
        },
        {
          label: 'Opvolging (VL3)',
          data: {{ sw_vl3 | tojson }},
          borderColor: 'rgba(40,160,98,0.9)',
          backgroundColor: 'rgba(40,160,98,0.12)',
          pointRadius: 4,
        },
      ],
    },
    options: {
      scales: { r: { min: 0, max: 10, ticks: { stepSize: 2 } } },
      plugins: { legend: { position: 'bottom' } },
    },
  });
})();
{% endif %}

// ── Verwijzers bar chart ─────────────────────────────────────────────────────
{% if verwijzers %}
(function() {
  const ctx = document.getElementById('verwijzersChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: {{ verwijzers | map(attribute='naam') | list | tojson }},
      datasets: [{
        label: 'Aantal',
        data: {{ verwijzers | map(attribute='count') | list | tojson }},
        backgroundColor: 'rgba(232,147,58,0.7)',
        borderColor: 'rgba(232,147,58,1)',
        borderWidth: 1,
      }],
    },
    options: {
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
})();
{% endif %}
</script>
{% endif %}
{% endblock %}
```

- [ ] **Step 5.2: Verify the page loads in the browser**

Start the app and open `http://localhost:5050/dashboard` in a browser.
Expected: filter bar visible, KPI row shows 0s (or real data if DB has clients), no Python errors.

- [ ] **Step 5.3: Commit**

```bash
git add app/templates/dashboard.html
git commit -m "feat: add dashboard template with all widgets"
```

---

### Task 6: Add nav link to base.html

**Files:**
- Modify: `app/templates/base.html`

- [ ] **Step 6.1: Add Dashboard link to navbar**

In `app/templates/base.html`, inside the `{% if coach.naam %}` block, add a Dashboard link before the coach name display. Replace:

```html
    <div class="d-flex align-items-center gap-2">
      <span class="text-white opacity-75 small">
```

with:

```html
    <div class="d-flex align-items-center gap-2">
      <a href="{{ url_for('main.dashboard') }}" class="btn btn-sm btn-navbar-ghost">Dashboard</a>
      <span class="text-white opacity-75 small">
```

- [ ] **Step 6.2: Verify nav link appears**

Reload the app. The navbar should now show a "Dashboard" button next to the coach name.

- [ ] **Step 6.3: Run full test suite one last time**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 6.4: Final commit**

```bash
git add app/templates/base.html
git commit -m "feat: add Dashboard nav link to navbar"
```

---

## Summary

After completing all tasks, the dashboard will be accessible at `/dashboard` with:

- A sticky period filter (Kwartaal / Jaar / Alles)
- KPI row: Totaal / Actief / Afgerond / Uitgevallen / Gem. tevredenheid
- Spinnenweb radar chart (VL1 vs VL3 overlay) + delta table
- Verwijzers bar chart + huisartsenpraktijken list
- Signalering table (lang wachtend → uitgevallen → achteruitgang)
- Demografie (geslacht + leeftijd bars)
- Uitstroom (bestemmingen + doorverwezen counts)
- Contactmomenten (gem. face-to-face + telefonisch)
