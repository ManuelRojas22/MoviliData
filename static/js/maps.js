const liveMaps = {};

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

function dynamicLayer(id) {
  const state = liveMaps[id];
  if (!state) return null;
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
  L.circle([lat, lng], {
    radius: 180 + score * 24,
    color: riskColor(score),
    fillColor: riskColor(score),
    fillOpacity: 0.24,
    weight: 2
  }).addTo(layer);

  L.circleMarker([lat, lng], {
    radius: 8,
    color: "#e5eefc",
    fillColor: riskColor(score),
    fillOpacity: 0.95,
    weight: 2
  }).addTo(layer).bindPopup(`<strong>${zone.name || zone.zone}</strong><br>${label}`);
}

async function renderRiskMap(id) {
  const map = createOsmMap(id);
  if (!map) return;
  const layer = dynamicLayer(id);
  const data = await MoviliAPI.maps();
  const heat = data.risk_zones.map(z => [z.lat, z.lng, z.heat]);
  if (L.heatLayer) {
    liveMaps[id].heat = L.heatLayer(heat, {
      radius: 34,
      blur: 24,
      gradient: {0.2: "#38bdf8", 0.55: "#f59e0b", 0.85: "#ef4444"}
    }).addTo(map);
  }
  data.risk_zones.forEach(z => {
    addZoneMarker(layer, z, `Riesgo ${z.risk_score}%<br>${z.reason}<br>Fuente: OpenStreetMap, clima e incidentes`);
  });
  MoviliLive.flash(document.getElementById(id));
}

async function renderTrafficMap(id) {
  const map = createOsmMap(id);
  if (!map) return;
  const layer = dynamicLayer(id);
  const data = await MoviliAPI.traffic();
  data.traffic.forEach(t => {
    addZoneMarker(layer, t, `Congestion estimada ${t.congestion_level}%<br>Velocidad ${t.average_speed} km/h<br>Incidentes ${t.incidents}<br>${t.status}`);
  });
  MoviliLive.flash(document.getElementById(id));
}

async function renderRoutesMap(id) {
  const map = createOsmMap(id);
  if (!map) return;
  const layer = dynamicLayer(id);
  const data = await MoviliAPI.routes();
  data.routes.forEach(route => {
    L.polyline(route.points, {
      color: riskColor(route.risk),
      weight: 5,
      opacity: 0.95
    }).addTo(layer).bindPopup(`<strong>${route.name}</strong><br>${route.distance} km - ${route.time} min<br>Riesgo ${route.risk}%`);
    L.marker(route.points[0]).addTo(layer).bindPopup(route.name);
  });
  MoviliLive.flash(document.getElementById(id));
}

async function renderPredictionMap(id, hour = 18) {
  const map = createOsmMap(id);
  if (!map) return;
  const layer = dynamicLayer(id);
  const data = await MoviliAPI.predictions(hour);
  data.predictions.forEach(p => {
    addZoneMarker(layer, {
      name: p.zone,
      lat: p.lat,
      lng: p.lng,
      risk_score: p.predicted_congestion
    }, `Prediccion ${p.predicted_congestion}%<br>Lluvia ${p.rain_probability}%<br>Confianza ${Math.round(p.confidence * 100)}%`);
  });
  MoviliLive.flash(document.getElementById(id));
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("landingMap")) MoviliLive.register(() => renderRiskMap("landingMap").catch(console.error), MoviliLive.intervalMs);
  if (document.getElementById("mainMap")) MoviliLive.register(() => renderRiskMap("mainMap").catch(console.error), MoviliLive.intervalMs);
  if (document.getElementById("trafficMap")) MoviliLive.register(() => renderTrafficMap("trafficMap").catch(console.error), MoviliLive.intervalMs);
  if (document.getElementById("routesMap")) MoviliLive.register(() => renderRoutesMap("routesMap").catch(console.error), MoviliLive.intervalMs);
  if (document.getElementById("riskMap")) MoviliLive.register(() => renderRiskMap("riskMap").catch(console.error), MoviliLive.intervalMs);
  if (document.getElementById("predictionMap")) {
    const range = document.getElementById("hourRange");
    MoviliLive.register(() => renderPredictionMap("predictionMap", range ? range.value : 18).catch(console.error), MoviliLive.intervalMs);
    if (range) range.addEventListener("input", event => renderPredictionMap("predictionMap", event.target.value));
  }
});
