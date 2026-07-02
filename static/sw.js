const CACHE = 'eco-v3'
const ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
]

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => {
      return cache.addAll(ASSETS)
    })
  )
  self.skipWaiting()
})

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', e => {
  // API siempre desde la red, nunca caché
  if (e.request.url.includes('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() => new Response(
        JSON.stringify({ error: 'Sin conexión' }),
        { headers: { 'Content-Type': 'application/json' }}
      ))
    )
    return
  }

  // Assets estáticos: caché primero (instantáneo)
  if (e.request.url.includes('/static/')) {
    e.respondWith(
      caches.match(e.request).then(cached => cached || fetch(e.request))
    )
    return
  }

  // HTML: caché primero, actualiza en background
  e.respondWith(
    caches.match(e.request).then(cached => {
      const network = fetch(e.request).then(response => {
        caches.open(CACHE).then(cache => cache.put(e.request, response.clone()))
        return response
      })
      return cached || network
    })
  )
})
