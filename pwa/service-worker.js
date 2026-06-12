const CACHE_NAME = "movilidata-os-v4";
const ASSETS = [
  "/",
  "/dashboard/",
  "/traffic/",
  "/routes/",
  "/predictions/",
  "/risk-zones/",
  "/alerts/",
  "/statistics/",
  "/pwa/offline.html",
  "/static/css/global.css",
  "/static/css/dashboard.css",
  "/static/css/maps.css",
  "/static/css/alerts.css",
  "/static/css/animations.css",
  "/static/css/responsive.css",
  "/static/js/api.js",
  "/static/js/main.js",
  "/static/js/maps.js",
  "/static/js/charts.js",
  "/static/js/alerts.js",
  "/static/js/dashboard.js",
  "/static/js/routes.js",
  "https://cdn.jsdelivr.net/npm/sweetalert2@11",
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
  "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
  "https://unpkg.com/leaflet.heat/dist/leaflet-heat.js",
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
];

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      Promise.allSettled(ASSETS.map(url =>
        cache.add(url).catch(() => {})
      ))
    )
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    Promise.all([
      clients.claim(),
      caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
    ])
  );
});

self.addEventListener("fetch", event => {
  const {request} = event;

  if (request.url.includes("/api/")) {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(JSON.stringify({error: "offline"}), {
          status: 503,
          headers: {"Content-Type": "application/json"}
        });
      })
    );
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
        return response;
      }).catch(() => caches.match(request).then(cached => cached || caches.match("/pwa/offline.html")))
    );
    return;
  }

  if (/\.(css|js|png|jpg|svg|woff2?)$/.test(request.url)) {
    event.respondWith(
      caches.match(request).then(cached => cached || fetch(request).then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
        return response;
      }))
    );
    return;
  }

  event.respondWith(
    fetch(request).catch(() =>
      caches.match(request).then(response => response || caches.match("/pwa/offline.html"))
    )
  );
});
