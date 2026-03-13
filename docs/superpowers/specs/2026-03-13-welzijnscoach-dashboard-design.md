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

- **Route:** `/dashboard`
- **Toegang:** Nieuwe "Dashboard"-knop in de bestaande navigatie (naast de homepage-link)
- **Template:** `app/templates/dashboard.html`

---

## 3. Tijdfilter

Een sticky filterbalk bovenaan de pagina met drie opties:

| Optie | Beschrijving |
|-------|-------------|
| Kwartaal | Huidig kwartaal (Q1/Q2/Q3/Q4 van het huidige jaar) |
| Jaar | Huidig kalenderjaar |
| Alles | Alle deelnemers ooit (default) |

De filter werkt op `aangemaakt_op` van de client. Alle widgets reageren op de geselecteerde periode.

---

## 4. KPI-balk

Een rij van 5 compacte cijferkaartjes direct onder de filterbalk:

| KPI | Berekening |
|-----|-----------|
| Totaal deelnemers | Aantal clients in geselecteerde periode |
| Actief | Clients waarbij VL2 of VL3 nog niet ingevuld is |
| Afgerond | Clients waarbij alle 3 vragenlijsten ingevuld zijn |
| Uitgevallen | Clients met `uitval_ja_nee = 'ja'` in VL2 |
| Gem. tevredenheid | Gemiddeld `tevredenheidscijfer` uit VL3 (alleen clients met VL3) |

---

## 5. Spinnenweb-widget

**Positie:** Grote widget, linksboven in het grid (2-koloms breedte)

**Radar chart:**
- Twee overlappende lijnen: gemiddelde VL1-scores (gestippeld) en gemiddelde VL3-scores (vol)
- Assen: de 6 dimensies (Lichaamsfuncties, Mentaal welbevinden, Zingeving, Kwaliteit van leven, Meedoen, Dagelijks functioneren)
- Schaal: 0–10
- Hergebruik van bestaande Chart.js radar-implementatie uit `_spinnenweb.html`
- Contextnoot: "Gebaseerd op X deelnemers met intake én opvolging"
- **Telt alleen** clients met zowel VL1 als VL3 ingevuld

**Delta-tabel eronder:**

| Dimensie | Gem. VL1 | Gem. VL3 | Δ |
|----------|----------|----------|---|
| Lichaamsfuncties | 6.2 | 7.1 | **+0.9** (groen) |
| Mentaal welbevinden | 5.8 | 6.4 | **+0.6** (groen) |
| ... | | | |

- Positief Δ = groen, negatief Δ = rood, neutraal = grijs
- Dimensie-gemiddelden berekend als gemiddelde van de bijbehorende sw_q-vragen (conform bestaande logica in `models.py`)

---

## 6. Verwijzers-widget

**Positie:** Middelgrote widget, rechts van spinnenweb

**Inhoud:**
1. **Staafdiagram** (horizontaal): verwijzertypes uit `verwijzer`-veld in VL1, gesorteerd op frequentie
2. **Lijst van huisartsenpraktijken**: naam (`huisartsenpraktijk`) + aantal verwijzingen, gesorteerd meest → minst

Gebaseerd op alle clients in geselecteerde periode met VL1 ingevuld.

---

## 7. Signalering-widget ("Aandacht vereist")

**Positie:** Widget rechtsboven, prominent

**Drie categorieën signalen, in deze volgorde:**

1. **Lang wachtend** — VL1 ingevuld > 3 maanden geleden, maar VL2 én VL3 nog niet ingevuld
2. **Uitgevallen** — `uitval_ja_nee = 'ja'` in VL2
3. **Achteruitgang** — Gemiddeld Δ over alle 6 dimensies (VL3 − VL1) < −1.0

Per signaal wordt getoond:
- Naam deelnemer
- Reden (bijv. "Wacht al 4 maanden op opvolging", "Uitgevallen", "Score gedaald met 1.3")
- Knop "Bekijk dossier" → link naar client-overview of VL3-view

Geen signalen = groene melding "Alle deelnemers zijn op schema".

---

## 8. Demografie-widget

**Positie:** Kleine widget, onderste rij links

**Inhoud:**
- Verdeling **geslacht** (Man/Vrouw/Anders) — donut of horizontaal staafje met percentages
- Verdeling **leeftijdscategorie** — horizontaal staafdiagram

Gebaseerd op VL1-data van clients in geselecteerde periode.

---

## 9. Uitstroom-widget

**Positie:** Kleine widget, onderste rij midden

**Inhoud:**
- Verdeling **uitstroom_naar** (bestemming na afsluiting) — tabel of staafje
- **Doorverwezen**: aantal ja/nee uit `doorverwezen_ja_nee`

Gebaseerd op VL2-data van clients in geselecteerde periode.

---

## 10. Contactmomenten-widget

**Positie:** Kleine widget, onderste rij rechts

**Inhoud:**
- Gemiddeld **face-to-face contactmomenten** (`contactmomenten_ff`)
- Gemiddeld **telefonische contactmomenten** (`contactmomenten_tel`)
- Weergave: twee grote cijfers naast elkaar, eventueel een klein staafje ter vergelijking

Gebaseerd op VL2-data van clients in geselecteerde periode.

---

## 11. Data & Backend

**Nieuwe route in `routes.py`:**
```python
@app.route('/dashboard')
def dashboard():
    # query params: periode = 'kwartaal' | 'jaar' | 'alles' (default)
    ...
```

**Datalaag:**
- Alle berekeningen in Python (geen client-side data processing)
- Query's op bestaande tabellen: `clients`, `vragenlijst_1`, `vragenlijst_2`, `vragenlijst_3`
- Spinnenweb-dimensie-gemiddelden hergebruiken de bestaande `SW_QUESTIONS`-definitie uit `models.py`
- JSON-data doorgeven aan template voor Chart.js-grafieken

---

## 12. Technische aanpak

- **Template:** Bootstrap 5 grid, bestaande stijlen van de app hergebruiken
- **Grafieken:** Chart.js (al aanwezig), radar chart hergebruikt van `_spinnenweb.html`
- **Geen nieuwe dependencies** nodig
- **Geen filtering op coach** — de app is per-coach (lokale installatie), dus alle data is al van de huidige coach

---

## 13. Wat buiten scope valt

- Cross-coach vergelijking
- Export van het dashboard
- Individuele vraagscores in het dashboard (alleen dimensieniveau)
- Maand-filter
