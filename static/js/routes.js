console.log("routes.js loaded");
const MEDELLIN_VIEWBOX="-75.68,6.10,-75.48,6.42";
const _acInstances = [];
let __simMarker = null;
let __simInterval = null;
let __simRoute = null;

function _setupAutocomplete(inputId, resultsId, latId, lngId, nhId, nhToggleId) {
  const input = document.getElementById(inputId);
  const results = document.getElementById(resultsId);
  const latField = document.getElementById(latId);
  const lngField = document.getElementById(lngId);
  const nhDropdown = document.getElementById(nhId);
  const nhToggle = document.getElementById(nhToggleId);
  let timer, active = -1, data = [];

  function selectNominatim(item) {
    input.value = item.display_name.split(",").slice(0, 3).join(",");
    latField.value = item.lat;
    lngField.value = item.lon;
    results.style.display = "none";
  }

  function selectNeighborhood(name, lat, lng) {
    console.log("selectNeighborhood", name, lat, lng);
    input.value = name;
    latField.value = lat;
    lngField.value = lng;
    nhDropdown.style.display = "none";
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    results.style.display = "none";
    latField.value = "";
    lngField.value = "";
    if (input.value.length < 3) return;
    timer = setTimeout(async () => {
      try {
        const q = input.value.match(/medell[ií]n/i) ? input.value : input.value + ", Medellín";
        const r = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=6&countrycodes=co&viewbox=${MEDELLIN_VIEWBOX}&bounded=0`, {headers: {"User-Agent": "MoviliData/1.0"}});
        data = await r.json();
        if (!data.length) { results.style.display = "none"; return; }
        results.innerHTML = data.map((x, i) => `<div class="ac-item" data-idx="${i}"><span>${x.display_name.split(",").slice(0, 3).join(",")}</span><span class="ac-sub">${x.type || "direccion"}</span></div>`).join("");
        results.style.display = "block";
        active = -1;
      } catch (e) { results.style.display = "none"; }
    }, 350);
  });

  results.addEventListener("click", e => {
    const item = e.target.closest(".ac-item");
    if (!item) return;
    selectNominatim(data[Number(item.dataset.idx)]);
  });

  input.addEventListener("keydown", e => {
    const items = results.querySelectorAll(".ac-item");
    if (!items.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); active = Math.min(active + 1, items.length - 1); _highlight(items); }
    else if (e.key === "ArrowUp") { e.preventDefault(); active = Math.max(active - 1, -1); _highlight(items); }
    else if (e.key === "Enter" && active >= 0) { e.preventDefault(); selectNominatim(data[active]); }
  });

  input.addEventListener("blur", () => {
    setTimeout(() => {
      if (latField.value && lngField.value) return;
      const q = input.value.trim();
      if (q.length < 3) return;
      const sq = q.match(/medell[ií]n/i) ? q : q + ", Medellín";
      fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(sq)}&format=json&limit=1&countrycodes=co&viewbox=${MEDELLIN_VIEWBOX}&bounded=0`,
        { headers: { "User-Agent": "MoviliData/1.0" } }
      )
        .then(r => r.json())
        .then(d => {
          if (d && d.length > 0) {
            latField.value = d[0].lat;
            lngField.value = d[0].lon;
            input.value = d[0].display_name.split(",").slice(0, 3).join(",");
          }
        })
        .catch(() => {});
    }, 200);
  });

  function _highlight(items) {
    items.forEach((el, i) => el.classList.toggle("active", i === active));
    if (active >= 0) items[active].scrollIntoView({ block: "nearest" });
  }

  console.log("setup", inputId, "nhToggle:", !!nhToggle, "nhDropdown:", !!nhDropdown);
  nhToggle.addEventListener("click", (e) => {
    console.log("CLICK toggle", nhToggle.id, "dropdown display was:", nhDropdown.style.display);
    e.stopPropagation(); // evita que el click llegue al listener global
    const all = document.querySelectorAll(".nh-dropdown");
    all.forEach(el => { if (el !== nhDropdown) el.style.display = "none"; });
    nhDropdown.style.display = nhDropdown.style.display === "none" ? "block" : "none";
    console.log("dropdown display now:", nhDropdown.style.display);
  });

  nhDropdown.addEventListener("click", (e) => {
    e.stopPropagation(); // evita que el click en un item cierre el dropdown antes de procesar
    const item = e.target.closest(".ac-item");
    if (!item) return;
    selectNeighborhood(item.dataset.value, item.dataset.lat, item.dataset.lng);
    nhDropdown.style.display = "none";
  });

  _acInstances.push({ input, results, nhDropdown, nhToggle });
  console.log("_acInstances pushed, total:", _acInstances.length);
}

const SPEED_MAP = { driving: 30, cycling: 15, walking: 5 };
const MODE_ICON = { driving: "🚗", cycling: "🚲", walking: "🚶" };

const MODE_COLORS = {
  driving: "#38bdf8",
  cycling: "#4ade80",
  walking: "#fb923c",
};

const MODE_ICONS = {
  driving: "🚗",
  cycling: "🚲",
  walking: "🚶",
};

const MODE_SPEEDS = {
  driving: 30,
  cycling: 15,
  walking: 5,
};

function stopSimulation() {
  if (__simInterval) {
    clearInterval(__simInterval);
    __simInterval = null;
  }
  if (__simMarker) {
    liveMaps["routesMap"]?.map.removeLayer(__simMarker);
    __simMarker = null;
  }
  __simRoute = null;
  const btn = document.getElementById("btnSimular");
  if (btn) {
    btn.textContent = "▶ Simular recorrido";
    btn.style.background = "";
    btn.style.borderColor = "";
  }
}

function startSimulation(route) {
  stopSimulation();

  const mapState = liveMaps["routesMap"];
  if (!mapState || !route || !route.points || route.points.length < 2) {
    MoviliLive.toast("No hay ruta disponible para simular", "warning");
    return;
  }

  __simRoute = route;
  const points   = route.points;
  const mode     = route.mode || "driving";
  const modeIcon = { driving: "🚗", cycling: "🚲", walking: "🚶" }[mode] || "🚗";
  const intervalMs = { driving: 25, cycling: 45, walking: 75 }[mode] || 25;

  __simMarker = L.marker(points[0], {
    icon: L.divIcon({
      html: `<span style="font-size:1.5rem;line-height:1;filter:drop-shadow(0 2px 4px rgba(0,0,0,.8))">${modeIcon}</span>`,
      className: "",
      iconAnchor: [12, 12],
    }),
    zIndexOffset: 1000,
  }).addTo(mapState.map);

  const btn = document.getElementById("btnSimular");
  if (btn) {
    btn.textContent = "⏹ Detener simulación";
    btn.style.background  = "#f59e0b";
    btn.style.borderColor = "#f59e0b";
  }

  let i = 0;
  const total = points.length;

  __simInterval = setInterval(() => {
    if (i >= total) {
      stopSimulation();
      MoviliLive.toast("Recorrido completado ✅", "success");
      return;
    }

    __simMarker.setLatLng(points[i]);

    if (i % 10 === 0) {
      mapState.map.panTo(points[i], { animate: true, duration: 0.4 });
    }

    i++;
  }, intervalMs);
}

function modeTime(route) {
  const mode = document.getElementById("routeMode")?.value || "driving";
  const speed = SPEED_MAP[mode] || 30;
  return Math.max(1, Math.round((route.distance || 0) / speed * 60));
}

function modeLabel() {
  const mode = document.getElementById("routeMode")?.value || "driving";
  return MODE_ICON[mode] || "🚗";
}

function riskBadge(risk) {
  if (risk == null) return `<span class="badge-risk">N/D</span>`;
  const cls = risk >= 75 ? "risk-high" : risk >= 55 ? "risk-mid" : "risk-low";
  return `<span class="badge-risk ${cls}">${risk}% riesgo</span>`;
}

function renderRouteList(el, routes) {
  if (!routes || routes.length === 0) {
    MoviliLive.setHTML(el, `<div class="route-item"><p>No se encontraron rutas. Verifica origen y destino.</p></div>`);
    return;
  }

  const selectedMode = document.getElementById("routeMode")?.value || "all";
  const visible = selectedMode === "all"
    ? routes
    : routes.filter(r => r.mode === selectedMode);

  if (visible.length === 0) {
    MoviliLive.setHTML(el, `<div class="route-item"><p>Sin rutas para el modo seleccionado.</p></div>`);
    return;
  }

  // Build prominent summary card for the best route
  const best = visible[0];
  const bestIcon = MODE_ICONS[best.mode] || "🚗";
  const bestColor = MODE_COLORS[best.mode] || "#38bdf8";
  const bestTime = best.time || Math.max(1, Math.round((best.distance || 0) / (MODE_SPEEDS[best.mode] || 30) * 60));
  const modeLabels = { driving: "En carro", cycling: "En bicicleta", walking: "A pie" };
  const bestModeLabel = modeLabels[best.mode] || best.mode;

  let summaryHtml = `<div class="route-summary-card" style="
    background: linear-gradient(135deg, rgba(${bestColor === '#38bdf8' ? '56,189,248' : bestColor === '#4ade80' ? '74,222,128' : '251,146,60'},.15), rgba(9,16,28,.9));
    border: 1px solid ${bestColor}44;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 14px;
    position: relative;
    overflow: hidden;
  ">
    <div style="position:absolute;top:0;right:0;width:80px;height:80px;background:${bestColor}11;border-radius:0 0 0 80px;"></div>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
      <span style="font-size:1.8rem;">${bestIcon}</span>
      <div>
        <div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em;font-weight:600;">Ruta recomendada · ${bestModeLabel}</div>
        <div style="font-size:.85rem;color:var(--text-bright);font-weight:500;margin-top:2px;">${best.origin} → ${best.destination}</div>
      </div>
    </div>
    <div style="display:flex;gap:16px;align-items:baseline;">
      <div style="text-align:center;">
        <div style="font-size:2.2rem;font-weight:700;color:${bestColor};line-height:1;">${bestTime}</div>
        <div style="font-size:.7rem;color:var(--text-soft);margin-top:2px;">minutos</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:1.3rem;font-weight:600;color:var(--text-bright);line-height:1;">${best.distance}</div>
        <div style="font-size:.7rem;color:var(--text-soft);margin-top:2px;">km</div>
      </div>
      ${best.speed != null ? `<div style="text-align:center;">
        <div style="font-size:1.3rem;font-weight:600;color:var(--text-bright);line-height:1;">${best.speed}</div>
        <div style="font-size:.7rem;color:var(--text-soft);margin-top:2px;">km/h</div>
      </div>` : ''}
      ${best.risk != null ? `<div style="text-align:center;">
        <div style="font-size:1.3rem;font-weight:600;color:${best.risk >= 75 ? '#ef4444' : best.risk >= 55 ? '#f59e0b' : '#22c55e'};line-height:1;">${best.risk}%</div>
        <div style="font-size:.7rem;color:var(--text-soft);margin-top:2px;">riesgo</div>
      </div>` : ''}
    </div>
    <button
      id="btnSimular"
      onclick="__simInterval ? stopSimulation() : startSimulation(window.__lastRoutesData?.routes?.[0])"
      style="
        margin-top:12px;
        width:100%;
        padding:7px 0;
        border-radius:8px;
        border:1px solid #22c55e;
        background:transparent;
        color:#22c55e;
        font-size:.8rem;
        font-weight:600;
        letter-spacing:.04em;
        cursor:pointer;
        transition:opacity .3s;
      "
      onmouseover="this.style.opacity='.7'"
      onmouseout="this.style.opacity='1'"
    >▶ Simular recorrido</button>
  </div>`;

  const html = visible.slice(1).map((r, i) => {
    const icon = MODE_ICONS[r.mode] || "🚗";
    const color = MODE_COLORS[r.mode] || "#38bdf8";
    const t = r.time || Math.max(1, Math.round((r.distance || 0) / (MODE_SPEEDS[r.mode] || 30) * 60));
    const riskHtml = riskBadge(r.risk);
    const congestionHtml = r.congestion != null
      ? `<span class="dot">·</span><span>🚦 ${r.congestion}% cong.</span>`
      : "";
    const speedHtml = r.speed != null
      ? `<span class="dot">·</span><span>${r.speed} km/h</span>`
      : "";
    const sourceHtml = r.source && r.source !== "sin datos"
      ? `<div class="route-source" style="font-size:.7rem;color:var(--text-muted);margin-top:3px;">
           Fuente: ${r.source === "TomTom Traffic API" ? "🛰️ TomTom" : r.source}
           ${r.incidents > 0 ? ` · ⚠️ ${r.incidents} incidente(s)` : ""}
         </div>`
      : "";

    return `<div class="route-item" style="border-left:3px solid ${color};cursor:pointer;transition:background .2s;" onmouseenter="this.style.background='rgba(255,255,255,.04)'" onmouseleave="this.style.background='transparent'">
      <div class="route-header">
        <span class="route-index" style="background:${color};color:#000">${i + 2}</span>
        <span class="route-name">${icon} ${r.name}</span>
        ${riskHtml}
      </div>
      <div class="route-meta">
        <span>📏 ${r.distance} km</span>
        <span class="dot">·</span>
        <span style="font-weight:600;color:${color};">⏱ ${t} min</span>
        ${speedHtml}
        ${congestionHtml}
      </div>
      ${sourceHtml}
    </div>`;
  }).join("");

  MoviliLive.setHTML(el, summaryHtml + html);
}

function clearRoutes() {
  stopSimulation();
  document.getElementById("routeOrigin").value = "";
  document.getElementById("routeDest").value = "";
  document.getElementById("routeOriginLat").value = "";
  document.getElementById("routeOriginLng").value = "";
  document.getElementById("routeDestLat").value = "";
  document.getElementById("routeDestLng").value = "";
  document.getElementById("routesList").innerHTML = `<div class="route-item"><p>Selecciona origen y destino para ver rutas</p></div>`;
  if (liveMaps["routesMap"]) {
    liveMaps["routesMap"].layer.clearLayers();
  }
  try { history.replaceState(null, "", "/routes/"); } catch(e) {}
}

function renderHistory() {
  const el = document.getElementById("routesHistory");
  if (!el) return;
  const history = JSON.parse(sessionStorage.getItem("routeHistory") || "[]");
  if (history.length === 0) {
    el.innerHTML = `<div class="text-muted small">Sin historial</div>`;
    return;
  }
  el.innerHTML = history.map((h, i) =>
    `<div class="history-item" data-origin="${h.origin}" data-dest="${h.dest}" data-origin-lat="${h.originLat||''}" data-origin-lng="${h.originLng||''}" data-dest-lat="${h.destLat||''}" data-dest-lng="${h.destLng||''}">
      <span>${h.displayOrigin||h.origin} → ${h.displayDest||h.dest}</span>
      <small>${h.time}</small>
    </div>`
  ).join("");

  el.querySelectorAll(".history-item").forEach(item => {
    item.addEventListener("click", () => {
      document.getElementById("routeOrigin").value = item.dataset.origin;
      document.getElementById("routeDest").value = item.dataset.dest;
      document.getElementById("routeOriginLat").value = item.dataset.originLat;
      document.getElementById("routeOriginLng").value = item.dataset.originLng;
      document.getElementById("routeDestLat").value = item.dataset.destLat;
      document.getElementById("routeDestLng").value = item.dataset.destLng;
      searchRoutes();
    });
  });
}

function addToHistory(origin, dest, originLat, originLng, destLat, destLng) {
  const history = JSON.parse(sessionStorage.getItem("routeHistory") || "[]");
  const key = `${origin}→${dest}`;
  const existing = history.findIndex(h => `${h.origin}→${h.dest}` === key);
  if (existing !== -1) history.splice(existing, 1);
  history.unshift({
    origin,
    dest,
    originLat: originLat || "",
    originLng: originLng || "",
    destLat: destLat || "",
    destLng: destLng || "",
    displayOrigin: document.getElementById("routeOrigin").value,
    displayDest: document.getElementById("routeDest").value,
    time: new Date().toLocaleTimeString("es-CO", {hour: "2-digit", minute: "2-digit"})
  });
  if (history.length > 10) history.length = 10;
  sessionStorage.setItem("routeHistory", JSON.stringify(history));
  renderHistory();
}

async function searchRoutes() {
  stopSimulation();
  const origin = document.getElementById("routeOrigin").value.trim();
  const dest   = document.getElementById("routeDest").value.trim();
  const listEl = document.getElementById("routesList");
  const btn    = document.querySelector("#routeForm .btn-info");

  if (!origin || !dest) {
    MoviliLive.toast("Escribe origen y destino", "warning");
    return;
  }

  btn.disabled = true;
  btn.textContent = "Buscando...";
  listEl.innerHTML = '<div class="route-item"><p>⏳ Resolviendo ubicaciones...</p></div>';

  // ── 1. Geocodificar origen y destino ──────────────────────────────────────
  let originLat = document.getElementById("routeOriginLat").value;
  let originLng = document.getElementById("routeOriginLng").value;
  let destLat   = document.getElementById("routeDestLat").value;
  let destLng   = document.getElementById("routeDestLng").value;

  async function geocode(text) {
    const q = text.match(/medell[ií]n/i) ? text : text + ", Medellín Colombia";
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=1&countrycodes=co&viewbox=${MEDELLIN_VIEWBOX}&bounded=0`;
    const r = await fetch(url, { headers: { "Accept-Language": "es", "User-Agent": "MoviliData/1.0" } });
    const d = await r.json();
    if (d && d.length > 0) return { lat: d[0].lat, lng: d[0].lon, name: d[0].display_name.split(",").slice(0,3).join(",") };
    return null;
  }

  if (!originLat || !originLng) {
    listEl.innerHTML = '<div class="route-item"><p>⏳ Buscando origen...</p></div>';
    const geo = await geocode(origin).catch(() => null);
    if (!geo) {
      MoviliLive.toast("No se encontró el origen. Intenta con otro nombre.", "warning");
      btn.disabled = false; btn.textContent = "Buscar ruta";
      listEl.innerHTML = '<div class="route-item"><p>Selecciona origen y destino para ver rutas</p></div>';
      return;
    }
    originLat = geo.lat; originLng = geo.lng;
    document.getElementById("routeOriginLat").value = originLat;
    document.getElementById("routeOriginLng").value = originLng;
    document.getElementById("routeOrigin").value = geo.name;
  }

  if (!destLat || !destLng) {
    listEl.innerHTML = '<div class="route-item"><p>⏳ Buscando destino...</p></div>';
    const geo = await geocode(dest).catch(() => null);
    if (!geo) {
      MoviliLive.toast("No se encontró el destino. Intenta con otro nombre.", "warning");
      btn.disabled = false; btn.textContent = "Buscar ruta";
      listEl.innerHTML = '<div class="route-item"><p>Selecciona origen y destino para ver rutas</p></div>';
      return;
    }
    destLat = geo.lat; destLng = geo.lng;
    document.getElementById("routeDestLat").value = destLat;
    document.getElementById("routeDestLng").value = destLng;
    document.getElementById("routeDest").value = geo.name;
  }

  // ── 2. Consultar OSRM desde el navegador ─────────────────────────────────
  listEl.innerHTML = '<div class="route-item"><p>⏳ Calculando rutas...</p></div>';

  const selectedMode = document.getElementById("routeMode")?.value || "driving";
  const modes = selectedMode === "all"
    ? ["driving", "cycling", "walking"]
    : [selectedMode];

  const OSRM_URLS = {
    driving: `https://router.project-osrm.org/route/v1/driving/${originLng},${originLat};${destLng},${destLat}?geometries=geojson&overview=full&steps=false`,
    cycling: `https://routing.openstreetmap.de/routed-bike/route/v1/driving/${originLng},${originLat};${destLng},${destLat}?geometries=geojson&overview=full&steps=false`,
    walking: `https://routing.openstreetmap.de/routed-foot/route/v1/driving/${originLng},${originLat};${destLng},${destLat}?geometries=geojson&overview=full&steps=false`,
  };

  const FALLBACK_SPEEDS = { driving: 30, cycling: 15, walking: 5 };
  const MODE_LABELS = { driving: "🚗 En carro", cycling: "🚲 En bicicleta", walking: "🚶 A pie" };

  function haversineKm(lat1, lng1, lat2, lng2) {
    const R = 6371, toRad = x => x * Math.PI / 180;
    const dLat = toRad(lat2 - lat1), dLng = toRad(lng2 - lng1);
    const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng/2)**2;
    return Math.round(R * 2 * Math.asin(Math.sqrt(a)) * 1.35 * 100) / 100;
  }

  async function fetchOsrm(mode) {
    try {
      const r = await fetch(OSRM_URLS[mode]);
      const d = await r.json();
      if (d.code === "Ok" && d.routes && d.routes.length > 0) {
        const route = d.routes[0];
        const points = route.geometry.coordinates.map(c => [c[1], c[0]]);
        const dist   = Math.round(route.distance / 1000 * 100) / 100;
        const time   = Math.max(1, Math.round(route.duration / 60));
        return { points, dist, time, source: "OSRM" };
      }
    } catch (e) { console.warn(`[OSRM ${mode}]`, e); }
    // Fallback haversine si OSRM falla
    const dist = haversineKm(parseFloat(originLat), parseFloat(originLng), parseFloat(destLat), parseFloat(destLng));
    const time = Math.max(1, Math.round(dist / FALLBACK_SPEEDS[mode] * 60));
    return {
      points: [[parseFloat(originLat), parseFloat(originLng)], [parseFloat(destLat), parseFloat(destLng)]],
      dist, time, source: "estimado"
    };
  }

  const osrmResults = await Promise.all(modes.map(m => fetchOsrm(m)));

  // ── 3. Enriquecer con TomTom via backend ──────────────────────────────────
  listEl.innerHTML = '<div class="route-item"><p>⏳ Obteniendo datos de tráfico...</p></div>';

  const routesPayload = modes.map((m, i) => ({
    mode: m,
    points: osrmResults[i].points,
    dist:   osrmResults[i].dist,
    time:   osrmResults[i].time,
    source: osrmResults[i].source,
  }));

  let data;
  try {
    const resp = await fetch("/api/routes", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({
        origin: document.getElementById("routeOrigin").value,
        destination: document.getElementById("routeDest").value,
        origin_lat: originLat,
        origin_lng: originLng,
        dest_lat: destLat,
        dest_lng: destLng,
        mode: selectedMode,
        routes_data: routesPayload,
      }),
    });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    data = await resp.json();
  } catch (err) {
    console.warn("[searchRoutes] backend falló, usando OSRM local:", err);
  }

  if (!data || !data.routes || data.routes.length === 0) {
    console.warn("[searchRoutes] sin datos del backend, construyendo desde OSRM local");
    const originName = document.getElementById("routeOrigin").value;
    const destName = document.getElementById("routeDest").value;
    data = {
      routes: routesPayload.map(r => ({
        name: `${MODE_LABELS[r.mode]}: ${originName} → ${destName}`,
        origin: originName,
        destination: destName,
        mode: r.mode,
        distance: r.dist,
        time: r.time,
        risk: null,
        congestion: null,
        speed: null,
        incidents: 0,
        rain_probability: null,
        source: "OSRM (sin TomTom)",
        points: r.points,
      })),
    };
  }

  window.__lastRoutesData = data;
  renderRouteList(listEl, data.routes);
  await window.renderRoutesMap("routesMap", data);
  addToHistory(
    document.getElementById("routeOrigin").value,
    document.getElementById("routeDest").value,
    originLat, originLng, destLat, destLng
  );

  btn.disabled = false;
  btn.textContent = "Buscar ruta";
}

window.renderRoutesMap = async function(id, data) {
  console.log("[renderRoutesMap] called, data:", data ? "yes" : "no");
  if (!data) return;
  const map = createOsmMap(id);
  if (!map) { console.error("[renderRoutesMap] createOsmMap returned null"); return; }
  const layer = dynamicLayer(id);
  layer.clearLayers();

  // Use all routes from data directly — the API already filters by mode
  const visibleRoutes = data.routes || [];
  console.log("[renderRoutesMap] visibleRoutes:", visibleRoutes.length);

  if (visibleRoutes.length === 0) return;

  const allBounds = [];

  visibleRoutes.forEach(route => {
    const color = MODE_COLORS[route.mode] || "#38bdf8";
    const icon = MODE_ICONS[route.mode] || "🚗";
    const t = route.time || Math.max(1, Math.round((route.distance || 0) / (MODE_SPEEDS[route.mode] || 30) * 60));
    const riskDisplay = route.risk != null ? `${route.risk}%` : "Sin datos";
    const riskLevel = route.risk == null
      ? "⚪ Sin datos TomTom"
      : route.risk >= 75 ? "🔴 Alto"
      : route.risk >= 55 ? "🟠 Medio"
      : "🟢 Bajo";
    const congText = route.congestion != null ? `${route.congestion}%` : "N/D";
    const speedText = route.speed != null ? `${route.speed} km/h` : "N/D";

    L.polyline(route.points, { color: "#fff", weight: 10, opacity: 0.25 }).addTo(layer);
    L.polyline(route.points, { color, weight: 6, opacity: 0.95 }).addTo(layer);
    const line = L.polyline(route.points, { color: "#fff", weight: 2, opacity: 0.8 })
      .addTo(layer)
      .bindPopup(
        `<strong>${icon} ${route.origin} → ${route.destination}</strong><br>` +
        `${route.distance} km · ${t} min · Riesgo: ${riskDisplay}`
      )
      .bindTooltip(
        `<strong>${icon} ${route.origin} → ${route.destination}</strong>` +
        `<table>` +
        `<tr><td class="label">📏 Distancia</td><td class="value">${route.distance} km</td></tr>` +
        `<tr><td class="label">⏱ Tiempo real OSRM</td><td class="value">${t} min</td></tr>` +
        `<tr><td class="label">🚦 Congestión</td><td class="value">${congText}</td></tr>` +
        `<tr><td class="label">💨 Velocidad</td><td class="value">${speedText}</td></tr>` +
        `<tr><td class="label">⚠️ Índice afectación</td><td class="value">${riskDisplay}</td></tr>` +
        `<tr><td class="label">🔵 Nivel riesgo</td><td class="value">${riskLevel}</td></tr>` +
        `<tr><td class="label">📡 Fuente</td><td class="value">${route.source || "sin datos"}</td></tr>` +
        `</table>`,
        { sticky: true, className: "clima-tooltip" }
      );

    // Collect bounds for fitBounds later
    try { allBounds.push(line.getBounds()); } catch(e) {}

    line.on("click", () => map.fitBounds(line.getBounds(), { padding: [24, 24] }));

    L.circleMarker(route.points[0], {
      radius: 8, color: "#fff", weight: 2, fillColor: "#22c55e", fillOpacity: 0.9
    }).addTo(layer)
      .bindPopup(`<strong>📍 Origen</strong><br>${route.origin}`)
      .bindTooltip(`<strong>${route.origin}</strong><br><span class="label">Origen</span>`,
        { sticky: true, className: "clima-tooltip" });

    const last = route.points[route.points.length - 1];
    L.circleMarker(last, {
      radius: 8, color: "#fff", weight: 2, fillColor: "#f59e0b", fillOpacity: 0.9
    }).addTo(layer)
      .bindPopup(`<strong>🏁 Destino</strong><br>${route.destination}`)
      .bindTooltip(`<strong>${route.destination}</strong><br><span class="label">Destino</span>`,
        { sticky: true, className: "clima-tooltip" });
  });

  // Auto-fit map to show all route lines
  if (allBounds.length > 0) {
    try {
      let combined = allBounds[0];
      for (let i = 1; i < allBounds.length; i++) {
        combined = combined.extend(allBounds[i]);
      }
      map.fitBounds(combined, { padding: [40, 40], maxZoom: 15 });
    } catch(e) { console.warn("[renderRoutesMap] fitBounds error:", e); }
  }

  const selectedMode = document.getElementById("routeMode")?.value || "driving";
  const caption = document.getElementById("routeCaption");
  if (caption) {
    const modeLabel = (MODE_ICONS[selectedMode] || "🚗") + " " + (selectedMode === "driving" ? "Carro" : selectedMode === "cycling" ? "Bicicleta" : selectedMode === "walking" ? "A pie" : selectedMode);
    caption.textContent = `${visibleRoutes.length} ruta(s) — ${modeLabel}`;
  }

  MoviliLive.flash(document.getElementById(id));
};

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("routeForm");
  if (!form) return;

  _setupAutocomplete("routeOrigin", "routeOriginResults", "routeOriginLat", "routeOriginLng", "routeOriginNh", "originNhToggle");
  _setupAutocomplete("routeDest", "routeDestResults", "routeDestLat", "routeDestLng", "routeDestNh", "destNhToggle");

  // Listener global único — registrado DESPUÉS de _setupAutocomplete
  // para que _acInstances ya tenga las dos instancias.
  // stopPropagation en nhToggle y nhDropdown evita que sus clicks lleguen aquí.
  document.addEventListener("click", (e) => {
    _acInstances.forEach(({ input, results, nhDropdown, nhToggle }) => {
      if (!results.contains(e.target) && e.target !== input) {
        results.style.display = "none";
      }
      if (!nhDropdown.contains(e.target) && e.target !== nhToggle) {
        nhDropdown.style.display = "none";
      }
    });
  });

  createOsmMap("routesMap");

  form.addEventListener("submit", e => {
    e.preventDefault();
    searchRoutes();
  });

  document.getElementById("clearRoute").addEventListener("click", clearRoutes);
  document.getElementById("clearHistory").addEventListener("click", () => {
    sessionStorage.removeItem("routeHistory");
    renderHistory();
  });
  document.getElementById("routeMode").addEventListener("change", () => {
    // Re-search with the new mode to get OSRM route for the correct profile
    const origin = document.getElementById("routeOrigin").value;
    const dest = document.getElementById("routeDest").value;
    if (origin && dest) {
      searchRoutes();
    }
  });
  renderHistory();

});
