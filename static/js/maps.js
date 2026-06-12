const liveMaps = {};
let mapsObserved = false;

const COMUNAS_16 = [
  {name: "Popular",        lat: 6.3050, lng: -75.5550},
  {name: "Santa Cruz",     lat: 6.2960, lng: -75.5600},
  {name: "Manrique",       lat: 6.2746, lng: -75.5523},
  {name: "Aranjuez",       lat: 6.2860, lng: -75.5650},
  {name: "Castilla",       lat: 6.2923, lng: -75.5707},
  {name: "Doce de Octubre",lat: 6.2980, lng: -75.5880},
  {name: "Robledo",        lat: 6.2775, lng: -75.5909},
  {name: "Villa Hermosa",  lat: 6.2620, lng: -75.5530},
  {name: "Buenos Aires",   lat: 6.2530, lng: -75.5570},
  {name: "Centro",         lat: 6.2518, lng: -75.5636},
  {name: "Laureles",       lat: 6.2459, lng: -75.5964},
  {name: "La América",     lat: 6.2420, lng: -75.5880},
  {name: "San Javier",     lat: 6.2355, lng: -75.6050},
  {name: "El Poblado",     lat: 6.2088, lng: -75.5678},
  {name: "Guayabal",       lat: 6.2107, lng: -75.5888},
  {name: "Belen",          lat: 6.2311, lng: -75.6038},
];

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

const COORD_TO_ZONE = {};
COMUNAS_16.forEach(c => { COORD_TO_ZONE[`${c.lat},${c.lng}`] = c.name; });

function nearestComuna(lat, lng, threshold) {
  threshold = threshold || 0.025;
  let best = null, bestDist = Infinity;
  COMUNAS_16.forEach(c => {
    const d = Math.abs(lat - c.lat) + Math.abs(lng - c.lng);
    if (d < bestDist) { bestDist = d; best = c; }
  });
  if (best && bestDist < threshold) return best;
  return null;
}

function addComunaClickHandler(map, clickLayer) {
  map.on("click", function(e) {
    const c = nearestComuna(e.latlng.lat, e.latlng.lng);
    if (!c) return;
    const popup = L.popup({className: "clima-tooltip"})
      .setLatLng([c.lat, c.lng])
      .setContent(`<div style="min-width:160px;text-align:center;"><strong style="font-size:.9rem;">📍 ${c.name}</strong><br><span style="font-size:.75rem;color:#94a3b8;">Comuna de Medellín</span><br><br><a href="/comuna/${c.name.toLowerCase().replace(/\s+/g,'-')}/" style="display:inline-block;background:#38bdf8;color:#0a0f1a;padding:6px 16px;border-radius:20px;text-decoration:none;font-weight:700;font-size:.8rem;">Ver detalle →</a></div>`)
      .openOn(map);
  });
}

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
  if (!el) return null;
  if (!window.L) {
    console.error("Leaflet no cargado. Verifica CDN o conectividad.");
    el.innerHTML = '<div style="padding:2rem;text-align:center;color:#f4f7fb;">Mapa no disponible (Leaflet no cargó)</div>';
    return null;
  }
  if (liveMaps[id]) return liveMaps[id].map;

  const map = L.map(id, {zoomControl: true, attributionControl: false}).setView(center, zoom);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19
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

  state.vehicleMarkers = VEHICLE_ROUTES.map((r,i) => {
    var fromZone=COORD_TO_ZONE[r.from.join(',')]||'?';
    var toZone=COORD_TO_ZONE[r.to.join(',')]||'?';
    return L.circleMarker([6.2442, -75.5812], {
      radius: 4,
      color: "#fff",
      weight: 1.5,
      fillColor: "#fbbf24",
      fillOpacity: 0.95,
    }).addTo(state.map).bindTooltip('🚗 '+fromZone+' → '+toZone,{sticky:true,className:'clima-tooltip'});
  });

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

function comunaSlug(name) {
  return name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
}

function addZoneMarker(layer, zone, label) {
  try {
    const score = zone.risk_score != null ? Number(zone.risk_score) : zone.congestion_level != null ? Number(zone.congestion_level) : zone.predicted_congestion != null ? Number(zone.predicted_congestion) : 50;
    const lat = Number(zone.lat);
    const lng = Number(zone.lng);
    if (isNaN(lat) || isNaN(lng)) { console.warn("addZoneMarker: invalid lat/lng", zone); return; }
    const src = zone.source || zone.data_source || "";
    const badge = src === "TomTom Traffic API" ? "🛰️" : src ? "📊" : "";
    const zname = zone.name || zone.zone || "";
    const slug = comunaSlug(zname);
    const congestion = zone.congestion_level != null ? zone.congestion_level : zone.congestion || "—";
    const speed = zone.average_speed != null ? zone.average_speed : zone.speed || "—";
    const incidents = zone.incidents != null ? zone.incidents : 0;
    const rain = zone.rain_probability != null ? zone.rain_probability : 0;

    const marker = L.circleMarker([lat, lng], {
      radius: 10,
      color: "#ffffff",
      weight: 2,
      fillColor: riskColor(score),
      fillOpacity: 0.85
    }).addTo(layer)
      .bindTooltip(`<strong>☁️ ${zname}</strong><br>${label}${badge ? `<br><span style="font-size:.7rem;color:#94a3b8;">${badge} ${src}</span>` : ""}`,{sticky:true,className:'clima-tooltip'})
      .bindPopup(`<div style="min-width:180px;text-align:center;"><strong style="font-size:.95rem;color:#f4f7fb;">📍 ${zname}</strong><br><span style="font-size:.75rem;color:#94a3b8;">Comuna de Medellín</span><hr style="border-color:#334155;margin:8px 0;"><table style="width:100%;font-size:.78rem;"><tr><td style="color:#94a3b8;padding:2px 8px 2px 0;">🚗 Congestión</td><td style="color:#f4f7fb;font-weight:600;text-align:right;">${congestion}%</td></tr><tr><td style="color:#94a3b8;padding:2px 8px 2px 0;">⚡ Velocidad</td><td style="color:#f4f7fb;font-weight:600;text-align:right;">${speed} km/h</td></tr><tr><td style="color:#94a3b8;padding:2px 8px 2px 0;">🚨 Incidentes</td><td style="color:#f4f7fb;font-weight:600;text-align:right;">${incidents}</td></tr><tr><td style="color:#94a3b8;padding:2px 8px 2px 0;">🌧️ Lluvia</td><td style="color:#f4f7fb;font-weight:600;text-align:right;">${rain}%</td></tr><tr><td style="color:#94a3b8;padding:2px 8px 2px 0;">⚠️ Riesgo</td><td style="color:#f4f7fb;font-weight:600;text-align:right;">${score}%</td></tr></table><hr style="border-color:#334155;margin:8px 0;"><a href="/comuna/${slug}/" style="display:inline-block;background:#38bdf8;color:#0a0f1a;padding:6px 20px;border-radius:20px;text-decoration:none;font-weight:700;font-size:.82rem;">Ver detalle →</a></div>`,{className:'clima-tooltip',maxWidth:280});
    marker.on('tooltipopen',function(e){
      const el = e.tooltip._container;
      if(el){el.style.setProperty('background','#1e293b','important');el.style.setProperty('border','1px solid #334155','important');el.style.setProperty('border-radius','8px','important');el.style.setProperty('box-shadow','0 4px 16px rgba(0,0,0,.5)','important');el.style.setProperty('padding','8px 12px','important');el.style.setProperty('color','#f4f7fb','important');el.style.setProperty('font-family','inherit','important');el.style.setProperty('font-size','.8rem','important');el.style.setProperty('line-height','1.5','important');}
    });
  } catch(e) { console.error("addZoneMarker error:", e, zone); }
}

function addRoutePolyline(layer, points, color, label) {
  L.polyline(points, {
    color: color,
    weight: 3,
    opacity: 0.7,
    dashArray: null
  }).addTo(layer).bindPopup(label).bindTooltip(label,{sticky:true,className:'clima-tooltip'});
  L.circleMarker(points[0], {
    radius: 6,
    color: "#fff",
    weight: 2,
    fillColor: "#22c55e",
    fillOpacity: 0.9
  }).addTo(layer).bindTooltip("Origen",{sticky:true,className:'clima-tooltip'});
  if (points.length > 1) {
    L.circleMarker(points[points.length - 1], {
      radius: 6,
      color: "#fff",
      weight: 2,
      fillColor: "#ef4444",
      fillOpacity: 0.9
    }).addTo(layer).bindTooltip("Destino",{sticky:true,className:'clima-tooltip'});
  }
}

async function renderRiskMap(id) {
  try {
    const map = createOsmMap(id);
    if (!map) throw new Error("createOsmMap returned null");
    const data = await MoviliAPI.maps();
    const layer = dynamicLayer(id);
    if (!layer) throw new Error("dynamicLayer returned null");
    if (!data || !Array.isArray(data.risk_zones)) { console.warn("renderRiskMap: no risk_zones data", data); return; }
    const heat = data.risk_zones.map(z => [z.lat, z.lng, z.heat]);
    if (L.heatLayer) {
      liveMaps[id].heat = L.heatLayer(heat, {
        radius: 20,
        blur: 15,
        gradient: {0.2: "#38bdf8", 0.55: "#f59e0b", 0.85: "#ef4444"}
      }).addTo(map);
    }
    data.risk_zones.forEach(z => {
      addZoneMarker(layer, z, `${z.risk_score}%<table><tr><td class="label">📊 Nivel</td><td class="value">${z.risk_score>=75?'Alto':z.risk_score>=55?'Medio-Alto':z.risk_score>=30?'Medio-Bajo':'Bajo'}</td></tr><tr><td class="label">🚗 Congestión</td><td class="value">${z.congestion}%</td></tr><tr><td class="label">🚨 Incidentes</td><td class="value">${z.incidents}</td></tr></table>`);
    });
    addComunaClickHandler(map, layer);
    MoviliLive.flash(document.getElementById(id));
  } catch(e) { console.error("renderRiskMap error:", e); }
}

async function renderTrafficMap(id) {
  try {
    const map = createOsmMap(id);
    if (!map) throw new Error("createOsmMap returned null");
    const boot = await MoviliAPI.bootstrap();
    stopVehicleAnimation(id);
    const layer = dynamicLayer(id);
    if (!layer) throw new Error("dynamicLayer returned null");
    const zones = boot && boot.zones ? boot.zones : [];
    zones.forEach(t => {
      addZoneMarker(layer, t, `${t.congestion_level}% · ${t.average_speed} km/h`);
    });
    startVehicleAnimation(id, zones);
    addComunaClickHandler(map, layer);
    MoviliLive.flash(document.getElementById(id));
  } catch(e) { console.error("renderTrafficMap error:", e); }
}

async function renderRoutesMap(id, data) {
  try {
    const map = createOsmMap(id);
    if (!map) throw new Error("createOsmMap returned null");
    if (!data) {
      const origin = document.getElementById("routeOrigin") ? document.getElementById("routeOrigin").value : "";
      const dest = document.getElementById("routeDest") ? document.getElementById("routeDest").value : "";
      const params = new URLSearchParams();
      if (origin) params.set("origin", origin);
      if (dest) params.set("destination", dest);
      const qs = params.toString();
      data = await MoviliAPI.get(`/api/routes${qs ? "?" + qs : ""}`);
    }
    const layer = dynamicLayer(id);
    if (!layer) throw new Error("dynamicLayer returned null");
    data.routes.forEach(route => {
      const riskLabel = route.risk != null ? `Índice: ${route.risk}%` : "";
      addRoutePolyline(layer, route.points, route.risk != null ? riskColor(route.risk) : "#3b82f6",
        `${route.distance} km · ${route.time} min${riskLabel ? ` · ${riskLabel}` : ""}`);
    });
    MoviliLive.flash(document.getElementById(id));
  } catch(e) { console.error("renderRoutesMap error:", e); }
}

const congestionColor=v=>v>=75?"#ef4444":v>=55?"#f59e0b":"#22c55e";
const markerRadius=v=>Math.max(8,Math.min(18,6+v*12));

async function renderPredictionMap(id, hour = 18) {
  try {
    const map = createOsmMap(id);
    if (!map) throw new Error("createOsmMap returned null");
    const data = await MoviliAPI.predictions(hour);
    const layer = dynamicLayer(id);
    if (!layer) throw new Error("dynamicLayer returned null");
    const offset = document.getElementById("forecastOffset") ? parseInt(document.getElementById("forecastOffset").value) : 0;
    (data.predictions||[]).forEach(p => {
      const lat = Number(p.lat), lng = Number(p.lng);
      if (isNaN(lat) || isNaN(lng)) { console.warn("renderPredictionMap: invalid lat/lng", p); return; }
      const f = p.forecast && p.forecast[offset] ? p.forecast[offset] : p.forecast && p.forecast[0] ? p.forecast[0] : null;
      if (!f) return;
      const congestion = Number(f.predicted_congestion);
      const confidence = Number(f.confidence) || 0.5;
      const rain = Number(f.rain_probability) || 0;
      const slug = comunaSlug(p.zone);
      L.circleMarker([lat, lng], {
        radius: markerRadius(confidence),
        color: "#fff",
        weight: 2 + Math.round(rain / 25),
        fillColor: congestionColor(congestion),
        fillOpacity: 0.85
      }).addTo(layer)
        .bindTooltip(`<h4 style="margin:0 0 4px;font-size:.85rem;">${p.zone}</h4><table style="font-size:.75rem;"><tr><td style="color:#94a3b8;padding-right:8px;">Congestión</td><td class="text-end" style="color:#f4f7fb;font-weight:600;">${congestion}%</td></tr><tr><td style="color:#94a3b8;padding-right:8px;">Lluvia</td><td class="text-end" style="color:#f4f7fb;font-weight:600;">${rain}%</td></tr><tr><td style="color:#94a3b8;padding-right:8px;">Confianza</td><td class="text-end" style="color:#f4f7fb;font-weight:600;">${Math.round(confidence*100)}%</td></tr></table>`,{sticky:true,className:'clima-tooltip'})
        .bindPopup(`<div style="min-width:180px;text-align:center;"><strong style="font-size:.95rem;color:#f4f7fb;">📍 ${p.zone}</strong><br><span style="font-size:.75rem;color:#94a3b8;">Predicción de congestión</span><hr style="border-color:#334155;margin:8px 0;"><table style="width:100%;font-size:.78rem;"><tr><td style="color:#94a3b8;padding:2px 8px 2px 0;">🚗 Congestión</td><td style="color:#f4f7fb;font-weight:600;text-align:right;">${congestion}%</td></tr><tr><td style="color:#94a3b8;padding:2px 8px 2px 0;">🌧️ Lluvia</td><td style="color:#f4f7fb;font-weight:600;text-align:right;">${rain}%</td></tr><tr><td style="color:#94a3b8;padding:2px 8px 2px 0;">📊 Confianza</td><td style="color:#f4f7fb;font-weight:600;text-align:right;">${Math.round(confidence*100)}%</td></tr></table><hr style="border-color:#334155;margin:8px 0;"><a href="/comuna/${slug}/" style="display:inline-block;background:#38bdf8;color:#0a0f1a;padding:6px 20px;border-radius:20px;text-decoration:none;font-weight:700;font-size:.82rem;">Ver detalle →</a></div>`,{className:'clima-tooltip',maxWidth:280});
    });
    addComunaClickHandler(map, layer);
    MoviliLive.flash(document.getElementById(id));
  } catch(e) { console.error("renderPredictionMap error:", e); }
}

function observeMap(id, renderFn) {
  const el = document.getElementById(id);
  if (!el) return;
  try {
    const register = () => {
      try { MoviliLive.register(() => renderFn(id).catch(console.error), MoviliLive.intervalMs); } catch(e) { console.error("observeMap register error:", e); }
    };
    if ("IntersectionObserver" in window && el.offsetParent !== null) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            observer.unobserve(entry.target);
            register();
          }
        });
      }, {rootMargin: "300px"});
      observer.observe(el);
    } else {
      register();
    }
  } catch(e) { console.error("observeMap error:", e); }
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("landingMap")) observeMap("landingMap", renderRiskMap);
  if (document.getElementById("mainMap")) observeMap("mainMap", renderRiskMap);
  if (document.getElementById("trafficMap")) MoviliLive.register(() => renderTrafficMap("trafficMap").catch(console.error), MoviliLive.intervalMs);
  if (document.getElementById("routesMap") && !document.getElementById("routeForm")) observeMap("routesMap", renderRoutesMap);
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
