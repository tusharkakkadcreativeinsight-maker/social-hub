const CACHE='socialhub-shell-v3';
const SHELL=['/','/offline','/static/css/style.css','/static/js/app.js','/static/js/ui-refresh.js','/static/images/default_avatar.svg'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',event=>{const req=event.request;const url=new URL(req.url);if(req.method!=='GET'||url.pathname.startsWith('/api')||url.pathname.startsWith('/uploads'))return;event.respondWith(fetch(req).then(res=>{const copy=res.clone();if(res.ok&&url.origin===location.origin)caches.open(CACHE).then(c=>c.put(req,copy));return res}).catch(()=>caches.match(req).then(cached=>cached||caches.match('/offline'))))});
