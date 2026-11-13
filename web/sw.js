/* Offline cache for the web version. Bump VERSION when files change. */
var VERSION = 'tos-1.0.1';
var FILES = ['./', 'index.html', 'css/app.css', 'js/reference.js', 'js/engine.js', 'js/exporters.js', 'js/athletes.js', 'js/examples.js',
  'js/storage.js', 'js/app.js', 'js/boot.js', 'manifest.webmanifest', 'icons/icon-180.png', 'icons/icon-192.png', 'icons/icon-512.png'];
self.addEventListener('install', function (e) { e.waitUntil(caches.open(VERSION).then(function (c) { return c.addAll(FILES); })); self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) { return Promise.all(keys.filter(function (k) { return k !== VERSION; }).map(function (k) { return caches.delete(k); })); }));
  self.clients.claim();
});
self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request).then(function (hit) { return hit || fetch(e.request); }));
});
