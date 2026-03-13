# Welzijnscoach Dashboard — Design Spec

**Datum:** 2026-03-13
**Project:** Registratiesysteem WoR
**Doel:** Een geaggregeerd coach-dashboard dat inzicht geeft in voortgang, impact en aandachtspunten over alle deelnemers heen.

---

## 1. Context

De welzijnscoach registreert deelnemers via drie vragenlijsten:
- **VL1** (intake): demografieën, verwijzer, spinnenweb baseline (44 vragen, 6 dimensies)
- **VL2** (uitstroom): contactmomenten, uitvaldata, doorverwijzing
- **VL3** (opvolging, ~3 maanden): spinnenweb follow-up, tevredenheidscijfer

Het dashboard geeft de coach een geaggregeerd overzicht over alle eigen deelnemers, gefilterd op tijdperiode.

---

## 2. Route & Navigatie

- **Route:** `GET /dashboard?periode=kwartaal|jaar|alles`
- **Default:** `periode=alles` (wanneer de queryparameter ontbreekt)
- **Toegang:** Nieuwe "Dashboard"-knop in de bestaande navigatie (naast de homepage-link)
- **Template:** `app/templates/dashboard.html`
- **Method:** GET only; de tijdfilter werkt als queryparameter

---

## 3. Tijdfilter

Een sticky filterbalk bovenaan de pagina met drie opties:

| Optie | `periode`-waarde | Bereik |
|-------|-----------------|--------|
| Kwartaal | `kwartaal` | Huidig kwartaal (Q1/Q2/Q3/Q4 van het huidige jaar) |
| Jaar | `jaar` | Huidig kalenderjaar (1 jan – 31 dec) |
| Alles | `alles` | Geen datumbeperking (default) |

**Filterbasis:** `clients.aangemaakt_op` is het **enige** filteranker voor alle widgets. Er zijn geen per-widget afwijkingen. Alle VL1/VL2/VL3-data van de geselecteerde clients wordt meegenomen, ongeacht wanneer die vragenlijsten ingevuld zijn.

**Lege staat:** Als de filter geen clients oplevert, tonen alle widgets een "Geen data beschikbaar"-melding in plaats van grafieken of tabellen.

---

## 4. KPI-balk

Een rij van 5 compacte cijferkaartjes direct onder de filterbalk.

| KPI | Definitie |
|-----|-----------|
| Totaal deelnemers | Aantal clients in geselecteerde periode |
| Actief | Clients waarbij niet alle 3 vragenlijsten ingevuld zijn, **én** niet uitgevallen |
| Afgerond | Clients waarbij alle 3 vragenlijsten ingevuld zijn |
| Uitgevallen | Clients met VL2 ingevuld én `uitval_ja_nee = 'ja'` — **aparte categorie met prioriteit**: wordt als Uitgevallen geclassificeerd vóór Afgerond/Actief wordt bepaald. Uitgesloten van Actief én Afgerond. |
| Gem. tevredenheid | Gemiddeld `tevredenheidscijfer` uit VL3; toon `"—"` als geen enkele client VL3 heeft |

> De vijf KPI-waarden overlappen deels en zijn niet bedoeld om op te tellen.
> Logica: `Actief + Afgerond + Uitgevallen = Totaal` (Uitgevallen is exclusief; Actief en Afgerond sluiten uitgevallen uit).

---

## 5. Spinnenweb-widget

**Positie:** Grote widget, linksboven in het grid (2-koloms breedte)

**Radar chart:**
- Twee overlappende lijnen: gemiddelde VL1-scores (gestippeld) en gemiddelde VL3-scores (vol)
- Assen: de 6 dimensies (Lichaamsfuncties, Mentaal welbevinden, Zingeving, Kwaliteit van leven, Meedoen, Dagelijks functioneren)
- Schaal: 0–10
- **Implementatie:** Nieuw `<canvas id="dashboardRadar">` in `dashboard.html`. Chart.js wordt geladen via `{{ url_for('static', filename='chart.umd.min.js') }}` — de lokale bundel, niet een CDN. De bestaande macro's in `_spinnenweb.html` werken op één client-rij en zijn niet herbruikbaar; de dimensie-berekeningen via `SW_QUESTIONS` uit `models.py` worden wel hergebruikt in de backend.
- Backend geeft twee arrays door aan het template: `vl1_gem` en `vl3_gem` (6 waarden elk)
- Contextnoot: "Gebaseerd op X deelnemers met intake én opvolging"
- **Telt alleen** clients met zowel VL1 als VL3 ingevuld
- Lege staat: toon melding "Nog geen deelnemers met zowel intake als opvolging"

**Delta-tabel eronder:**

| Dimensie | Gem. VL1 | Gem. VL3 | Δ |
|----------|----------|----------|---|
| Lichaamsfuncties | 6.2 | 7.1 | **+0.9** (groen) |
| ... | | | |

- Positief Δ = groen, negatief Δ = rood, neutraal (−0.2 tot +0.2) = grijs
- Dimensie-gemiddelden berekend via `SW_QUESTIONS` in `models.py`

---

## 6. Verwijzers-widget

**Positie:** Middelgrote widget, rechts van spinnenweb

**Databron:** `vragenlijst_1.verwijzer` en `vragenlijst_1.huisartsenpraktijk` — uitsluitend VL1, niet VL2.

**Inhoud:**
1. **Staafdiagram** (horizontaal): verdeling van `verwijzer`-waarden, gesorteerd op frequentie
2. **Lijst van huisartsenpraktijken**: waarde van `huisartsenpraktijk` + aantal verwijzingen, gesorteerd meest → minst

Het `huisartsenpraktijk`-veld is vrije tekst; er is bewust geen deduplicatie van bijna-duplicaten — data wordt weergegeven zoals ingevoerd. Dit is een bekende beperking.

---

## 7. Signalering-widget ("Opvolging mogelijk")

**Positie:** Widget rechtsboven, prominent

**Constante:** `SIGNALERING_ACHTERUITGANG_DREMPEL = -1.0` — te definiëren als named constant in `models.py`

**Drie categorieën signalen, in deze volgorde:**

1. **Lang wachtend** — `clients.aangemaakt_op` > 3 maanden geleden, én **VL2 is nog niet ingevuld** (ongeacht VL3). Een client zonder VL2 na 3 maanden wordt als stalled beschouwd.
2. **Verdere ondersteuningsbehoefte** — `vragenlijst_3.behoefte_ondersteuning` is:
   - `Ja, ik zou graag opnieuw contact met de welzijnscoach`
   - `Ja, ik denk dat ik professionele hulp nodig heb`
3. **Achteruitgang** — **enige dimensie** waarbij Δ (VL3 − VL1) < `SIGNALERING_ACHTERUITGANG_DREMPEL` (−1.0). Niet het totaalgemiddelde, maar per dimensie afzonderlijk.

Per signaal wordt getoond:
- Naam deelnemer
- Reden (bijv. "Wacht al 4 maanden", "Ja, ik zou graag opnieuw contact met de welzijnscoach", "Mentaal welbevinden: −1.4")
- Knop "Bekijk dossier" → link naar meest relevante view:
  - VL3 ingevuld → `/client/<id>/vragenlijst/3/view`
  - VL2 ingevuld, geen VL3 → `/client/<id>/vragenlijst/2/view`
  - Alleen VL1 ingevuld → `/client/<id>/vragenlijst/1/view`

Geen signalen → groene melding "Alle deelnemers zijn op schema".

---

## 8. Demografie-widget

**Positie:** Kleine widget, onderste rij links

**Databron:** `vragenlijst_1` kolommen: `geslacht`, `leeftijdscategorie`

**Inhoud:**
- Verdeling **`geslacht`** (Man/Vrouw/Anders/etc.) — horizontaal staafdiagram met percentages
- Verdeling **`leeftijdscategorie`** — horizontaal staafdiagram

Template context: `demografie = { 'geslacht': [{'label': str, 'count': int}, ...], 'leeftijd': [{'label': str, 'count': int}, ...] }`

Lege staat: "Geen data" wanneer geen clients VL1 hebben.

---

## 9. Uitstroom-widget

**Positie:** Kleine widget, onderste rij midden

**Databron:** `vragenlijst_2` kolommen: `uitstroom_naar`, `doorverwezen_ja_nee`

**Inhoud:**
- Verdeling **`uitstroom_naar`** — horizontaal staafdiagram, gesorteerd op frequentie
- **Doorverwezen**: twee cijfers naast elkaar — aantal "Ja" en aantal "Nee" uit `doorverwezen_ja_nee`

Template context: `uitstroom = { 'bestemmingen': [{'label': str, 'count': int}, ...], 'doorverwezen_ja': int, 'doorverwezen_nee': int }`

Lege staat: "Geen data" wanneer geen clients VL2 hebben.

---

## 10. Contactmomenten-widget

**Positie:** Kleine widget, onderste rij rechts

**Databron:** `vragenlijst_2` kolommen: `contactmomenten_ff` (INTEGER), `contactmomenten_tel` (INTEGER)

**Berekening:** Gemiddelde over alle clients in de periode met VL2 ingevuld, inclusief uitgevallen clients.

**Inhoud:**
- Gemiddeld **face-to-face** (`contactmomenten_ff`) — groot cijfer
- Gemiddeld **telefonisch** (`contactmomenten_tel`) — groot cijfer

Template context: `contactmomenten = { 'gem_ff': float|None, 'gem_tel': float|None }`

Lege staat: "—" per waarde wanneer `None`.

---

## 11. Data & Backend

**Route contract:**
```python
@app.route('/dashboard')
def dashboard():
    periode = request.args.get('periode', 'alles')  # 'kwartaal' | 'jaar' | 'alles'
    # Bepaal datum-range op basis van periode
    # Selecteer clients op aangemaakt_op
    # Bereken aggregaties
    return render_template('dashboard.html',
        periode=periode,
        kpis=...,           # dict: totaal, actief, afgerond, uitgevallen, gem_tevredenheid
        sw_vl1=...,         # list[float]: 6 dimensie-gemiddelden VL1
        sw_vl3=...,         # list[float]: 6 dimensie-gemiddelden VL3
        sw_n=...,           # int: aantal clients met beide metingen
        sw_labels=...,      # list[str]: dimensienamen
        verwijzers=...,     # list[dict]: {naam, count}
        huisartsen=...,     # list[dict]: {naam, count}
        signalen=...,       # list[dict]: {naam, reden, link}
        demografie=...,     # dict: geslacht, leeftijd
        uitstroom=...,      # dict: bestemming, doorverwezen
        contactmomenten=... # dict: gem_ff, gem_tel
    )
```

**Datalaag:**
- Alle berekeningen in Python (geen client-side data processing)
- `SW_QUESTIONS` uit `models.py` hergebruikt voor dimensie-gemiddelden
- `SIGNALERING_ACHTERUITGANG_DREMPEL = -1.0` als named constant in `models.py`

**Chart.js:**
- `dashboard.html` laadt `chart.umd.min.js` via `{{ url_for('static', filename='chart.umd.min.js') }}` in `{% block scripts %}` — lokale bundel, geen CDN vereist

---

## 12. Wat buiten scope valt

- Cross-coach vergelijking
- Export van het dashboard
- Individuele vraagscores (alleen dimensieniveau)
- Maand-filter
- Deduplicatie van vrije-tekst verwijzersnamen
