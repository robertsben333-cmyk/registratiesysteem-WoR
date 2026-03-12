---
title: Voltooide deelnemers — apart tabblad
date: 2026-03-12
status: draft
---

# Spec: Voltooide deelnemers tab

## Doel

Wanneer alle drie de vragenlijsten (VL1 Intake, VL2 Uitstroom, VL3 Opvolging) van een deelnemer zijn ingevuld, verschijnt die deelnemer niet langer in de actieve lijst maar in een apart tabblad "Voltooide deelnemers".

## Definitie "voltooid"

Een cliënt is voltooid als voor diens `client_id` rijen bestaan in **alle drie** tabellen: `vragenlijst_1`, `vragenlijst_2` én `vragenlijst_3`.

## Wijzigingen

### `app/routes.py` — `index()`

`get_all_clients()` retourneert `sqlite3.Row`-objecten; `c['id']` (Python) en `client.id` (Jinja2) werken beide.

Na het opbouwen van de `status`-dict (met integer-sleutels `{1: bool, 2: bool, 3: bool}`), wordt de lijst gesplitst:

```python
active_clients = [c for c in clients if not all(status[c['id']].values())]
done_clients   = [c for c in clients if all(status[c['id']].values())]
```

De template-aanroep verandert van `clients=clients` naar:

```python
return render_template('index.html',
    active_clients=active_clients,
    done_clients=done_clients,
    status=status)
```

**Let op:** de wijziging in `routes.py` en `index.html` moeten samen worden ingezet. De template mag de variabele `clients` niet meer gebruiken.

### `app/templates/index.html`

**Topniveau-conditie:**
```jinja
{% if active_clients or done_clients %}
  {# tab-container #}
{% else %}
  {# bestaande lege-staat kaart — tekst "Nog geen cliënten toegevoegd." en "+ Eerste cliënt toevoegen" knop blijven ongewijzigd #}
{% endif %}
```

**Bootstrap tabs markup (standaard `data-bs-toggle="tab"`):**

Bootstrap JS is al aanwezig via `static/bootstrap.bundle.min.js`. Tabs worden geactiveerd via de standaard Bootstrap 5 data-attributen. Tab 1 is standaard actief via `active` klasse op het `<li>`-element en `show active` op het bijbehorende `<div class="tab-pane">`.

Schematisch:
```html
<ul class="nav nav-tabs mb-3">
  <li class="nav-item">
    <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-actief">
      Actieve deelnemers
    </button>
  </li>
  <li class="nav-item">
    <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-voltooid">
      Voltooide deelnemers
      {% if done_clients %}
        <span class="badge bg-success ms-1">{{ done_clients|length }}</span>
      {% endif %}
    </button>
  </li>
</ul>
<div class="tab-content">
  <div class="tab-pane fade show active" id="tab-actief"> ... </div>
  <div class="tab-pane fade" id="tab-voltooid"> ... </div>
</div>
```

**Tabelinhoud:**
De volledige conditional logica (inclusief "Nog te doen" / "Invullen" branches) blijft aanwezig in beide tab-panes voor consistentie in de templatecode. In de voltooide tab zullen de "Nog te doen" branches per definitie nooit renderen, maar de code hoeft niet vereenvoudigd te worden.

Tabelkolommen per tab:
- VL1: "Bekijken" + "Bewerken" (als ingevuld), "Invullen" (als niet)
- VL2: "Bekijken" + "Bewerken" (als ingevuld) via `vragenlijst_2_view`, "Invullen" (als niet)
- VL3: "Bekijken" + "Bewerken" (als ingevuld), "Invullen" (als niet)
- Verwijder-knop (✕) aanwezig voor alle cliënten in beide tabs

**Delete modals:** blijven in `<tbody>` staan, conform de bestaande templatestructuur (ongewijzigd patroon).

**Badge op tab-header:** alleen de "Voltooide deelnemers" tab krijgt een badge met het aantal. De "Actieve deelnemers" tab krijgt geen badge — dit is een expliciete keuze.

**Lege-staat per tab (als een tab leeg is maar de andere niet):**
Toon een tabelrij die de volledige breedte beslaat:
```html
<tr>
  <td colspan="7" class="text-center text-muted py-3">Nog geen actieve deelnemers.</td>
</tr>
```
(vervang tekst voor de voltooide tab: "Nog geen voltooide deelnemers.") Geen CTA-knop in beide gevallen.

**Na een redirect naar `index`:** altijd Tab 1 actief. Geen tab-persistentie.

VL2 redirect al naar `main.index` (na opslaan ziet de gebruiker de cliënt verdwenen uit Tab 1 als die voltooid is).
VL3 redirect naar `main.vragenlijst_3_view` — de gebruiker ziet de transitie pas bij het volgende bezoek aan de index. Beide routes voegen al een flash-bericht toe ("Vragenlijst X opgeslagen."). Geen wijzigingen aan deze redirects nodig; dit gedrag is acceptabel.

**De "+ Nieuwe cliënt" en "Exporteer Excel" knoppen** blijven in de page-header boven de tabs.

## Niet in scope

- Geen databasewijzigingen.
- Geen nieuwe routes.
- Geen wijziging aan de vragenlijst-routes of exportlogica.
