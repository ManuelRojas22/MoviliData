const CACHE_NAME = "movilidata-os-v1";
const ASSETS = ["/", "/dashboard/", "/pwa/offline.html", "/static/css/global.css", "/static/css/responsive.css", "/static/js/main.js"];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)));
});

self.addEventListener("fetch", event => {
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request).then(response => response || caches.match("/pwa/offline.html"))));
});
