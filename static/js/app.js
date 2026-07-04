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
// VISTA: AGREGAR — descarga via YouTube
// ══════════════════════════════════════════════
let downloadPolling = null

document.getElementById('yt-download-btn').addEventListener('click', async () => {
  const url       = document.getElementById('yt-url').value.trim()
  const albumName = document.getElementById('yt-album-name').value.trim()

  if (!albumName) {
    document.getElementById('yt-album-name').focus()
    return
  }
  if (!url) {
    document.getElementById('yt-url').focus()
    return
  }

  const btn      = document.getElementById('yt-download-btn')
  btn.disabled   = true
  btn.textContent = 'Iniciando...'

  document.getElementById('yt-progress').style.display  = 'block'
  document.getElementById('yt-feedback').style.display  = 'none'

  try {
    const res  = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, album_name: albumName })
    })
    const data = await res.json()

    if (!data.ok) {
      showYtFeedback(data.error, 'error')
      btn.disabled    = false
      btn.textContent = 'Descargar álbum'
      return
    }

    downloadPolling = setInterval(async () => {
      try {
        const r    = await fetch('/api/download/status')
        const stat = await r.json()

        document.getElementById('yt-progress-fill').style.width = stat.progress + '%'
        document.getElementById('yt-progress-msg').textContent  = stat.message

        if (!stat.running) {
          clearInterval(downloadPolling)
          downloadPolling = null
          btn.disabled    = false
          btn.innerHTML   = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M23 7s-.3-2-1.2-2.8c-1.1-1.2-2.4-1.2-3-1.3C16.6 2.8 12 2.8 12 2.8s-4.6 0-6.8.1c-.6.1-1.9.1-3 1.3C1.3 5 1 7 1 7S.7 9.1.7 11.3v2c0 2.1.3 4.2.3 4.2s.3 2 1.2 2.8c1.1 1.2 2.6 1.1 3.3 1.2C7.3 21.7 12 21.7 12 21.7s4.6 0 6.8-.2c.6-.1 1.9-.1 3-1.3.9-.8 1.2-2.8 1.2-2.8s.3-2.1.3-4.2v-2C23.3 9.1 23 7 23 7zM9.7 15.5V8.3l6.5 3.6-6.5 3.6z"/>
            </svg>
            Descargar álbum`

          if (stat.error) {
            showYtFeedback('Error: ' + stat.error, 'error')
          } else {
            showYtFeedback('✓ ' + stat.message + ' El álbum ya está en tu biblioteca.', 'success')
            document.getElementById('yt-url').value        = ''
            document.getElementById('yt-album-name').value = ''
            document.getElementById('yt-progress').style.display = 'none'
          }
        }
      } catch (err) {
        console.warn('Error polling descarga:', err)
      }
    }, 1000)

  } catch (err) {
    showYtFeedback('Error de conexión', 'error')
    btn.disabled    = false
    btn.textContent = 'Descargar álbum'
  }
})

function showYtFeedback(msg, type) {
  const el      = document.getElementById('yt-feedback')
  el.textContent  = msg
  el.className    = `upload-feedback ${type}`
  el.style.display = 'block'
  if (type === 'success') {
    setTimeout(() => { el.style.display = 'none' }, 5000)
  }
}

// ══════════════════════════════════════════════
// MODAL: APRENDER DISCO NUEVO
// ══════════════════════════════════════════════
let pendingUid = null

function checkPendingUid(pendingFromStatus) {
  if (pendingFromStatus && pendingFromStatus !== pendingUid) {
    pendingUid = pendingFromStatus
    showLearnModal(pendingFromStatus)
  } else if (!pendingFromStatus && pendingUid) {
    pendingUid = null
    hideLearnModal()
  }
}

async function showLearnModal(uid) {
  document.getElementById('modal-uid').textContent = uid

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

document.getElementById('modal-cancel').addEventListener('click', async () => {
  try {
    await fetch('/api/pending/discard', { method: 'POST' })
  } catch (err) {}
  hideLearnModal()
})

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
      loadStatus()
    }
  } catch (err) {
    console.warn('Error asociando disco:', err)
  }
})

// ══════════════════════════════════════════════
// VISTA: INICIO — estado y reproducción
// ══════════════════════════════════════════════
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

    checkPendingUid(data.pending_uid)
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

// ── Animación cambio de disco ─────────────────
let lastAlbum = null

function animateDiscChange(newAlbum, callback) {
  const disc = els.disc

  if (!lastAlbum || lastAlbum === newAlbum) {
    lastAlbum = newAlbum
    callback()
    return
  }

  lastAlbum = newAlbum
  disc.style.animationPlayState = 'paused'
  disc.style.transition = 'transform 0.3s ease-in, opacity 0.25s ease'
  disc.style.transform  = 'scale(0.1)'
  disc.style.opacity    = '0'

  setTimeout(() => {
    callback()
    disc.style.transition = 'none'
    disc.style.transform  = 'scale(0.1)'
    disc.style.opacity    = '0'
    disc.offsetHeight

    disc.style.transition = 'transform 0.4s cubic-bezier(0.34, 1.4, 0.64, 1), opacity 0.3s ease'
    disc.style.transform  = 'scale(1)'
    disc.style.opacity    = '1'

    setTimeout(() => {
      disc.style.animationPlayState = state.playing ? 'running' : 'paused'
    }, 400)
  }, 300)
}

function renderAll() {
  const newAlbum = state.trackName !== 'Sin disco apoyado' ? state.trackName : null

  animateDiscChange(newAlbum, () => {
    els.discTag.textContent = state.discTag
  })

  els.trackName.textContent = state.trackName
  els.trackSub.textContent  = state.trackSub
  els.playIcon.innerHTML    = state.playing ? ICON_PAUSE : ICON_PLAY
  els.playBtn.setAttribute('aria-label', state.playing ? 'Pausar' : 'Reproducir')
  els.disc.classList.toggle('spinning', state.playing)
  if (!state.draggingVolume) renderVolume(state.volume)
  renderLights(state.lights)

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
  let detail = $('view-album-detail')
  if (!detail) {
    detail = document.createElement('div')
    detail.id = 'view-album-detail'
    detail.className = 'view'
    document.querySelector('body').insertBefore(detail, document.querySelector('.bottom-nav'))
  }

  detail.innerHTML = `
    <header class="app-header detail-header">
      <button class="back-btn" id="back-btn" aria-label="Volver">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M19 12H5M12 5l-7 7 7 7"/>
        </svg>
      </button>
      <div class="detail-header-text">
        <p class="app-label">Álbum</p>
        <h1 class="app-name serif">${album.name}</h1>
      </div>
    </header>

    <div class="album-detail-disc">
      <div class="disc disc-medium">
        <div class="disc-grooves"></div>
        <div class="disc-label">
          <div class="disc-dot"></div>
          <span class="disc-tag">${album.name.slice(0, 5).toUpperCase()}</span>
        </div>
      </div>
      <p class="album-detail-count">${album.tracks} pistas</p>
    </div>

    <div class="tracks-list" id="tracks-list"></div>
  `

  navigateTo('album-detail')

  try {
    $('tracks-list').innerHTML = `
      ${[1,2,3,4,5].map((_, i) => `
        <div class="track-item">
          <div class="skeleton" style="width:20px; height:14px; border-radius:4px;"></div>
          <div class="skeleton skeleton-text" style="flex:1; width:${60 + i * 8}%"></div>
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
      </div>
    `).join('')
  } catch (err) {
    $('tracks-list').innerHTML = '<div class="tracks-loading">Error cargando pistas</div>'
  }

  $('back-btn').addEventListener('click', () => navigateTo('discos'))
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
setInterval(loadStatus, 2000)

// ── Service Worker ───────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .then(() => console.log('[ECO] SW registrado'))
      .catch(err => console.warn('[ECO] SW error:', err))
  })
}
