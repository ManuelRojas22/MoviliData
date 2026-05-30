async function renderDashboard() {
  const grid = document.getElementById("metricGrid");
  const weather = document.getElementById("weatherPanel");
  const table = document.getElementById("trafficTable");
  const routes = document.getElementById("routesList");
  const feed = document.getElementById("alertsFeed");
  if (!grid && !weather && !table && !routes && !feed) return;

  const [boot] = await MoviliAPI.fetchAll(MoviliAPI.bootstrap);

  if (grid && boot && boot.metrics) {
    const html = boot.metrics.map(m => `<article class="metric-card"><span>${m.label}</span><strong>${m.value}${m.unit}</strong><small>${m.trend}% tendencia</small></article>`).join("");
    MoviliLive.setHTML(grid, html);
  }
  if (weather && boot && boot.weather) {
    MoviliLive.setHTML(weather, `
      <div class="alert-item"><strong>${boot.weather.temperature} C</strong><p>Temperatura actual - ${boot.weather.source}</p></div>
      <div class="alert-item"><strong>${boot.weather.precipitation_probability}%</strong><p>Probabilidad de lluvia</p></div>
      <div class="alert-item"><strong>${boot.incidents ? boot.incidents.length : 0}</strong><p>Incidentes abiertos detectados</p></div>
    `);
  }
  if (table && boot && boot.zones && boot.zones.length) {
    const html = boot.zones.map(t => `<tr><td>${t.zone}</td><td>${t.congestion_level}%</td><td>${t.average_speed} km/h</td><td>${t.incidents}</td><td>${t.status}</td></tr>`).join("");
    MoviliLive.setHTML(table, html);
  }
  if (feed && boot && boot.alerts && boot.alerts.length) {
    const html = boot.alerts.map(a => `<article class="alert-card ${a.level}"><span class="badge-risk">${a.level}</span><h2>${a.title}</h2><p>${a.description}</p><small>${a.zone}</small></article>`).join("");
    MoviliLive.setHTML(feed, html);
  }
  if (routes && !document.getElementById("routeForm")) {
    try {
      const rd = await MoviliAPI.routes();
      if (rd && rd.routes && rd.routes.length) {
        const html = rd.routes.map(r => `<div class="route-item"><strong>${r.name}</strong><p>${r.distance} km - ${r.time} min - riesgo ${r.risk}%</p></div>`).join("");
        MoviliLive.setHTML(routes, html);
      }
    } catch(e) { console.error("routes fetch error", e); }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  MoviliLive.register(() => renderDashboard().catch(console.error), MoviliLive.intervalMs);
});
