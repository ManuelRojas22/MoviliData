function riskBadge(risk) {
  const cls = risk >= 75 ? "risk-high" : risk >= 55 ? "risk-mid" : "risk-low";
  return `<span class="badge-risk ${cls}">${risk}% riesgo</span>`;
}

function renderRouteList(el, routes) {
  let html = "";
  if (!routes || routes.length === 0) {
    html = `<div class="route-item"><p>Selecciona origen y destino para ver rutas</p></div>`;
  } else {
    html = routes.map((r, i) => {
      const primary = i === 0 ? "route-primary" : "";
      return `<div class="route-item ${primary}">
        <div class="route-header">
          <span class="route-index">${i + 1}</span>
          <span class="route-name">${r.name}</span>
          ${riskBadge(r.risk)}
        </div>
        <div class="route-meta">
          <span>${r.distance} km</span>
          <span class="dot">·</span>
          <span>${r.time} min</span>
          <span class="dot">·</span>
          <span>${r.origin} → ${r.destination}</span>
        </div>
      </div>`;
    }).join("");
  }
  MoviliLive.setHTML(el, html);
}

function clearRoutes() {
  document.getElementById("routeOrigin").value = "";
  document.getElementById("routeDest").value = "";
  document.getElementById("routesList").innerHTML = `<div class="route-item"><p>Selecciona origen y destino para ver rutas</p></div>`;
  if (liveMaps["routesMap"]) {
    liveMaps["routesMap"].layer.clearLayers();
  }
  history.replaceState(null, "", "/routes/");
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
    `<div class="history-item" data-origin="${h.origin}" data-dest="${h.dest}">
      <span>${h.origin} → ${h.dest}</span>
      <small>${h.time}</small>
    </div>`
  ).join("");

  el.querySelectorAll(".history-item").forEach(item => {
    item.addEventListener("click", () => {
      document.getElementById("routeOrigin").value = item.dataset.origin;
      document.getElementById("routeDest").value = item.dataset.dest;
      searchRoutes();
    });
  });
}

function addToHistory(origin, dest) {
  const history = JSON.parse(sessionStorage.getItem("routeHistory") || "[]");
  const key = `${origin}→${dest}`;
  const existing = history.findIndex(h => `${h.origin}→${h.dest}` === key);
  if (existing !== -1) history.splice(existing, 1);
  history.unshift({
    origin,
    dest,
    time: new Date().toLocaleTimeString("es-CO", {hour: "2-digit", minute: "2-digit"})
  });
  if (history.length > 10) history.length = 10;
  sessionStorage.setItem("routeHistory", JSON.stringify(history));
  renderHistory();
}

async function searchRoutes() {
  const origin = document.getElementById("routeOrigin").value;
  const dest = document.getElementById("routeDest").value;
  const listEl = document.getElementById("routesList");
  const btn = document.querySelector("#routeForm .btn-info");

  if (!origin || !dest) {
    MoviliLive.toast("Selecciona origen y destino", "warning");
    return;
  }
  if (origin === dest) {
    MoviliLive.toast("Origen y destino deben ser diferentes", "warning");
    return;
  }

  btn.disabled = true;
  btn.textContent = "Buscando...";

  try {
    const qs = `?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(dest)}`;
    const data = await MoviliAPI.get(`/api/routes${qs}`);
    renderRouteList(listEl, data.routes);
    await renderRoutesMap("routesMap", data);
    history.replaceState(null, "", `/routes/${qs}`);
    addToHistory(origin, dest);
  } catch (err) {
    MoviliLive.toast("Error al buscar rutas", "error");
    console.error(err);
  } finally {
    btn.disabled = false;
    btn.textContent = "Buscar ruta";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("routeForm");
  if (!form) return;

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

  renderHistory();

  const origin = document.getElementById("routeOrigin").value;
  const dest = document.getElementById("routeDest").value;
  if (origin && dest && origin !== dest) {
    searchRoutes();
  }

  MoviliLive.register(() => {
    const o = document.getElementById("routeOrigin").value;
    const d = document.getElementById("routeDest").value;
    if (o && d && o !== d) searchRoutes();
  }, MoviliLive.intervalMs);
});
