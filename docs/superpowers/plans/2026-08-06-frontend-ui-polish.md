# Eco Records — Pulido de UI/UX del frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar la sección de Iluminación (frontend + backend, es código muerto), reconstruir la animación de cambio de disco como un slide lateral que no pelee con el giro del vinilo, y arreglar 3 bugs/pulidos menores de la UI existente.

**Architecture:** Todo el trabajo es sobre archivos estáticos vanilla (HTML/CSS/JS sin build step) más un recorte puntual y acotado en `app.py`/`config.json`. La animación de disco anima `#disc-wrapper` (padre) por separado de `#disc` (hijo, que sigue girando via `@keyframes spin` sin que nada JS le toque `transform` inline) — eso es lo que corrige el bug de raíz del intento anterior.

**Tech Stack:** HTML/CSS/JS vanilla, Flask (Python), sin frameworks ni librerías nuevas.

## Global Constraints

- No agregar frameworks JS, librerías de animación, ni build pipeline (spec, sección "No-objetivos").
- No tocar `daemon.py`, control de motor, NFC, GPIO ni audio.
- No cambiar la paleta de colores (`--bg` `#F5EDE0`, `--text-primary` `#2A1F14`, `--accent` `#C4956A`, etc.) ni la tipografía (Playfair Display + Inter).
- El único cambio de backend permitido es eliminar la ruta muerta `/api/lights` y la clave `"lights"` (aprobado explícitamente) — ningún otro endpoint se toca.
- **Adaptación de testing:** este repo no tiene framework de tests para el frontend (vanilla JS/CSS sin test runner) ni para el backend más allá de scripts manuales. No se agrega ninguno — sería contradecir la restricción de "sin dependencias pesadas". Cada tarea usa **verificación manual concreta** (pasos exactos de navegador/consola) en vez de un test automatizado, tal como especifica el spec en su sección "Testing / verificación".
- **Entorno de desarrollo local:** no hay `venv` ni Flask instalados en esta máquina (solo se corre en la Pi en producción). Para verificar el frontend, servir los archivos estáticos con `python -m http.server 8000` desde la raíz del repo (librería estándar, sin dependencias) y abrir `http://localhost:8000/templates/index.html` — los `fetch` a `/api/*` van a fallar (no hay Flask corriendo), lo cual la app ya maneja sin romperse; para probar la UI con datos se maneja el estado directamente desde la consola del navegador contra los objetos globales `state`, `els` y las funciones `renderAll()` / `animateDiscChange()` (el script se carga como `<script src>` normal, no `type="module"`, así que sus declaraciones de nivel superior son accesibles desde la consola). Para el backend, usar `python -m py_compile app.py` y `python -m json.tool config.json` como smoke-test (no requieren Flask instalado).

---

### Task 1: Backend — eliminar `/api/lights` y la clave `lights`

**Files:**
- Modify: `app.py:62-75` (payload de `/api/status`), `app.py:160-169` (ruta `/api/lights`)
- Modify: `config.json:8` (clave `"lights"`)
- Test: manual (ver Step 3) — no hay framework de tests en el repo

**Interfaces:**
- Consumes: nada nuevo.
- Produces: `/api/status` ya no incluye la clave `"lights"` en su JSON; la ruta `/api/lights` deja de existir (404). Ninguna otra tarea depende de este endpoint.

- [ ] **Step 1: Quitar la ruta `/api/lights` de `app.py`**

Reemplazar (nota el comentario y la ruta completos, entre el bloque de `/api/volume` y el de `/api/playpause`):

```python
# ── API: cambiar volumen ──────────────────────
@app.route("/api/volume", methods=["POST"])
def set_volume():
    data = request.get_json()
    volume = int(data.get("volume", 70))
    config = read_config()
    config["volume"] = volume
    write_config(config)
    return jsonify({"ok": True, "volume": volume})

# ── API: cambiar luces ────────────────────────
@app.route("/api/lights", methods=["POST"])
def set_lights():
    data = request.get_json()
    preset = data.get("preset", "warm")
    config = read_config()
    config["lights"] = preset
    write_config(config)
    return jsonify({"ok": True, "lights": preset})

# ── API: comandos de reproducción ─────────────
@app.route("/api/playpause", methods=["POST"])
```

por:

```python
# ── API: cambiar volumen ──────────────────────
@app.route("/api/volume", methods=["POST"])
def set_volume():
    data = request.get_json()
    volume = int(data.get("volume", 70))
    config = read_config()
    config["volume"] = volume
    write_config(config)
    return jsonify({"ok": True, "volume": volume})

# ── API: comandos de reproducción ─────────────
@app.route("/api/playpause", methods=["POST"])
```

- [ ] **Step 2: Quitar `"lights"` del payload de `/api/status`**

Reemplazar:

```python
    return jsonify({
        "playing":      album_display,
        "raw_album":    album_name,
        "track_name":   track_name,
        "track":        now.get("track", 0),
        "total_tracks": now.get("total", 0),
        "is_playing":   now.get("playing", False),
        "elapsed":      now.get("elapsed", 0),
        "duration":     now.get("duration", 0),
        "volume":       config.get("volume", 70),
        "lights":       config.get("lights", "warm"),
        "albums":       list(config.get("albums", {}).values()),
        "pending_uid":  config.get("pending_uid", None)
    })
```

por:

```python
    return jsonify({
        "playing":      album_display,
        "raw_album":    album_name,
        "track_name":   track_name,
        "track":        now.get("track", 0),
        "total_tracks": now.get("total", 0),
        "is_playing":   now.get("playing", False),
        "elapsed":      now.get("elapsed", 0),
        "duration":     now.get("duration", 0),
        "volume":       config.get("volume", 70),
        "albums":       list(config.get("albums", {}).values()),
        "pending_uid":  config.get("pending_uid", None)
    })
```

- [ ] **Step 3: Quitar la clave `"lights"` de `config.json`**

Reemplazar:

```json
  "volume": 66,
  "lights": "warm",
  "command": null,
```

por:

```json
  "volume": 66,
  "command": null,
```

- [ ] **Step 4: Verificar**

Correr (no requieren Flask instalado, son solo stdlib de Python):

```bash
python -m py_compile app.py
python -m json.tool config.json
```

Esperado: ambos comandos terminan sin error (sin output es éxito). Después, confirmar con una búsqueda de texto que no queda ningún `lights` en `app.py` ni `config.json` (por ejemplo abriendo ambos archivos y revisando).

- [ ] **Step 5: Commit**

```bash
git add app.py config.json
git commit -m "fix: eliminar endpoint muerto /api/lights (sin driver de hardware real)"
```

---

### Task 2: Frontend — eliminar toda la UI de Iluminación

**Files:**
- Modify: `templates/index.html` (bloque de Iluminación en `.controls-card`)
- Modify: `static/css/style.css` (`.lights-row`, `.light-btn`, `.light-btn.active`)
- Modify: `static/js/app.js` (`state.lights`, `els.lightsDisplay`, `LIGHT_LABELS`, `renderLights()`, `setLights()`, listener de `.light-btn`, llamadas a `renderLights()`)
- Test: manual (ver Step 6)

**Interfaces:**
- Consumes: nada nuevo.
- Produces: `state` ya no tiene `lights`; `els` ya no tiene `lightsDisplay`; no existen los símbolos `LIGHT_LABELS`, `renderLights`, `setLights`. Ninguna tarea posterior debe referenciarlos.

- [ ] **Step 1: Quitar el bloque de Iluminación de `templates/index.html`**

Reemplazar (dentro de `.controls-card`, justo después del slider de volumen):

```html
      <div class="slider-wrap">
        <input type="range" min="0" max="100" value="70" class="slider" id="volume-slider" aria-label="Volumen">
      </div>
      <div class="divider"></div>
      <div class="control-row">
        <div class="control-label-wrap">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <path d="M9 21h6M12 3a6 6 0 0 1 4.47 10.12A4 4 0 0 0 15 17H9a4 4 0 0 0-1.47-3.88A6 6 0 0 1 12 3z"/>
          </svg>
          <span class="control-label">Iluminación</span>
        </div>
        <span class="control-value accent" id="lights-display">Cálida</span>
      </div>
      <div class="lights-row">
        <button class="light-btn" data-preset="off">Apagado</button>
        <button class="light-btn active" data-preset="warm">Cálida</button>
        <button class="light-btn" data-preset="soft">Suave</button>
      </div>
    </section>
```

por:

```html
      <div class="slider-wrap">
        <input type="range" min="0" max="100" value="70" class="slider" id="volume-slider" aria-label="Volumen">
      </div>
    </section>
```

- [ ] **Step 2: Quitar `.lights-row`/`.light-btn` de `static/css/style.css`**

Reemplazar:

```css
/* ── Lights ────────────────────────────────── */
.lights-row {
  display: flex;
  gap: 8px;
}

.light-btn {
  flex: 1;
  height: 32px;
  border-radius: var(--radius-btn);
  background: var(--bg);
  border: 1px solid var(--border);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  transition: all 0.15s;
}

.light-btn.active {
  background: var(--accent-bg);
  border-color: var(--accent);
  color: var(--accent-dark);
  font-weight: 600;
}
```

por (queda vacío, se quita el bloque completo — el siguiente bloque `/* ── Albums list ... */` pasa a seguir directo después del bloque `/* ── Divider ─...*/`):

*(nada — eliminar todo el bloque anterior sin reemplazo)*

- [ ] **Step 3: Quitar `lights` de `static/js/app.js` — objeto `state`**

Reemplazar:

```js
const state = {
  playing: false,
  volume: 70,
  lights: 'warm',
  trackName: '—',
```

por:

```js
const state = {
  playing: false,
  volume: 70,
  trackName: '—',
```

- [ ] **Step 4: Quitar `lightsDisplay` del objeto `els`**

Reemplazar:

```js
  volumeSlider:   $('volume-slider'),
  volumeDisplay:  $('volume-display'),
  lightsDisplay:  $('lights-display'),
  albumsList:     $('albums-list'),
```

por:

```js
  volumeSlider:   $('volume-slider'),
  volumeDisplay:  $('volume-display'),
  albumsList:     $('albums-list'),
```

- [ ] **Step 5: Quitar `LIGHT_LABELS`**

Reemplazar:

```js
const ICON_PLAY = `<path d="M8 5.14v14l11-7-11-7z"/>`

const LIGHT_LABELS = { off: 'Apagado', warm: 'Cálida', soft: 'Suave' }

// ══════════════════════════════════════════════
// NAVEGACIÓN
```

por:

```js
const ICON_PLAY = `<path d="M8 5.14v14l11-7-11-7z"/>`

// ══════════════════════════════════════════════
// NAVEGACIÓN
```

- [ ] **Step 6: Quitar la asignación de `state.lights` en `loadStatus()`**

Reemplazar:

```js
    if (!state.initialized) state.playing = data.is_playing || false
    state.initialized = true
    state.volume      = data.volume
    state.lights      = data.lights
    state.track       = data.track || 0
    state.totalTracks = data.total_tracks || 0
    state.playing       = data.is_playing || false
```

por:

```js
    if (!state.initialized) state.playing = data.is_playing || false
    state.initialized = true
    state.volume      = data.volume
    state.track       = data.track || 0
    state.totalTracks = data.total_tracks || 0
    state.playing       = data.is_playing || false
```

- [ ] **Step 7: Quitar la llamada a `renderLights('warm')` en `renderInitial()`**

Reemplazar:

```js
function renderInitial() {
  els.trackName.textContent = 'Sin disco apoyado'
  els.trackSub.textContent  = 'Acercá un disco para empezar'
  els.discTag.textContent   = '—'
  renderVolume(70)
  renderLights('warm')
}
```

por:

```js
function renderInitial() {
  els.trackName.textContent = 'Sin disco apoyado'
  els.trackSub.textContent  = 'Acercá un disco para empezar'
  els.discTag.textContent   = '—'
  renderVolume(70)
}
```

- [ ] **Step 8: Quitar la llamada a `renderLights(state.lights)` en `renderAll()`**

Reemplazar:

```js
  if (!state.draggingVolume) renderVolume(state.volume)
  renderLights(state.lights)
  renderProgress()
```

por:

```js
  if (!state.draggingVolume) renderVolume(state.volume)
  renderProgress()
```

- [ ] **Step 9: Quitar la función `renderLights()`**

Reemplazar:

```js
function renderLights(preset) {
  els.lightsDisplay.textContent = LIGHT_LABELS[preset] || preset
  document.querySelectorAll('.light-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === preset)
  })
}
```

por:

*(nada — eliminar la función completa)*

- [ ] **Step 10: Quitar el listener de `.light-btn` y la función `setLights()`**

Reemplazar:

```js
els.volumeSlider.addEventListener('mouseup',  () => { state.draggingVolume = false })
els.volumeSlider.addEventListener('touchend', () => { state.draggingVolume = false })

document.querySelectorAll('.light-btn').forEach(btn => {
  btn.addEventListener('click', () => setLights(btn.dataset.preset))
})

async function setVolume(val) {
  state.volume = val
  try {
    await fetch('/api/volume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ volume: val }),
    })
  } catch (err) { console.warn('Error volumen:', err) }
}

async function setLights(preset) {
  state.lights = preset
  renderLights(preset)
  try {
    await fetch('/api/lights', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset }),
    })
  } catch (err) { console.warn('Error luces:', err) }
}
```

por:

```js
els.volumeSlider.addEventListener('mouseup',  () => { state.draggingVolume = false })
els.volumeSlider.addEventListener('touchend', () => { state.draggingVolume = false })

async function setVolume(val) {
  state.volume = val
  try {
    await fetch('/api/volume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ volume: val }),
    })
  } catch (err) { console.warn('Error volumen:', err) }
}
```

- [ ] **Step 11: Verificar**

Desde la raíz del repo:

```bash
python -m http.server 8000
```

Abrir `http://localhost:8000/templates/index.html` en el navegador. Confirmar:
- La consola no tiene errores (en particular ningún `Cannot read properties of null` referido a `lights-display` o similares).
- La tarjeta de controles solo muestra "Volumen" — no hay fila de Iluminación ni botones Apagado/Cálida/Suave.
- Buscar en los 3 archivos tocados (`templates/index.html`, `static/css/style.css`, `static/js/app.js`) que no quede ningún `light`/`Light`/`luces` (fuera de comentarios de otras secciones no relacionadas).

- [ ] **Step 12: Commit**

```bash
git add templates/index.html static/css/style.css static/js/app.js
git commit -m "feat: eliminar UI de Iluminacion (feature vestigial sin hardware)"
```

---

### Task 3: CSS — tokens de duración/easing

**Files:**
- Modify: `static/css/style.css:6-21` (bloque `:root`)
- Test: manual (ver Step 2)

**Interfaces:**
- Consumes: nada.
- Produces: variables CSS `--ease-out-soft`, `--ease-in-soft`, `--dur-fast`, `--dur-base`, `--dur-slide` disponibles globalmente desde `:root`. Las tareas 6 y 8 las consumen.

- [ ] **Step 1: Agregar los tokens al bloque `:root`**

Reemplazar:

```css
:root {
  --bg:             #F5EDE0;
  --bg-card:        #FFFFFF;
  --bg-muted:       #EDE4D6;
  --border:         #E0D4C4;
  --text-primary:   #2A1F14;
  --text-secondary: #7A6A58;
  --text-muted:     #B0A090;
  --accent:         #C4956A;
  --accent-dark:    #7A4A10;
  --accent-bg:      rgba(196, 149, 106, 0.12);
  --disc-bg:        #0A0705;
  --radius-card:    20px;
  --radius-btn:     11px;
  --shadow-card:    0 1px 3px rgba(42,31,20,0.06), 0 4px 12px rgba(42,31,20,0.04);
}
```

por:

```css
:root {
  --bg:             #F5EDE0;
  --bg-card:        #FFFFFF;
  --bg-muted:       #EDE4D6;
  --border:         #E0D4C4;
  --text-primary:   #2A1F14;
  --text-secondary: #7A6A58;
  --text-muted:     #B0A090;
  --accent:         #C4956A;
  --accent-dark:    #7A4A10;
  --accent-bg:      rgba(196, 149, 106, 0.12);
  --disc-bg:        #0A0705;
  --radius-card:    20px;
  --radius-btn:     11px;
  --shadow-card:    0 1px 3px rgba(42,31,20,0.06), 0 4px 12px rgba(42,31,20,0.04);
  --ease-out-soft:  cubic-bezier(0.34, 1.4, 0.64, 1);
  --ease-in-soft:   cubic-bezier(0.4, 0, 1, 1);
  --dur-fast:       150ms;
  --dur-base:       250ms;
  --dur-slide:      300ms;
}
```

- [ ] **Step 2: Verificar**

Abrir `static/css/style.css` en el navegador vía devtools (o `python -m http.server 8000` + inspeccionar `:root` en la pestaña Elements/Styles) y confirmar que las 5 variables nuevas aparecen con sus valores. No debe haber ningún cambio visual todavía (son variables sin uso aún).

- [ ] **Step 3: Commit**

```bash
git add static/css/style.css
git commit -m "feat: agregar tokens CSS de duracion/easing para animaciones"
```

---

### Task 4: CSS — estado "plato vacío" del disco

**Files:**
- Modify: `static/css/style.css` (después del bloque `.disc-tag`)
- Test: manual (ver Step 2)

**Interfaces:**
- Consumes: nada.
- Produces: clase `.disc.is-empty` (+ overrides de `.disc-grooves`, `.disc-label`, `.disc-dot` dentro de ese contexto). Puramente presentacional — no la usa nadie todavía. Las tareas 5 y 6 la consumen.

- [ ] **Step 1: Agregar la variante `.disc.is-empty`**

Reemplazar:

```css
.disc-tag {
  font-size: 7px;
  color: rgba(196,149,106,0.65);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-weight: 500;
}

/* ── Track info ────────────────────────────── */
```

por:

```css
.disc-tag {
  font-size: 7px;
  color: rgba(196,149,106,0.65);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-weight: 500;
}

/* ── Disco vacío (sin disco físico apoyado) ────── */
.disc.is-empty {
  background: radial-gradient(circle at 38% 35%, #1C140C 0%, #0A0705 100%);
  border-color: rgba(196,149,106,0.08);
}

.disc.is-empty .disc-grooves {
  opacity: 0.25;
}

.disc.is-empty .disc-label {
  opacity: 0.35;
  background: linear-gradient(145deg, #2A1F14, #1C140C);
  border-color: rgba(196,149,106,0.12);
}

.disc.is-empty .disc-dot {
  background: rgba(196,149,106,0.3);
}

/* ── Track info ────────────────────────────── */
```

- [ ] **Step 2: Verificar**

Servir con `python -m http.server 8000`, abrir la página, y en devtools console correr:

```js
document.getElementById('disc').classList.add('is-empty')
```

Confirmar que el disco se ve más oscuro/apagado (grooves y label tenues). Después correr:

```js
document.getElementById('disc').classList.remove('is-empty')
```

y confirmar que vuelve al aspecto normal (vinilo negro con label marcado). Ningún otro elemento de la página debería verse afectado.

- [ ] **Step 3: Commit**

```bash
git add static/css/style.css
git commit -m "feat: agregar estado visual de plato vacio para el disco"
```

---

### Task 5: Fix — flash de ícono inicial y controles habilitados según álbum cargado

**Files:**
- Modify: `templates/index.html` (botones de transporte + clase inicial del disco)
- Modify: `static/css/style.css` (`.play-btn:disabled`)
- Modify: `static/js/app.js` (`renderInitial()`, `renderAll()`)
- Test: manual (ver Step 6)

**Interfaces:**
- Consumes: `.disc.is-empty` (Task 4).
- Produces: `renderInitial()` deja `playBtn`/`prevBtn`/`nextBtn` deshabilitados. `renderAll()` calcula `const hasAlbum = state.totalTracks > 0` y lo usa para habilitar/deshabilitar `playBtn`/`prevBtn`/`nextBtn` y togglear `is-empty` en `#disc` (en vez de basarse en `state.playing`). La Task 6 va a mover el toggle de `is-empty` desde acá hacia `animateDiscChange()` — dejar el nombre de variable `hasAlbum` igual para que ese diff calce.

- [ ] **Step 1: HTML — disco arranca en estado vacío, botones deshabilitados, ícono play por defecto**

Reemplazar:

```html
    <section class="disc-section" aria-label="Disco actual">
      <div class="disc-shadow"></div>
      <div class="disc-wrapper" id="disc-wrapper">
        <div class="disc" id="disc">
```

por:

```html
    <section class="disc-section" aria-label="Disco actual">
      <div class="disc-shadow"></div>
      <div class="disc-wrapper" id="disc-wrapper">
        <div class="disc is-empty" id="disc">
```

- [ ] **Step 2: HTML — botones de transporte deshabilitados y sin flash de ícono pausa**

Reemplazar:

```html
        <div class="player-controls">
          <button class="ctrl-btn" id="prev-btn" aria-label="Anterior">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M19 20L9 12l10-8v16zM5 4h2v16H5z"/>
            </svg>
          </button>
          <button class="play-btn" id="play-btn" aria-label="Pausar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" id="play-icon">
              <rect x="6" y="4" width="4" height="16" rx="1.5"/>
              <rect x="14" y="4" width="4" height="16" rx="1.5"/>
            </svg>
          </button>
          <button class="ctrl-btn" id="next-btn" aria-label="Siguiente">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M5 4l10 8-10 8V4zM19 4h-2v16h2z"/>
            </svg>
          </button>
        </div>
```

por:

```html
        <div class="player-controls">
          <button class="ctrl-btn" id="prev-btn" aria-label="Anterior" disabled>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M19 20L9 12l10-8v16zM5 4h2v16H5z"/>
            </svg>
          </button>
          <button class="play-btn" id="play-btn" aria-label="Reproducir" disabled>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" id="play-icon">
              <path d="M8 5.14v14l11-7-11-7z"/>
            </svg>
          </button>
          <button class="ctrl-btn" id="next-btn" aria-label="Siguiente" disabled>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M5 4l10 8-10 8V4zM19 4h-2v16h2z"/>
            </svg>
          </button>
        </div>
```

- [ ] **Step 3: CSS — estado deshabilitado del botón de play**

Reemplazar:

```css
.ctrl-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
```

por:

```css
.ctrl-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.play-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}
```

- [ ] **Step 4: JS — `renderInitial()` deshabilita los controles**

Reemplazar:

```js
function renderInitial() {
  els.trackName.textContent = 'Sin disco apoyado'
  els.trackSub.textContent  = 'Acercá un disco para empezar'
  els.discTag.textContent   = '—'
  renderVolume(70)
}
```

por:

```js
function renderInitial() {
  els.trackName.textContent = 'Sin disco apoyado'
  els.trackSub.textContent  = 'Acercá un disco para empezar'
  els.discTag.textContent   = '—'
  els.playBtn.disabled = true
  els.prevBtn.disabled = true
  els.nextBtn.disabled = true
  renderVolume(70)
}
```

- [ ] **Step 5: JS — `renderAll()` habilita controles según álbum cargado, no según reproducción**

Reemplazar:

```js
  els.prevBtn.disabled = !state.playing
  els.nextBtn.disabled = !state.playing
}
```

por:

```js
  const hasAlbum = state.totalTracks > 0
  els.disc.classList.toggle('is-empty', !hasAlbum)
  els.playBtn.disabled = !hasAlbum
  els.prevBtn.disabled = !hasAlbum
  els.nextBtn.disabled = !hasAlbum
}
```

- [ ] **Step 6: Verificar**

Servir con `python -m http.server 8000`, abrir la página con la consola abierta.

1. Al cargar: el disco se ve en estado "plato vacío" (oscuro), los 3 botones de transporte se ven atenuados/deshabilitados, y el ícono central es el de "play" (triángulo), nunca el de pausa — confirmar viendo el HTML fuente (Ctrl+U / "ver código fuente") que el SVG ya es el triángulo antes de que corra ningún JS.
2. En consola, simular que llega un álbum:

```js
state.totalTracks = 10
state.playing = false
renderAll()
```

Confirmar que los 3 botones se habilitan (ya no atenuados) a pesar de que `state.playing` es `false`, y que el disco deja el estado "plato vacío". Esto confirma el fix del bug de prev/next bloqueados en pausa.

3. Correr `state.totalTracks = 0; renderAll()` y confirmar que los 3 botones vuelven a deshabilitarse y el disco vuelve a verse "vacío".

- [ ] **Step 7: Commit**

```bash
git add templates/index.html static/css/style.css static/js/app.js
git commit -m "fix: evitar flash de icono inicial y habilitar prev/next segun album cargado, no segun reproduccion"
```

---

### Task 6: Animación de cambio de disco (slide lateral)

**Files:**
- Modify: `static/css/style.css` (`.disc-wrapper` + clases de slide)
- Modify: `static/js/app.js` (`els.discWrapper`, nueva función `animateDiscChange()`, `renderAll()`)
- Test: manual (ver Step 5)

**Interfaces:**
- Consumes: `--dur-base`, `--ease-in-soft`, `--dur-slide`, `--ease-out-soft` (Task 3); `.disc.is-empty` (Task 4); `hasAlbum` block de `renderAll()` (Task 5, se preserva sin tocar salvo la línea de `is-empty` que se muda a `animateDiscChange`).
- Produces: `els.discWrapper` (nuevo). Función global `animateDiscChange(albumId)` — la Task 9 la usa en su checklist de QA manual. Clases CSS `.disc-slide-out`, `.disc-slide-in`, `.disc-teleport` sobre `#disc-wrapper`.

- [ ] **Step 1: CSS — clases de slide sobre `.disc-wrapper`**

Reemplazar:

```css
.disc-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}
```

por:

```css
.disc-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--dur-base) var(--ease-in-soft), opacity var(--dur-base) var(--ease-in-soft);
}

.disc-wrapper.disc-slide-out {
  transform: translateX(-140%);
  opacity: 0;
}

.disc-wrapper.disc-teleport {
  transition: none;
  transform: translateX(140%);
  opacity: 0;
}

.disc-wrapper.disc-slide-in {
  transition: transform var(--dur-slide) var(--ease-out-soft), opacity var(--dur-slide) var(--ease-out-soft);
  transform: translateX(0);
  opacity: 1;
}
```

- [ ] **Step 2: JS — agregar `discWrapper` al objeto `els`**

Reemplazar:

```js
  discTag:        $('disc-tag'),
  disc:           $('disc'),
  playBtn:        $('play-btn'),
```

por:

```js
  discTag:        $('disc-tag'),
  disc:           $('disc'),
  discWrapper:    $('disc-wrapper'),
  playBtn:        $('play-btn'),
```

- [ ] **Step 3: JS — agregar `animateDiscChange()` antes de `renderAll()`**

Reemplazar:

```js
function renderProgress() {
  const pct = state.duration > 0 ? Math.min(100, (state.elapsed / state.duration) * 100) : 0
  els.progressFill.style.width = pct + '%'
  els.progressThumb.style.left = pct + '%'
  els.timeCurrent.textContent  = formatTime(state.elapsed)
  els.timeTotal.textContent    = formatTime(state.duration)
}

function renderAll() {
```

por:

```js
function renderProgress() {
  const pct = state.duration > 0 ? Math.min(100, (state.elapsed / state.duration) * 100) : 0
  els.progressFill.style.width = pct + '%'
  els.progressThumb.style.left = pct + '%'
  els.timeCurrent.textContent  = formatTime(state.elapsed)
  els.timeTotal.textContent    = formatTime(state.duration)
}

// ── Animación de cambio de disco (slide lateral) ──
// Se dispara solo cuando cambia la identidad del álbum (coverAlbumId),
// nunca por cambio de pista dentro del mismo álbum. El wrapper es quien
// anima transform/opacity — #disc nunca recibe transform inline, así
// que su animación de giro (@keyframes spin) nunca se corta ni salta.
let lastAnimatedAlbum
let discAnimTimeouts = []

function clearDiscAnimTimeouts() {
  discAnimTimeouts.forEach(id => clearTimeout(id))
  discAnimTimeouts = []
}

function animateDiscChange(albumId) {
  const wrapper = els.discWrapper

  if (lastAnimatedAlbum === undefined) {
    lastAnimatedAlbum = albumId
    els.disc.classList.toggle('is-empty', !albumId)
    updateDiscCover(albumId)
    return
  }

  if (albumId === lastAnimatedAlbum) return

  if (discAnimTimeouts.length > 0) {
    // Había una transición en curso: la cortamos y saltamos directo
    // al estado final visual, sin animar, antes de arrancar la nueva.
    clearDiscAnimTimeouts()
    wrapper.classList.remove('disc-slide-out', 'disc-slide-in', 'disc-teleport')
    wrapper.style.transition = 'none'
    wrapper.style.transform  = 'translateX(0)'
    wrapper.style.opacity    = '1'
    wrapper.offsetHeight // forzar reflow
    wrapper.style.transition = ''
    wrapper.style.transform  = ''
    wrapper.style.opacity    = ''
  }

  lastAnimatedAlbum = albumId
  wrapper.classList.add('disc-slide-out')

  discAnimTimeouts.push(setTimeout(() => {
    wrapper.classList.remove('disc-slide-out')
    wrapper.classList.add('disc-teleport')
    els.disc.classList.toggle('is-empty', !albumId)
    updateDiscCover(albumId)
    wrapper.offsetHeight // forzar reflow
    wrapper.classList.remove('disc-teleport')
    wrapper.classList.add('disc-slide-in')
    discAnimTimeouts = []
  }, 250))
}

function renderAll() {
```

- [ ] **Step 4: JS — `renderAll()` usa `animateDiscChange()` en vez de `updateDiscCover()` directo, y deja de togglear `is-empty` ahí (lo hace `animateDiscChange`)**

Reemplazar:

```js
function renderAll() {
  updateDiscCover(state.coverAlbumId)
```

por:

```js
function renderAll() {
  animateDiscChange(state.coverAlbumId)
```

Y por separado, reemplazar:

```js
  const hasAlbum = state.totalTracks > 0
  els.disc.classList.toggle('is-empty', !hasAlbum)
  els.playBtn.disabled = !hasAlbum
```

por:

```js
  const hasAlbum = state.totalTracks > 0
  els.playBtn.disabled = !hasAlbum
```

- [ ] **Step 5: Verificar**

Servir con `python -m http.server 8000`, abrir con la consola abierta.

1. Primer disco (sin animación, es la carga inicial):

```js
state.coverAlbumId = 'thriller'
animateDiscChange(state.coverAlbumId)
```

Confirmar que no hay ningún slide — el disco pasa directo de "vacío" a mostrar el tag/cover (el fetch del cover a `/api/albums/thriller/cover` va a fallar sin backend, eso es esperado y no debe tirar error en consola más allá de un 404 de red).

2. Cambio de álbum (acá sí debe animar):

```js
els.disc.classList.add('spinning')
state.coverAlbumId = 'paranoid'
animateDiscChange(state.coverAlbumId)
```

Confirmar visualmente: el disco desliza hacia la izquierda desangrándose (~250ms), reaparece desde la derecha y se asienta con un pequeño rebote (~300ms) — y que en ningún momento el giro (la rotación continua de `spinning`) se corta, salta o tartamudea durante la transición.

3. Interrupción — disparar dos cambios seguidos sin esperar a que termine el primero:

```js
state.coverAlbumId = '02-09'
animateDiscChange(state.coverAlbumId)
state.coverAlbumId = 'thriller'
animateDiscChange(state.coverAlbumId)
```

Confirmar que el disco termina visible, centrado, con opacidad 1 (no se queda a mitad de camino ni desaparecido) una vez que las animaciones se asientan.

4. Repetir el mismo álbum no debe animar nada:

```js
animateDiscChange('thriller')
```

Sin efecto visual (ya es el álbum actual).

- [ ] **Step 6: Commit**

```bash
git add static/css/style.css static/js/app.js
git commit -m "feat: animacion de cambio de disco (slide lateral) sin pelear con el giro"
```

---

### Task 7: Cierre simétrico de modales

**Files:**
- Modify: `static/css/style.css` (después de `@keyframes card-up`)
- Modify: `static/js/app.js` (handlers de `settings-modal` y `learn-modal`)
- Test: manual (ver Step 4)

**Interfaces:**
- Consumes: nada de tareas anteriores (región independiente del archivo).
- Produces: función global `closeModal(modalEl)`. Clases CSS `.modal-overlay.closing` + `@keyframes modal-out` / `card-down`.

- [ ] **Step 1: CSS — animación de cierre**

Reemplazar:

```css
.modal-card {
  background: var(--bg);
  border-radius: 24px;
  padding: 28px 24px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  animation: card-up 0.3s ease forwards;
}

@keyframes card-up {
  from { transform: translateY(40px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}
```

por:

```css
.modal-card {
  background: var(--bg);
  border-radius: 24px;
  padding: 28px 24px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  animation: card-up 0.3s ease forwards;
}

@keyframes card-up {
  from { transform: translateY(40px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}

.modal-overlay.closing {
  animation: modal-out 180ms ease forwards;
}

.modal-overlay.closing .modal-card {
  animation: card-down 180ms ease forwards;
}

@keyframes modal-out {
  from { opacity: 1; }
  to   { opacity: 0; }
}

@keyframes card-down {
  from { transform: translateY(0);    opacity: 1; }
  to   { transform: translateY(40px); opacity: 0; }
}
```

- [ ] **Step 2: JS — `closeModal()` + modal de ajustes**

Reemplazar:

```js
document.getElementById('settings-btn').addEventListener('click', () => {
  document.getElementById('settings-volume-label').textContent = state.volume + '%'
  document.getElementById('settings-modal').style.display = 'flex'
})

document.getElementById('settings-close').addEventListener('click', () => {
  document.getElementById('settings-modal').style.display = 'none'
})

document.getElementById('shutdown-btn').addEventListener('click', async () => {
  const btn = document.getElementById('shutdown-btn')
  btn.textContent = 'Apagando...'
  btn.disabled    = true
  try {
    await fetch('/api/shutdown', { method: 'POST' })
    btn.textContent = 'Apagado — esperá 10 seg y desenchufá'
    setTimeout(() => {
      document.getElementById('settings-modal').style.display = 'none'
    }, 8000)
  } catch (err) {
    btn.textContent = 'Error al apagar'
    btn.disabled     = false
  }
})
```

por:

```js
function closeModal(modalEl) {
  modalEl.classList.add('closing')
  setTimeout(() => {
    modalEl.style.display = 'none'
    modalEl.classList.remove('closing')
  }, 180)
}

document.getElementById('settings-btn').addEventListener('click', () => {
  const modal = document.getElementById('settings-modal')
  modal.classList.remove('closing')
  document.getElementById('settings-volume-label').textContent = state.volume + '%'
  modal.style.display = 'flex'
})

document.getElementById('settings-close').addEventListener('click', () => {
  closeModal(document.getElementById('settings-modal'))
})

document.getElementById('shutdown-btn').addEventListener('click', async () => {
  const btn = document.getElementById('shutdown-btn')
  btn.textContent = 'Apagando...'
  btn.disabled    = true
  try {
    await fetch('/api/shutdown', { method: 'POST' })
    btn.textContent = 'Apagado — esperá 10 seg y desenchufá'
    setTimeout(() => {
      closeModal(document.getElementById('settings-modal'))
    }, 8000)
  } catch (err) {
    btn.textContent = 'Error al apagar'
    btn.disabled     = false
  }
})
```

- [ ] **Step 3: JS — modal de "disco nuevo"**

Reemplazar:

```js
async function showLearnModal(uid) {
  document.getElementById('modal-uid').textContent = uid
  const select = document.getElementById('modal-album-select')
  select.innerHTML = '<option value="">Elegir álbum...</option>'
  try {
    const res    = await fetch('/api/albums')
    const albums = await res.json()
    albums.forEach(album => {
      const opt = document.createElement('option')
      opt.value = album.id
      opt.textContent = album.name
      select.appendChild(opt)
    })
  } catch (err) { console.warn('Error cargando álbumes:', err) }
  document.getElementById('learn-modal').style.display = 'flex'
}

function hideLearnModal() {
  document.getElementById('learn-modal').style.display = 'none'
  document.getElementById('modal-album-select').value  = ''
  pendingUid = null
}
```

por:

```js
async function showLearnModal(uid) {
  document.getElementById('modal-uid').textContent = uid
  const select = document.getElementById('modal-album-select')
  select.innerHTML = '<option value="">Elegir álbum...</option>'
  try {
    const res    = await fetch('/api/albums')
    const albums = await res.json()
    albums.forEach(album => {
      const opt = document.createElement('option')
      opt.value = album.id
      opt.textContent = album.name
      select.appendChild(opt)
    })
  } catch (err) { console.warn('Error cargando álbumes:', err) }
  const modal = document.getElementById('learn-modal')
  modal.classList.remove('closing')
  modal.style.display = 'flex'
}

function hideLearnModal() {
  closeModal(document.getElementById('learn-modal'))
  document.getElementById('modal-album-select').value  = ''
  pendingUid = null
}
```

- [ ] **Step 4: Verificar**

Servir con `python -m http.server 8000`, abrir con la consola abierta.

1. Click en el ícono de ajustes (engranaje) → confirmar que el modal abre con el slide-up de siempre. Click en "Cerrar" → confirmar que ahora el overlay se desvanece y la tarjeta desliza hacia abajo (~180ms) antes de desaparecer, en vez de desaparecer de golpe.
2. En consola: `showLearnModal('AA:BB:CC:DD')` → confirmar que abre. Click en "Cancelar" → confirmar el mismo fade-out/slide-down simétrico.

- [ ] **Step 5: Commit**

```bash
git add static/css/style.css static/js/app.js
git commit -m "feat: cierre animado simetrico de modales (settings y disco nuevo)"
```

---

### Task 8: Crossfade de texto al cambiar de pista

**Files:**
- Modify: `static/css/style.css` (`.track-name`, `.track-sub`)
- Modify: `static/js/app.js` (`renderTrackText()`, `renderAll()`)
- Test: manual (ver Step 4)

**Interfaces:**
- Consumes: `--dur-fast` (Task 3); estructura de `renderAll()` post-Task 6 (las líneas de `trackName`/`trackSub` quedan intactas por las tareas 5 y 6, así que el anchor de este diff es estable).
- Produces: función global `renderTrackText()`, variable `lastDisplayedTrackName`, clase CSS `.text-fade`.

- [ ] **Step 1: CSS — transición de opacidad en el texto de pista**

Reemplazar:

```css
.track-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.track-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 3px;
  font-weight: 400;
}
```

por:

```css
.track-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity var(--dur-fast) ease;
}

.track-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 3px;
  font-weight: 400;
  transition: opacity var(--dur-fast) ease;
}

.track-name.text-fade,
.track-sub.text-fade {
  opacity: 0;
}
```

- [ ] **Step 2: JS — agregar `renderTrackText()` antes de `renderAll()`**

Reemplazar:

```js
    discAnimTimeouts = []
  }, 250))
}

function renderAll() {
```

por:

```js
    discAnimTimeouts = []
  }, 250))
}

// ── Crossfade de texto al cambiar de pista ────────
let lastDisplayedTrackName

function renderTrackText() {
  if (lastDisplayedTrackName === undefined) {
    lastDisplayedTrackName = state.trackName
    els.trackName.textContent = state.trackName
    els.trackSub.textContent  = state.trackSub
    return
  }

  if (state.trackName === lastDisplayedTrackName) return
  lastDisplayedTrackName = state.trackName

  els.trackName.classList.add('text-fade')
  els.trackSub.classList.add('text-fade')

  setTimeout(() => {
    els.trackName.textContent = state.trackName
    els.trackSub.textContent  = state.trackSub
    els.trackName.classList.remove('text-fade')
    els.trackSub.classList.remove('text-fade')
  }, 150)
}

function renderAll() {
```

- [ ] **Step 3: JS — usar `renderTrackText()` en `renderAll()`**

Reemplazar:

```js
  els.trackName.textContent = state.trackName
  els.trackSub.textContent  = state.trackSub
  els.discTag.textContent   = state.discTag
```

por:

```js
  renderTrackText()
  els.discTag.textContent   = state.discTag
```

- [ ] **Step 4: Verificar**

Servir con `python -m http.server 8000`, abrir con la consola abierta.

```js
state.trackName = 'Track A'
state.trackSub  = 'Álbum X · Pista 1 de 10'
renderAll()
```

Confirmar que el texto aparece directo (primer render, sin fundido). Después:

```js
state.trackName = 'Track B'
state.trackSub  = 'Álbum X · Pista 2 de 10'
renderAll()
```

Confirmar que el texto se desvanece, cambia, y vuelve a aparecer (~300ms total) en vez de reemplazarse de golpe. Repetir con el mismo valor (`renderAll()` de nuevo sin cambiar `state.trackName`) y confirmar que no dispara ningún fundido.

- [ ] **Step 5: Commit**

```bash
git add static/css/style.css static/js/app.js
git commit -m "feat: crossfade de texto al cambiar de pista"
```

---

### Task 9: Polling a 700ms + QA final de todo el pulido

**Files:**
- Modify: `static/js/app.js:setInterval(loadStatus, 500)`
- Test: manual (ver Step 2, checklist completo del spec)

**Interfaces:**
- Consumes: todo lo de las tareas 1-8 (verificación de integración final).
- Produces: `setInterval(loadStatus, 700)`.

- [ ] **Step 1: JS — subir el intervalo de polling**

Reemplazar:

```js
renderInitial()
loadStatus()
setInterval(loadStatus, 500)
```

por:

```js
renderInitial()
loadStatus()
setInterval(loadStatus, 700)
```

- [ ] **Step 2: QA final — checklist completo**

Backend (sin necesidad de Flask instalado):

```bash
python -m py_compile app.py
python -m json.tool config.json
```

Ambos sin error.

Búsqueda de texto residual — abrir `app.py`, `config.json`, `templates/index.html`, `static/css/style.css`, `static/js/app.js` y confirmar que ninguno contiene `light`, `Light`, `luces` ni `Iluminaci` (fuera de este plan/spec, que no se tocan).

Frontend — servir con `python -m http.server 8000`, abrir `http://localhost:8000/templates/index.html` con la consola abierta y recorrer, en orden:

1. **Carga fresca:** sin flash de ícono pausa, disco en "plato vacío", los 3 botones de transporte deshabilitados.
2. **Álbum cargado:**
   ```js
   state.totalTracks = 10
   state.coverAlbumId = 'thriller'
   state.trackName = 'Track 1'
   state.trackSub = 'Thriller · Pista 1 de 10'
   state.playing = true
   renderAll()
   ```
   Confirmar: controles habilitados, disco sale del estado vacío (sin animación, es la primera carga), gira (`spinning`).
3. **Cambio de álbum:**
   ```js
   state.coverAlbumId = 'paranoid'
   state.trackName = 'War Pigs'
   state.trackSub = 'Paranoid · Pista 1 de 8'
   renderAll()
   ```
   Confirmar: el disco hace el slide lateral completo, y el giro no se corta durante la transición.
4. **Cambio de pista dentro del mismo álbum:**
   ```js
   state.trackName = 'Paranoid'
   state.trackSub = 'Paranoid · Pista 2 de 8'
   renderAll()
   ```
   Confirmar: NO dispara el slide del disco, solo el crossfade de texto.
5. **Pausa no bloquea skip:**
   ```js
   state.playing = false
   renderAll()
   ```
   Confirmar: prev/next/play siguen habilitados (`hasAlbum` sigue siendo `true`).
6. **Modales:** abrir y cerrar `settings-modal` (botón de ajustes) y `learn-modal` (`showLearnModal('AA:BB:CC')` + botón Cancelar) — confirmar el fade-out/slide-down simétrico en ambos casos.

Si algún paso falla, no continuar — volver a la tarea correspondiente y corregir antes de dar por cerrado el trabajo.

- [ ] **Step 3: Commit**

```bash
git add static/js/app.js
git commit -m "chore: subir intervalo de polling a 700ms"
```

---

## Self-Review

**Cobertura del spec:**
- Sección 1 (Iluminación) → Tasks 1 y 2. ✓
- Sección 2 (animación de disco: arquitectura wrapper/hijo, disparo por álbum, secuencia slide, interrupción, plato vacío) → Tasks 3, 4, 6. ✓
- Sección 3 (bugs: prev/next, flash de ícono) → Task 5. ✓ (el tercer "bug", disparo por pista vs. álbum, queda resuelto por diseño en `animateDiscChange` de Task 6, que compara por `coverAlbumId`.)
- Sección 4 (pulido menor: cierre de modales, crossfade de texto, tokens, polling) → Tasks 3, 7, 8, 9. ✓
- "Archivos afectados" del spec → todos cubiertos (`templates/index.html`, `static/css/style.css`, `static/js/app.js`, `app.py`, `config.json`). ✓
- "Testing / verificación" del spec → cada ítem de esa lista aparece como paso concreto en el checklist de Task 9 Step 2. ✓

**Placeholders:** ninguno — cada step tiene el código exacto a reemplazar, sin "TODO"/"similar a la tarea N"/descripciones sin código.

**Consistencia de nombres:** `animateDiscChange(albumId)` (Task 6) es llamada exactamente así desde `renderAll()` (Task 6, Step 4) y referenciada igual en el QA de Task 9. `renderTrackText()` (Task 8) coincide en ambos lugares. `closeModal(modalEl)` (Task 7) se usa igual en los 3 call-sites (`settings-close`, `shutdown-btn`, `hideLearnModal`). `hasAlbum` se introduce en Task 5 y se seguye usando igual en Task 6 sin renombrar. `els.discWrapper` se define en Task 6 Step 2 y se usa en el mismo task (no lo consume ninguna otra tarea).
