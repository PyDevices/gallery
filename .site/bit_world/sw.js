// The page, its runtime and its Python belong together, so they're cached as
// one set under one version, which the site build writes below. A new version
// waits until every window of the old one has closed, so nothing running ever
// loads half of each.
const VERSION = '__VERSION__';
const CACHE = 'bit_world-' + VERSION;
const FILES = [
  './',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './micropython.mjs',
  './micropython.wasm',
  './bit_world.bundle',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(FILES)));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys()
    .then((names) => Promise.all(names
      .filter((name) => name.startsWith('bit_world-') && name !== CACHE)
      .map((name) => caches.delete(name))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.open(CACHE)
    .then((cache) => cache.match(event.request, {ignoreSearch: true}))
    .then((hit) => hit || fetch(event.request)));
});
