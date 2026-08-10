const SOCIALHUB_CACHE = 'socialhub-pwa-v2';
const ASSETS = [
  '/static/css/style.css',
  '/static/css/animations.css',
  '/static/js/app.js',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SOCIALHUB_CACHE).then((cache) => cache.addAll(ASSETS)).catch(() => null));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== SOCIALHUB_CACHE).map((key) => caches.delete(key)))));
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  const isSameOrigin = url.origin === self.location.origin;
  const isApiRequest = isSameOrigin && url.pathname.startsWith('/api/');
  const isPageNavigation = event.request.mode === 'navigate';
  const isStaticAsset = isSameOrigin && (
    url.pathname.startsWith('/static/') ||
    url.pathname === '/manifest.json' ||
    url.pathname === '/favicon.ico'
  );

  // Always fetch API responses and HTML pages from the network so dynamic pages
  // do not get stuck with stale cached data or repeated reload behavior.
  if (isApiRequest || isPageNavigation || !isStaticAsset) {
    event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
      const clone = response.clone();
      caches.open(SOCIALHUB_CACHE).then((cache) => cache.put(event.request, clone)).catch(() => null);
      return response;
    }))
  );
});