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
  track: 0,
  totalTracks: 0,
  draggingVolume: false,
  currentView: 'home',
  initialized: false,
}

// ── Referencias al DOM ───────────────────────
const $ = id => document.getElementById(id)

const els = {
  trackName:      $('track-name'),
  trackSub:       $('track-sub'),
  discTag:        $('disc-tag'),
  disc:           $('disc'),
  playBtn:        $('play-btn'),
  playIcon:       $('play-icon'),
  prevBtn:        $('prev-btn'),
  nextBtn:        $('next-btn'),
  progressFill:   $('progress-fill'),
  progressThumb:  $('progress-thumb'),
  timeCurrent:    $('time-current'),
  timeTotal:      $('time-total'),
  volumeSlider:   $('volume-slider'),
  volumeDisplay:  $('volume-display'),
  lightsDisplay:  $('lights-display'),
  albumsList:     $('albums-list'),
  albumName:      $('album-name'),
  trackFiles:     $('track-files'),
  fileLabelText:  $('file-label-text'),
  fileList:       $('file-list'),
  uploadFeedback: $('upload-feedback'),
  uploadBtn:      $('upload-btn'),
}

// ── SVG icons ───────────────────────────────
const ICON_PAUSE = `
  <rect x="6" y="4" width="4" height="16" rx="1.5"/>
  <rect x="14" y="4" width="4" height="16" rx="1.5"/>
`
const ICON_PLAY = `<path d="M8 5.14v14l11-7-11-7z"/>`

const LIGHT_LABELS = { off: 'Apagado', warm: 'Cálida', soft: 'Suave' }

// ══════════════════════════════════════════════
// NAVEGACIÓN
// ══════════════════════════════════════════════
function navigateTo(view) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'))
  document.getElementById('view-' + view).classList.add('active')
  document.querySelectorAll('.nav-item').forEach(btn => {
    const isActive = btn.dataset.view === view
    btn.classList.toggle('active', isActive)
    btn.querySelector('.nav-icon-wrap').classList.toggle('active', isActive)
  })
  state.currentView = view
  if (view === 'discos') loadAlbums()
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => navigateTo(btn.dataset.view))
})

// ══════════════════════════════════════════════
// VISTA: INICIO
// ══════════════════════════════════════════════

// ══════════════════════════════════════════════
// MODAL: AJUSTES
// ══════════════════════════════════════════════
document.getElementById('settings-btn').addEventListener('click', () => {
  document.getElementById('settings-volume-label').textContent = state.volume + '%'
  document.getElementById('settings-modal').style.display = 'flex'
})

document.getElementById('settings-close').addEventListener('click', () => {
  document.getElementById('settings-modal').style.display = 'none'
})

document.getElementById('shutdown-btn').addEventListener('click', async () => {
  const btn = document.getElementById('shutdown-btn')
  btn.textContent   = 'Apagando...'
  btn.disabled      = true

  try {
    await fetch('/api/shutdown', { method: 'POST' })
    btn.textContent = '✓ Apagado — esperá 10 seg y desenchufá'
    setTimeout(() => {
      document.getElementById('settings-modal').style.display = 'none'
    }, 8000)
  } catch (err) {
    btn.textContent  = 'Error al apagar'
    btn.disabled     = false
  }
})

// ══════════════════════════════════════════════
// MODAL: APRENDER DISCO NUEVO
// ══════════════════════════════════════════════
let pendingUid = null

async function checkPendingUid() {
  try {
    const res  = await fetch('/api/pending')
    const data = await res.json()

    if (data.uid && data.uid !== pendingUid) {
      pendingUid = data.uid
      showLearnModal(data.uid)
    } else if (!data.uid && pendingUid) {
      pendingUid = null
      hideLearnModal()
    }
  } catch (err) {
    console.warn('Error chequeando UID pendiente:', err)
  }
}

async function showLearnModal(uid) {
  // Mostrar el UID
  document.getElementById('modal-uid').textContent = uid

  // Cargar álbumes disponibles en el select
  const select = document.getElementById('modal-album-select')
  select.innerHTML = '<option value="">Elegir álbum...</option>'

  try {
    const res    = await fetch('/api/albums')
    const albums = await res.json()
    albums.forEach(album => {
      const opt   = document.createElement('option')
      opt.value   = album.id
      opt.textContent = album.name
      select.appendChild(opt)
    })
  } catch (err) {
    console.warn('Error cargando álbumes:', err)
  }

  document.getElementById('learn-modal').style.display = 'flex'
}

function hideLearnModal() {
  document.getElementById('learn-modal').style.display = 'none'
  document.getElementById('modal-album-select').value  = ''
  pendingUid = null
}

// Botón cancelar
document.getElementById('modal-cancel').addEventListener('click', async () => {
  try {
    await fetch('/api/pending/discard', { method: 'POST' })
  } catch (err) {}
  hideLearnModal()
})

// Botón confirmar
document.getElementById('modal-confirm').addEventListener('click', async () => {
  const album = document.getElementById('modal-album-select').value
  if (!album) {
    document.getElementById('modal-album-select').style.borderColor = 'var(--accent)'
    return
  }

  try {
    const res  = await fetch('/api/learn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uid: pendingUid, album }),
    })
    const data = await res.json()

    if (data.ok) {
      hideLearnModal()
      // Recargar estado para que empiece a sonar
      loadStatus()
    }
  } catch (err) {
    console.warn('Error asociando disco:', err)
  }
})

async function loadStatus() {
  try {
    const res = await fetch('/api/status')
    if (!res.ok) throw new Error('Error de red')
    const data = await res.json()

    if (!state.initialized) {
      state.playing = data.is_playing || false
    }
    state.initialized = true
    state.volume      = data.volume
    state.lights      = data.lights
    state.track       = data.track || 0
    state.totalTracks = data.total_tracks || 0

    state.trackName = data.track_name
      ? data.track_name
      : data.playing
      ? data.playing
      : 'Sin disco apoyado'
    state.trackSub  = data.playing && data.total_tracks > 0
      ? `${data.playing} · Pista ${data.track} de ${data.total_tracks}`
      : data.playing
      ? data.playing
      : 'Acercá un disco para empezar'
    state.discTag   = data.playing
      ? data.playing.slice(0, 5).toUpperCase()
      : '—'

    renderAll()
  } catch (err) {
    console.warn('Sin conexión:', err)
    els.trackName.textContent = 'Sin conexión'
    els.trackSub.textContent  = 'Verificá la red'
  }
}

function renderInitial() {
  els.trackName.textContent = 'Sin disco apoyado'
  els.trackSub.textContent  = 'Acercá un disco para empezar'
  els.discTag.textContent   = '—'
  renderVolume(70)
  renderLights('warm')
}

function renderAll() {
  els.trackName.textContent = state.trackName
  els.trackSub.textContent  = state.trackSub
  els.discTag.textContent   = state.discTag
  els.playIcon.innerHTML    = state.playing ? ICON_PAUSE : ICON_PLAY
  els.playBtn.setAttribute('aria-label', state.playing ? 'Pausar' : 'Reproducir')
  els.disc.classList.toggle('spinning', state.playing)
  if (!state.draggingVolume) renderVolume(state.volume)
  renderLights(state.lights)

  // Deshabilitar skip si no hay nada sonando
  els.prevBtn.disabled = !state.playing
  els.nextBtn.disabled = !state.playing
}

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

function renderLights(preset) {
  els.lightsDisplay.textContent = LIGHT_LABELS[preset] || preset
  document.querySelectorAll('.light-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === preset)
  })
}

// ── Eventos: play/pause ──────────────────────
els.playBtn.addEventListener('click', () => {
  state.playing = !state.playing
  els.playIcon.innerHTML = state.playing ? ICON_PAUSE : ICON_PLAY
  els.playBtn.setAttribute('aria-label', state.playing ? 'Pausar' : 'Reproducir')
  els.disc.classList.toggle('spinning', state.playing)
  els.prevBtn.disabled = !state.playing
  els.nextBtn.disabled = !state.playing
})

// ── Eventos: skip ────────────────────────────
els.prevBtn.addEventListener('click', () => {
  if (!state.playing || !state.totalTracks) return
  state.track = Math.max(1, state.track - 1)
  els.trackSub.textContent = `Pista ${state.track} de ${state.totalTracks}`
})

els.nextBtn.addEventListener('click', () => {
  if (!state.playing || !state.totalTracks) return
  state.track = Math.min(state.totalTracks, state.track + 1)
  els.trackSub.textContent = `Pista ${state.track} de ${state.totalTracks}`
})

// ── Eventos: volumen ─────────────────────────
els.volumeSlider.addEventListener('mousedown',  () => { state.draggingVolume = true })
els.volumeSlider.addEventListener('touchstart', () => { state.draggingVolume = true }, { passive: true })

els.volumeSlider.addEventListener('input', function () {
  renderVolume(parseInt(this.value))
})

els.volumeSlider.addEventListener('change', function () {
  state.draggingVolume = false
  setVolume(parseInt(this.value))
})

els.volumeSlider.addEventListener('mouseup',  () => { state.draggingVolume = false })
els.volumeSlider.addEventListener('touchend', () => { state.draggingVolume = false })

// ── Eventos: luces ───────────────────────────
document.querySelectorAll('.light-btn').forEach(btn => {
  btn.addEventListener('click', () => setLights(btn.dataset.preset))
})

// ── APIs ─────────────────────────────────────
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

// ══════════════════════════════════════════════
// VISTA: DISCOS
// ══════════════════════════════════════════════
async function loadAlbums() {
  els.albumsList.innerHTML = `
    ${[1,2,3].map(() => `
      <div class="skeleton-card">
        <div class="skeleton skeleton-disc"></div>
        <div style="flex:1">
          <div class="skeleton skeleton-text wide"></div>
          <div class="skeleton skeleton-text narrow"></div>
        </div>
      </div>
    `).join('')}
  `

  try {
    const res    = await fetch('/api/albums')
    const albums = await res.json()

    if (albums.length === 0) {
      els.albumsList.innerHTML = `
        <div class="albums-empty">
          <div class="albums-empty-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>
            </svg>
          </div>
          <p class="albums-empty-title">Todavía no hay discos</p>
          <p class="albums-empty-sub">Subí tu primer álbum desde<br>la sección Agregar</p>
        </div>
      `
      return
    }
    
    els.albumsList.innerHTML = ''
    albums.forEach(album => {
      const card = document.createElement('div')
      card.className = 'album-card'
      card.innerHTML = `
        <div class="album-disc">
          <div class="album-disc-dot"></div>
        </div>
        <div class="album-info">
          <p class="album-name">${album.name}</p>
          <p class="album-tracks">${album.tracks} ${album.tracks === 1 ? 'pista' : 'pistas'}</p>
        </div>
        <svg class="album-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M9 18l6-6-6-6"/>
        </svg>
      `
      // Click abre el detalle del álbum
      card.addEventListener('click', () => showAlbumDetail(album))
      els.albumsList.appendChild(card)
    })

  } catch (err) {
    els.albumsList.innerHTML = `
      <div class="albums-empty">
        <p class="albums-empty-title">Error cargando álbumes</p>
        <p class="albums-empty-sub">Verificá la conexión</p>
      </div>
    `
  }
}

// ── Detalle de álbum ─────────────────────────
async function showAlbumDetail(album) {
  // Crear vista de detalle dinámicamente
  let detail = $('view-album-detail')
  if (!detail) {
    detail = document.createElement('div')
    detail.id = 'view-album-detail'
    detail.className = 'view'
    document.querySelector('body').insertBefore(detail, document.querySelector('.bottom-nav'))
  }

  detail.innerHTML = `
    <header class="app-header">
      <button class="back-btn" id="back-btn" aria-label="Volver">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M19 12H5M12 5l-7 7 7 7"/>
        </svg>
      </button>
      <div class="app-title">
        <p class="app-label">Álbum</p>
        <h1 class="app-name serif">${album.name}</h1>
      </div>
    </header>

    <div class="album-detail-disc">
      <div class="disc disc-small">
        <div class="disc-grooves"></div>
        <div class="disc-label">
          <div class="disc-dot"></div>
          <span class="disc-tag">${album.name.slice(0, 5).toUpperCase()}</span>
        </div>
      </div>
      <p class="album-detail-count">${album.tracks} pistas</p>
    </div>

    <div class="tracks-list" id="tracks-list">
      <div class="tracks-loading">Cargando pistas...</div>
    </div>
  `

  navigateTo('album-detail')

  // Cargar pistas del álbum
  try {
    // Mostrar skeleton de pistas
    $('tracks-list').innerHTML = `
      ${[1,2,3,4,5].map((_, i) => `
        <div class="track-item">
          <div class="skeleton" style="width:20px; height:14px; border-radius:4px;"></div>
          <div class="skeleton skeleton-text" style="flex:1; width:${60 + i * 8}%"></div>
          <div class="skeleton" style="width:30px; height:12px; border-radius:4px;"></div>
        </div>
      `).join('')}
    `

    const res    = await fetch(`/api/albums/${album.id}/tracks`)
    const tracks = await res.json()
    const list   = $('tracks-list')

    list.innerHTML = tracks.map((track, i) => `
      <div class="track-item">
        <span class="track-num">${String(i + 1).padStart(2, '0')}</span>
        <span class="track-item-name">${track.name}</span>
        <span class="track-item-duration">${track.duration || '—'}</span>
      </div>
    `).join('')
  } catch (err) {
    $('tracks-list').innerHTML = '<div class="tracks-loading">Error cargando pistas</div>'
  }
  // Botón volver
  $('back-btn').addEventListener('click', () => navigateTo('discos'))
}

// ══════════════════════════════════════════════
// VISTA: AGREGAR
// ══════════════════════════════════════════════
els.trackFiles.addEventListener('change', function () {
  const files = Array.from(this.files)
  if (files.length === 0) {
    els.fileLabelText.textContent = 'Elegir archivos de audio'
    els.fileList.style.display = 'none'
    return
  }
  els.fileLabelText.textContent = `${files.length} archivo${files.length > 1 ? 's' : ''} seleccionado${files.length > 1 ? 's' : ''}`
  els.fileList.style.display = 'block'
  els.fileList.innerHTML = files.map(f => `
    <div class="file-item">
      <svg class="file-item-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
      </svg>
      ${f.name}
    </div>
  `).join('')
})

els.uploadBtn.addEventListener('click', async () => {
  const albumName = els.albumName.value.trim()
  const files     = els.trackFiles.files

  if (!albumName) {
    showFeedback('Escribí el nombre del álbum primero', 'error')
    els.albumName.focus()
    return
  }
  if (files.length === 0) {
    showFeedback('Seleccioná al menos un archivo de audio', 'error')
    return
  }

  els.uploadBtn.disabled     = true
  els.uploadBtn.textContent  = 'Subiendo...'

  try {
    const formData = new FormData()
    formData.append('album_name', albumName)
    Array.from(files).forEach(f => formData.append('tracks', f))

    const res  = await fetch('/api/upload', { method: 'POST', body: formData })
    const data = await res.json()

    if (data.ok) {
      showFeedback(`✓ "${albumName}" subido — ${data.tracks_saved} pista${data.tracks_saved !== 1 ? 's' : ''}`, 'success')
      els.albumName.value           = ''
      els.trackFiles.value          = ''
      els.fileLabelText.textContent = 'Elegir archivos de audio'
      els.fileList.style.display    = 'none'
    } else {
      showFeedback('Error: ' + (data.error || 'algo salió mal'), 'error')
    }
  } catch (err) {
    showFeedback('Error de conexión al subir', 'error')
  } finally {
    els.uploadBtn.disabled   = false
    els.uploadBtn.innerHTML  = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      Subir álbum
    `
  }
})

function showFeedback(msg, type) {
  els.uploadFeedback.textContent   = msg
  els.uploadFeedback.className     = `upload-feedback ${type}`
  els.uploadFeedback.style.display = 'block'
  setTimeout(() => { els.uploadFeedback.style.display = 'none' }, 4000)
}

// ══════════════════════════════════════════════
// UTILIDADES
// ══════════════════════════════════════════════
function capitalize(str) {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
}

// ══════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════
renderInitial()
loadStatus()
setInterval(loadStatus, 1000)
setInterval(checkPendingUid, 1500)
