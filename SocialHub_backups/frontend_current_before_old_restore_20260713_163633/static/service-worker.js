const SOCIALHUB_CACHE = 'socialhub-shell-v3';
const SHELL_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/manifest.json',
  '/static/images/default_avatar.svg',
  '/static/images/default_cover.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SOCIALHUB_CACHE).then((cache) => cache.addAll(SHELL_ASSETS)).catch(() => null));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== SOCIALHUB_CACHE).map((key) => caches.delete(key)))));
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  const isPrivateOrDynamic = url.pathname.startsWith('/api/') || url.pathname.startsWith('/uploads/') || url.pathname.startsWith('/ws/');
  if (isPrivateOrDynamic) {
    event.respondWith(fetch(event.request));
    return;
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
      if (!response || response.status !== 200 || response.type !== 'basic') return response;
      const copy = response.clone();
      caches.open(SOCIALHUB_CACHE).then((cache) => cache.put(event.request, copy));
      return response;
    }).catch(() => caches.match('/') || cached))
  );
});