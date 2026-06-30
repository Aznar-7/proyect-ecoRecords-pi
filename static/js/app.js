/* ═══════════════════════════════════════════
   ECO RECORDS — app.js
═══════════════════════════════════════════ */

// ── Estado local ────────────────────────────
const state = {
  playing: false,
  volume: 70,
  lights: 'warm',
  trackName: '—',
  trackSub: '—',
  discTag: '—',
  raggingVolume: false,
}

// ── Referencias al DOM ───────────────────────
const $ = id => document.getElementById(id)

const els = {
  trackName:     $('track-name'),
  trackSub:      $('track-sub'),
  discTag:       $('disc-tag'),
  disc:          $('disc'),
  playBtn:       $('play-btn'),
  playIcon:      $('play-icon'),
  progressFill:  $('progress-fill'),
  progressThumb: $('progress-thumb'),
  timeCurrent:   $('time-current'),
  timeTotal:     $('time-total'),
  volumeSlider:  $('volume-slider'),
  volumeDisplay: $('volume-display'),
  lightsDisplay: $('lights-display'),
}

// ── SVG icons ───────────────────────────────
const ICON_PAUSE = `
  <rect x="6" y="4" width="4" height="16" rx="1.5"/>
  <rect x="14" y="4" width="4" height="16" rx="1.5"/>
`
const ICON_PLAY = `
  <path d="M8 5.14v14l11-7-11-7z"/>
`

// ── Labels de luces ─────────────────────────
const LIGHT_LABELS = {
  off:  'Apagado',
  warm: 'Cálida',
  soft: 'Suave',
}

// ── Cargar estado desde la API ───────────────
async function loadStatus() {
  try {
    const res = await fetch('/api/status')
    if (!res.ok) throw new Error('Error de red')
    const data = await res.json()

    state.playing   = data.playing !== null
    state.volume    = data.volume
    state.lights    = data.lights
    state.trackName = data.playing
      ? capitalize(data.playing) + ' — Vol. 1'
      : 'Sin disco'
    state.trackSub  = data.playing
      ? `Pista ${data.track} de ${data.total_tracks}`
      : 'Apoyá un disco para empezar'
    state.discTag   = data.playing
      ? data.playing.slice(0, 5).toUpperCase()
      : '—'

    renderAll()

  } catch (err) {
    console.warn('No se pudo cargar el estado:', err)
    els.trackName.textContent = 'Sin conexión'
    els.trackSub.textContent  = 'Verificá la red'
  }
}

// ── Render general ───────────────────────────
function renderAll() {
  // Track info
  els.trackName.textContent = state.trackName
  els.trackSub.textContent  = state.trackSub
  els.discTag.textContent   = state.discTag

  // Play/pause
  els.playIcon.innerHTML = state.playing ? ICON_PAUSE : ICON_PLAY
  els.playBtn.setAttribute('aria-label', state.playing ? 'Pausar' : 'Reproducir')

  // Disco — girar o no según estado
  els.disc.classList.toggle('spinning', state.playing)

  // Volumen y luces
  if (!state.draggingVolume) renderVolume(state.volume)
  renderLights(state.lights)
}

// ── Render volumen ───────────────────────────
function renderVolume(val) {
  els.volumeDisplay.textContent = val + '%'
  els.volumeSlider.value = val
  els.volumeSlider.style.background = `linear-gradient(
    to right,
    var(--accent) 0%,
    var(--accent) ${val}%,
    var(--border) ${val}%,
    var(--border) 100%
  )`
}

// ── Render luces ─────────────────────────────
function renderLights(preset) {
  els.lightsDisplay.textContent = LIGHT_LABELS[preset] || preset
  document.querySelectorAll('.light-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === preset)
  })
}

// ── API: cambiar volumen ─────────────────────
async function setVolume(val) {
  state.volume = val
  renderVolume(val)
  try {
    await fetch('/api/volume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ volume: val }),
    })
  } catch (err) {
    console.warn('Error guardando volumen:', err)
  }
}

// ── API: cambiar luces ───────────────────────
async function setLights(preset) {
  state.lights = preset
  renderLights(preset)
  try {
    await fetch('/api/lights', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset }),
    })
  } catch (err) {
    console.warn('Error guardando luces:', err)
  }
}

// ── Evento: play/pause ───────────────────────
els.playBtn.addEventListener('click', () => {
  state.playing = !state.playing
  els.playIcon.innerHTML = state.playing ? ICON_PAUSE : ICON_PLAY
  els.playBtn.setAttribute('aria-label', state.playing ? 'Pausar' : 'Reproducir')
  els.disc.classList.toggle('spinning', state.playing)
})

// ── Evento: volumen slider ───────────────────
els.volumeSlider.addEventListener('mousedown', () => { state.draggingVolume = true })
els.volumeSlider.addEventListener('touchstart', () => { state.draggingVolume = true })

els.volumeSlider.addEventListener('input', function () {
  renderVolume(parseInt(this.value))
})

els.volumeSlider.addEventListener('change', function () {
  state.draggingVolume = false
  setVolume(parseInt(this.value))
})

els.volumeSlider.addEventListener('mouseup', () => { state.draggingVolume = false })
els.volumeSlider.addEventListener('touchend', () => { state.draggingVolume = false })
// ── Evento: luces ────────────────────────────
document.querySelectorAll('.light-btn').forEach(btn => {
  btn.addEventListener('click', () => setLights(btn.dataset.preset))
})

// ── Utilidades ───────────────────────────────
function capitalize(str) {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
}

// ── Polling cada 3 segundos ──────────────────
// Cuando llegue el NFC real, esto va a actualizar la UI automáticamente
setInterval(loadStatus, 3000)

// ── Init ─────────────────────────────────────
loadStatus()
