const liveMaps = {};
let mapsObserved = false;

const VEHICLE_ROUTES = [
  {from: [6.2088, -75.5678], to: [6.2518, -75.5636]},
  {from: [6.2518, -75.5636], to: [6.2459, -75.5964]},
  {from: [6.2459, -75.5964], to: [6.2311, -75.6038]},
  {from: [6.2311, -75.6038], to: [6.2107, -75.5888]},
  {from: [6.2107, -75.5888], to: [6.2088, -75.5678]},
  {from: [6.2518, -75.5636], to: [6.2746, -75.5523]},
  {from: [6.2746, -75.5523], to: [6.2775, -75.5909]},
  {from: [6.2775, -75.5909], to: [6.2923, -75.5707]},
  {from: [6.2923, -75.5707], to: [6.2518, -75.5636]},
  {from: [6.2459, -75.5964], to: [6.2775, -75.5909]},
  {from: [6.2311, -75.6038], to: [6.2518, -75.5636]},
];

const COORD_TO_ZONE = {
  "6.2088,-75.5678": "El Poblado",
  "6.2459,-75.5964": "Laureles",
  "6.2518,-75.5636": "Centro",
  "6.2311,-75.6038": "Belen",
  "6.2775,-75.5909": "Robledo",
  "6.2746,-75.5523": "Manrique",
  "6.2107,-75.5888": "Guayabal",
  "6.2923,-75.5707": "Castilla",
};

function _interpolatePath(from, to, steps = 10) {
  const path = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    path.push([from[0] + (to[0] - from[0]) * t, from[1] + (to[1] - from[1]) * t]);
  }
  return path;
}

function _fetchOsrmPath(from, to) {
  const url = `https://router.project-osrm.org/route/v1/driving/${from[1]},${from[0]};${to[1]},${to[0]}?geometries=geojson&overview=full&steps=false`;
  return fetch(url, {headers: {"User-Agent": "MoviliData/1.0"}})
    .then(r => r.json())
    .then(data => {
      if (data.code !== "Ok" || !data.routes) return null;
      const coords = data.routes[0].geometry.coordinates;
      return coords.map(c => [c[1], c[0]]);
    })
    .catch(() => null);
}

const _vehiclePathCache = {};

async function _getVehiclePath(from, to) {
  const key = `${from[0]},${from[1]}-${to[0]},${to[1]}`;
  if (_vehiclePathCache[key]) return _vehiclePathCache[key];
  const osrm = await _fetchOsrmPath(from, to);
  const path = osrm || _interpolatePath(from, to, 20);
  _vehiclePathCache[key] = path;
  return path;
}

function createOsmMap(id, center = [6.2442, -75.5812], zoom = 12) {
  const el = document.getElementById(id);
  if (!el || !window.L) return null;
  if (liveMaps[id]) return liveMaps[id].map;

  const map = L.map(id, {zoomControl: true}).setView(center, zoom);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);
  liveMaps[id] = {map, layer: L.layerGroup().addTo(map), heat: null};
  return map;
}

function _pathPosition(path, t) {
  const total = path.length - 1;
  const fi = t * total;
  const si = Math.floor(fi);
  const st = fi - si;
  const a = path[Math.min(si, total)];
  const b = path[Math.min(si + 1, total)];
  return [a[0] + (b[0] - a[0]) * st, a[1] + (b[1] - a[1]) * st];
}

function _routeSpeed(r, trafficData) {
  const keyFrom = `${r.from[0]},${r.from[1]}`;
  const keyTo = `${r.to[0]},${r.to[1]}`;
  const zoneFrom = COORD_TO_ZONE[keyFrom];
  const zoneTo = COORD_TO_ZONE[keyTo];
  let speed = 30;
  if (trafficData && trafficData.length) {
    const s1 = trafficData.find(t => t.zone === zoneFrom);
    const s2 = trafficData.find(t => t.zone === zoneTo);
    const v1 = s1 ? s1.average_speed : 30;
    const v2 = s2 ? s2.average_speed : 30;
    speed = (v1 + v2) / 2;
  }
  return Math.max(8, Math.min(60, speed));
}

function startVehicleAnimation(id, trafficData) {
  const state = liveMaps[id];
  if (!state) return;
  if (state.vehicles) return;
  state.vehicles = [];

  state.vehicleState = VEHICLE_ROUTES.map(r => {
    const speed = _routeSpeed(r, trafficData);
    return {
      path: null,
      t: Math.random() * 2,
      speed: 0.001 + (speed / 60) * 0.003,
    };
  });

  state.vehicleMarkers = VEHICLE_ROUTES.map(() =>
    L.circleMarker([6.2442, -75.5812], {
      radius: 4,
      color: "#fff",
      weight: 1.5,
      fillColor: "#fbbf24",
      fillOpacity: 0.95,
    }).addTo(state.map)
  );

  VEHICLE_ROUTES.forEach((r, i) => {
    _getVehiclePath(r.from, r.to).then(path => {
      state.vehicleState[i].path = path;
      state.vehicleMarkers[i].setLatLng(path[0]);
    });
  });

  state.vehicleTimer = setInterval(() => {
    state.vehicleState.forEach((v, i) => {
      if (!v.path) return;
      v.t += v.speed;
      const tri = v.t % 2;
      const posT = tri <= 1 ? tri : 2 - tri;
      const pos = _pathPosition(v.path, posT);
      state.vehicleMarkers[i].setLatLng(pos);
    });
  }, 50);
}

function stopVehicleAnimation(id) {
  const state = liveMaps[id];
  if (!state) return;
  if (state.vehicleTimer) {
    clearInterval(state.vehicleTimer);
    state.vehicleTimer = null;
  }
  if (state.vehicleMarkers) {
    state.vehicleMarkers.forEach(m => state.map.removeLayer(m));
    state.vehicleMarkers = null;
  }
  state.vehicleState = null;
  state.vehicles = null;
}

function dynamicLayer(id) {
  const state = liveMaps[id];
  if (!state) return null;
  stopVehicleAnimation(id);
  state.layer.clearLayers();
  if (state.heat) {
    state.map.removeLayer(state.heat);
    state.heat = null;
  }
  return state.layer;
}

function riskColor(score) {
  if (score >= 75) return "#ef4444";
  if (score >= 55) return "#f59e0b";
  return "#22c55e";
}

function addZoneMarker(layer, zone, label) {
  const score = Number(zone.risk_score || zone.congestion_level || zone.predicted_congestion || 50);
  const lat = Number(zone.lat);
  const lng = Number(zone.lng);

  L.circleMarker([lat, lng], {
    radius: 10,
    color: "#ffffff",
    weight: 2,
    fillColor: riskColor(score),
    fillOpacity: 0.85
  }).addTo(layer).bindPopup(`<strong>${zone.name || zone.zone}</strong><br>${label}`);
}

function addRoutePolyline(layer, points, color, label) {
  L.polyline(points, {
    color: color,
    weight: 3,
    opacity: 0.7,
    dashArray: null
  }).addTo(layer).bindPopup(label);
  L.circleMarker(points[0], {
    radius: 6,
    color: "#fff",
    weight: 2,
    fillColor: "#22c55e",
    fillOpacity: 0.9
  }).addTo(layer).bindPopup("Origen");
  if (points.length > 1) {
    L.circleMarker(points[points.length - 1], {
      radius: 6,
      color: "#fff",
      weight: 2,
      fillColor: "#ef4444",
      fillOpacity: 0.9
    }).addTo(layer).bindPopup("Destino");
  }
}

async function renderRiskMap(id) {
  const map = createOsmMap(id);
  if (!map) return;
  const layer = dynamicLayer(id);
  const data = await MoviliAPI.maps();
  const heat = data.risk_zones.map(z => [z.lat, z.lng, z.heat]);
  if (L.heatLayer) {
    liveMaps[id].heat = L.heatLayer(heat, {
      radius: 20,
      blur: 15,
      gradient: {0.2: "#38bdf8", 0.55: "#f59e0b", 0.85: "#ef4444"}
    }).addTo(map);
  }
  data.risk_zones.forEach(z => {
    addZoneMarker(layer, z, `Riesgo ${z.risk_score}%`);
  });
  MoviliLive.flash(document.getElementById(id));
}

async function renderTrafficMap(id) {
  const map = createOsmMap(id);
  if (!map) return;
  stopVehicleAnimation(id);
  const layer = dynamicLayer(id);
  const boot = await MoviliAPI.bootstrap();
  const zones = boot && boot.zones ? boot.zones : [];
  zones.forEach(t => {
    addZoneMarker(layer, t, `${t.congestion_level}% · ${t.average_speed} km/h`);
  });
  startVehicleAnimation(id, zones);
  MoviliLive.flash(document.getElementById(id));
}

async function renderRoutesMap(id, data) {
  const map = createOsmMap(id);
  if (!map) return;
  const layer = dynamicLayer(id);
  if (!data) {
    const origin = document.getElementById("routeOrigin") ? document.getElementById("routeOrigin").value : "";
    const dest = document.getElementById("routeDest") ? document.getElementById("routeDest").value : "";
    const params = new URLSearchParams();
    if (origin) params.set("origin", origin);
    if (dest) params.set("destination", dest);
    const qs = params.toString();
    data = await MoviliAPI.get(`/api/routes${qs ? "?" + qs : ""}`);
  }
  data.routes.forEach(route => {
    addRoutePolyline(layer, route.points, riskColor(route.risk),
      `${route.distance} km · ${route.time} min · riesgo ${route.risk}%`);
  });
  MoviliLive.flash(document.getElementById(id));
}

async function renderPredictionMap(id, hour = 18) {
  const map = createOsmMap(id);
  if (!map) return;
  const layer = dynamicLayer(id);
  const data = await MoviliAPI.predictions(hour);
  const offset = document.getElementById("forecastOffset") ? parseInt(document.getElementById("forecastOffset").value) : 0;
  data.predictions.forEach(p => {
    const f = p.forecast && p.forecast[offset] ? p.forecast[offset] : p.forecast && p.forecast[0] ? p.forecast[0] : {predicted_congestion: 50, rain_probability: 30, confidence: 0.7, hour: offset};
    addZoneMarker(layer, {
      name: p.zone,
      lat: p.lat,
      lng: p.lng,
      risk_score: f.predicted_congestion
    }, `${f.predicted_congestion}% · ${f.rain_probability}% lluvia`);
  });
  MoviliLive.flash(document.getElementById(id));
}

function observeMap(id, renderFn) {
  const el = document.getElementById(id);
  if (!el) return;
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          observer.unobserve(entry.target);
          MoviliLive.register(() => renderFn(id).catch(console.error), MoviliLive.intervalMs);
        }
      });
    }, {rootMargin: "300px"});
    observer.observe(el);
  } else {
    MoviliLive.register(() => renderFn(id).catch(console.error), MoviliLive.intervalMs);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("landingMap")) observeMap("landingMap", renderRiskMap);
  if (document.getElementById("mainMap")) observeMap("mainMap", renderRiskMap);
  if (document.getElementById("trafficMap")) MoviliLive.register(() => renderTrafficMap("trafficMap").catch(console.error), MoviliLive.intervalMs);
  if (document.getElementById("routesMap") && !document.getElementById("routeForm")) observeMap("routesMap", renderRoutesMap);
  if (document.getElementById("riskMap")) observeMap("riskMap", renderRiskMap);
  if (document.getElementById("predictionMap")) {
    const range = document.getElementById("hourRange");
    observeMap("predictionMap", (id) => renderPredictionMap(id, range ? range.value : 18));
    if (range) range.addEventListener("input", event => renderPredictionMap("predictionMap", event.target.value));
  }
  const offsetSlider = document.getElementById("forecastOffset");
  if (offsetSlider) {
    offsetSlider.addEventListener("input", () => {
      const range = document.getElementById("hourRange");
      renderPredictionMap("predictionMap", range ? range.value : 18);
    });
  }
});
