const SOCIALHUB_CACHE = 'socialhub-shell-v3-high-level-css';
const SHELL_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/ui-refresh.js',
  '/static/manifest.json',
  '/static/images/default_avatar.svg',
  '/static/images/default_cover.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SOCIALHUB_CACHE)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .catch(() => null)
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== SOCIALHUB_CACHE).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin === self.location.origin && url.pathname.startsWith('/static/css/')) {
    event.respondWith(fetch(event.request).then((response) => {
      const copy = response.clone();
      caches.open(SOCIALHUB_CACHE).then((cache) => cache.put(event.request, copy));
      return response;
    }).catch(() => caches.match(event.request)));
    return;
  }
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
