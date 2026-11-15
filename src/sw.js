/* Keeps the app working offline. The page itself is fetched fresh when online
   (so updates arrive) and served from the cache when not. Photos are cache-first. */
const VERSION = '__VERSION__';
const APP = 'euro-app-' + VERSION;
const PHOTOS = 'euro-photos-v1';
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(APP).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('euro-app-') && k !== APP).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  if (url.pathname.includes('/photos/')) {
    e.respondWith(caches.open(PHOTOS).then(async c => {
      const key = 'photos/' + url.pathname.split('/').pop();
      const hit = await c.match(key);
      if (hit) return hit;
      const r = await fetch(req);
      if (r.ok) c.put(key, r.clone());
      return r;
    }));
    return;
  }

  const scopePath = new URL(self.registration.scope).pathname;
  const isApp = url.pathname === scopePath || url.pathname === scopePath + 'index.html';
  if (isApp) {
    e.respondWith((async () => {
      const c = await caches.open(APP);
      try {
        const ctl = new AbortController();
        const timer = setTimeout(() => ctl.abort(), 4000);
        const r = await fetch(url.origin + url.pathname, {signal: ctl.signal, cache: 'no-cache'});
        clearTimeout(timer);
        if (r.ok && (r.headers.get('content-type') || '').includes('text/html')) c.put('index.html', r.clone());
        return r;
      } catch (err) {
        return (await c.match('index.html')) || (await c.match('./')) || Response.error();
      }
    })());
    return;
  }

  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => {
    if (r.ok) caches.open(APP).then(c => c.put(req, r.clone()));
    return r;
  })));
});
