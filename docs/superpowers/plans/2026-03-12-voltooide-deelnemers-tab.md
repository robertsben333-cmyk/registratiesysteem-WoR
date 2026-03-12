# Voltooide deelnemers tab — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the client overview into two Bootstrap tabs — "Actieve deelnemers" and "Voltooide deelnemers" — where a client is "voltooid" when all three vragenlijsten are filled in.

**Architecture:** The `index()` route already builds a `status` dict per client. We split the existing `clients` list into `active_clients` / `done_clients` using that dict, pass both to the template, and replace the single table in `index.html` with a Bootstrap nav-tabs structure containing two identical table panels.

**Tech Stack:** Flask, Jinja2, Bootstrap 5 (already loaded via `static/bootstrap.bundle.min.js`)

---

## Chunk 1: Backend — split clients in `routes.py`

**Files:**
- Modify: `app/routes.py:57-69`

### Task 1: Split clients into active and done lists

- [ ] **Step 1: Open `app/routes.py` and locate the `index()` function (lines 57–69)**

  Current code:
  ```python
  clients = get_all_clients()
  status = {
      c['id']: {
          1: get_vl1(c['id']) is not None,
          2: get_vl2(c['id']) is not None,
          3: get_vl3(c['id']) is not None,
      }
      for c in clients
  }
  return render_template('index.html', clients=clients, status=status)
  ```

- [ ] **Step 2: Replace the `return render_template(...)` line with the split + new render call**

  Replace only the last line:
  ```python
  active_clients = [c for c in clients if not all(status[c['id']].values())]
  done_clients   = [c for c in clients if all(status[c['id']].values())]
  return render_template('index.html',
      active_clients=active_clients,
      done_clients=done_clients,
      status=status)
  ```

  The full `index()` function now looks like:
  ```python
  @bp.route('/')
  def index():
      if not g.coach.get('naam'):
          return redirect(url_for('main.coach_setup'))
      clients = get_all_clients()
      status = {
          c['id']: {
              1: get_vl1(c['id']) is not None,
              2: get_vl2(c['id']) is not None,
              3: get_vl3(c['id']) is not None,
          }
          for c in clients
      }
      active_clients = [c for c in clients if not all(status[c['id']].values())]
      done_clients   = [c for c in clients if all(status[c['id']].values())]
      return render_template('index.html',
          active_clients=active_clients,
          done_clients=done_clients,
          status=status)
  ```

- [ ] **Step 3: Verify the app still starts (template will temporarily break — that's fine)**

  Run: `python main.py` (or however the app is started — check `main.py` in the project root)
  Expected: Flask starts without import errors. The `/` route will show a Jinja2 `UndefinedError` for `clients` — that is expected at this stage.

---

## Chunk 2: Frontend — Bootstrap tabs in `index.html`

**Files:**
- Modify: `app/templates/index.html`

### Task 2: Replace single table with two-tab layout

- [ ] **Step 1: Replace the entire `{% if clients %}...{% endif %}` block**

  The current block starts at line 17 (`{% if clients %}`) and ends at line 142 (`{% endif %}`). Line 143 (`{% endblock %}`) must be kept — do **not** replace it.

  Replace it with the following:

  ```jinja
  {% if active_clients or done_clients %}
  {# ── Tab navigation ───────────────────────────────────────────────── #}
  <ul class="nav nav-tabs mb-3">
    <li class="nav-item">
      <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-actief" type="button">
        Actieve deelnemers
      </button>
    </li>
    <li class="nav-item">
      <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-voltooid" type="button">
        Voltooide deelnemers
        {% if done_clients %}
          <span class="badge bg-success ms-1">{{ done_clients|length }}</span>
        {% endif %}
      </button>
    </li>
  </ul>

  <div class="tab-content">

    {# ── Tab 1: Actieve deelnemers ──────────────────────────────────── #}
    <div class="tab-pane fade show active" id="tab-actief">
      <div class="card">
        <div class="card-body p-0">
          <table class="table table-hover mb-0 align-middle">
            <thead class="table-light">
              <tr>
                <th style="min-width:120px">Naam</th>
                <th>Toegevoegd op</th>
                <th class="text-center" style="width:160px">
                  Vragenlijst 1<br><small class="text-muted fw-normal">Intake</small>
                </th>
                <th class="text-center" style="width:160px">
                  Vragenlijst 2<br><small class="text-muted fw-normal">Uitstroom</small>
                </th>
                <th class="text-center" style="width:160px">
                  Vragenlijst 3<br><small class="text-muted fw-normal">Opvolging (3 mnd)</small>
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {% for client in active_clients %}
              <tr>
                <td class="fw-semibold">{{ client.voornaam }}</td>
                <td class="text-muted small">{{ client.aangemaakt_op[:10] if client.aangemaakt_op else '—' }}</td>

                {# VL1 #}
                <td class="text-center">
                  {% if status[client.id][1] %}
                    <a href="{{ url_for('main.vragenlijst_1_view', client_id=client.id) }}"
                       class="vl-badge done">&#10003; Ingevuld</a>
                    <div class="d-flex gap-1 mt-1">
                      <a href="{{ url_for('main.vragenlijst_1_view', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bekijken</a>
                      <a href="{{ url_for('main.vragenlijst_1', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bewerken</a>
                    </div>
                  {% else %}
                    <a href="{{ url_for('main.vragenlijst_1', client_id=client.id) }}"
                       class="vl-badge todo">Nog te doen</a>
                    <a href="{{ url_for('main.vragenlijst_1', client_id=client.id) }}"
                       class="btn btn-outline-secondary btn-sm w-100 mt-1" style="font-size:0.75rem">Invullen</a>
                  {% endif %}
                </td>

                {# VL2 #}
                <td class="text-center">
                  {% if status[client.id][2] %}
                    <a href="{{ url_for('main.vragenlijst_2_view', client_id=client.id) }}"
                       class="vl-badge done">&#10003; Ingevuld</a>
                    <div class="d-flex gap-1 mt-1">
                      <a href="{{ url_for('main.vragenlijst_2_view', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bekijken</a>
                      <a href="{{ url_for('main.vragenlijst_2', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bewerken</a>
                    </div>
                  {% else %}
                    <a href="{{ url_for('main.vragenlijst_2', client_id=client.id) }}"
                       class="vl-badge todo">Nog te doen</a>
                    <a href="{{ url_for('main.vragenlijst_2', client_id=client.id) }}"
                       class="btn btn-outline-secondary btn-sm w-100 mt-1" style="font-size:0.75rem">Invullen</a>
                  {% endif %}
                </td>

                {# VL3 #}
                <td class="text-center">
                  {% if status[client.id][3] %}
                    <a href="{{ url_for('main.vragenlijst_3_view', client_id=client.id) }}"
                       class="vl-badge done">&#10003; Ingevuld</a>
                    <div class="d-flex gap-1 mt-1">
                      <a href="{{ url_for('main.vragenlijst_3_view', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bekijken</a>
                      <a href="{{ url_for('main.vragenlijst_3', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bewerken</a>
                    </div>
                  {% else %}
                    <a href="{{ url_for('main.vragenlijst_3', client_id=client.id) }}"
                       class="vl-badge todo">Nog te doen</a>
                    <a href="{{ url_for('main.vragenlijst_3', client_id=client.id) }}"
                       class="btn btn-outline-secondary btn-sm w-100 mt-1" style="font-size:0.75rem">Invullen</a>
                  {% endif %}
                </td>

                {# Verwijderen #}
                <td>
                  <button type="button" class="btn btn-outline-danger btn-sm"
                          data-bs-toggle="modal" data-bs-target="#del{{ client.id }}">
                    ✕
                  </button>
                </td>
              </tr>

              {# Delete modal #}
              <div class="modal fade" id="del{{ client.id }}" tabindex="-1">
                <div class="modal-dialog modal-sm">
                  <div class="modal-content">
                    <div class="modal-header py-2">
                      <h6 class="modal-title mb-0">Cliënt verwijderen</h6>
                      <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                      Weet u zeker dat u <strong>{{ client.voornaam }}</strong> en alle bijbehorende data wilt verwijderen?
                    </div>
                    <div class="modal-footer py-2">
                      <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Annuleren</button>
                      <form method="post" action="{{ url_for('main.client_delete', client_id=client.id) }}">
                        <button type="submit" class="btn btn-danger btn-sm">Verwijderen</button>
                      </form>
                    </div>
                  </div>
                </div>
              </div>
              {% else %}
              <tr>
                <td colspan="7" class="text-center text-muted py-3">Nog geen actieve deelnemers.</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    {# ── Tab 2: Voltooide deelnemers ────────────────────────────────── #}
    <div class="tab-pane fade" id="tab-voltooid">
      <div class="card">
        <div class="card-body p-0">
          <table class="table table-hover mb-0 align-middle">
            <thead class="table-light">
              <tr>
                <th style="min-width:120px">Naam</th>
                <th>Toegevoegd op</th>
                <th class="text-center" style="width:160px">
                  Vragenlijst 1<br><small class="text-muted fw-normal">Intake</small>
                </th>
                <th class="text-center" style="width:160px">
                  Vragenlijst 2<br><small class="text-muted fw-normal">Uitstroom</small>
                </th>
                <th class="text-center" style="width:160px">
                  Vragenlijst 3<br><small class="text-muted fw-normal">Opvolging (3 mnd)</small>
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {% for client in done_clients %}
              <tr>
                <td class="fw-semibold">{{ client.voornaam }}</td>
                <td class="text-muted small">{{ client.aangemaakt_op[:10] if client.aangemaakt_op else '—' }}</td>

                {# VL1 #}
                <td class="text-center">
                  {% if status[client.id][1] %}
                    <a href="{{ url_for('main.vragenlijst_1_view', client_id=client.id) }}"
                       class="vl-badge done">&#10003; Ingevuld</a>
                    <div class="d-flex gap-1 mt-1">
                      <a href="{{ url_for('main.vragenlijst_1_view', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bekijken</a>
                      <a href="{{ url_for('main.vragenlijst_1', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bewerken</a>
                    </div>
                  {% else %}
                    <a href="{{ url_for('main.vragenlijst_1', client_id=client.id) }}"
                       class="vl-badge todo">Nog te doen</a>
                    <a href="{{ url_for('main.vragenlijst_1', client_id=client.id) }}"
                       class="btn btn-outline-secondary btn-sm w-100 mt-1" style="font-size:0.75rem">Invullen</a>
                  {% endif %}
                </td>

                {# VL2 #}
                <td class="text-center">
                  {% if status[client.id][2] %}
                    <a href="{{ url_for('main.vragenlijst_2_view', client_id=client.id) }}"
                       class="vl-badge done">&#10003; Ingevuld</a>
                    <div class="d-flex gap-1 mt-1">
                      <a href="{{ url_for('main.vragenlijst_2_view', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bekijken</a>
                      <a href="{{ url_for('main.vragenlijst_2', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bewerken</a>
                    </div>
                  {% else %}
                    <a href="{{ url_for('main.vragenlijst_2', client_id=client.id) }}"
                       class="vl-badge todo">Nog te doen</a>
                    <a href="{{ url_for('main.vragenlijst_2', client_id=client.id) }}"
                       class="btn btn-outline-secondary btn-sm w-100 mt-1" style="font-size:0.75rem">Invullen</a>
                  {% endif %}
                </td>

                {# VL3 #}
                <td class="text-center">
                  {% if status[client.id][3] %}
                    <a href="{{ url_for('main.vragenlijst_3_view', client_id=client.id) }}"
                       class="vl-badge done">&#10003; Ingevuld</a>
                    <div class="d-flex gap-1 mt-1">
                      <a href="{{ url_for('main.vragenlijst_3_view', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bekijken</a>
                      <a href="{{ url_for('main.vragenlijst_3', client_id=client.id) }}"
                         class="btn btn-outline-secondary btn-sm flex-grow-1" style="font-size:0.75rem">Bewerken</a>
                    </div>
                  {% else %}
                    <a href="{{ url_for('main.vragenlijst_3', client_id=client.id) }}"
                       class="vl-badge todo">Nog te doen</a>
                    <a href="{{ url_for('main.vragenlijst_3', client_id=client.id) }}"
                       class="btn btn-outline-secondary btn-sm w-100 mt-1" style="font-size:0.75rem">Invullen</a>
                  {% endif %}
                </td>

                {# Verwijderen #}
                <td>
                  <button type="button" class="btn btn-outline-danger btn-sm"
                          data-bs-toggle="modal" data-bs-target="#del{{ client.id }}">
                    ✕
                  </button>
                </td>
              </tr>

              {# Delete modal #}
              <div class="modal fade" id="del{{ client.id }}" tabindex="-1">
                <div class="modal-dialog modal-sm">
                  <div class="modal-content">
                    <div class="modal-header py-2">
                      <h6 class="modal-title mb-0">Cliënt verwijderen</h6>
                      <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                      Weet u zeker dat u <strong>{{ client.voornaam }}</strong> en alle bijbehorende data wilt verwijderen?
                    </div>
                    <div class="modal-footer py-2">
                      <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Annuleren</button>
                      <form method="post" action="{{ url_for('main.client_delete', client_id=client.id) }}">
                        <button type="submit" class="btn btn-danger btn-sm">Verwijderen</button>
                      </form>
                    </div>
                  </div>
                </div>
              </div>
              {% else %}
              <tr>
                <td colspan="7" class="text-center text-muted py-3">Nog geen voltooide deelnemers.</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

  </div>{# end tab-content #}

  {% else %}
  <div class="card">
    <div class="card-body text-center py-5 text-muted">
      <p class="mb-3">Nog geen cliënten toegevoegd.</p>
      <a href="{{ url_for('main.client_add') }}" class="btn btn-primary">+ Eerste cliënt toevoegen</a>
    </div>
  </div>
  {% endif %}
  ```

- [ ] **Step 2: Start the app and verify in browser**

  Run: `python main.py`

  Manual checks:
  1. Open `http://localhost:5000/` — two tabs visible: "Actieve deelnemers" (active) and "Voltooide deelnemers"
  2. Tab 1 shows all clients that are missing at least one vragenlijst
  3. Tab 2 shows clients with all three filled (badge shows count if > 0)
  4. Tab 2 empty state ("Nog geen voltooide deelnemers.") visible when no one is done
  5. Tab 1 empty state ("Nog geen actieve deelnemers.") visible when everyone is done
  6. Global empty state (card + "Eerste cliënt toevoegen") visible when no clients at all
  7. Delete modal opens and works correctly from both tabs
  8. Switching tabs works without page reload

- [ ] **Step 3: Commit**

  ```bash
  git add app/routes.py app/templates/index.html
  git commit -m "feat: split client overview into actief/voltooid tabs"
  ```
