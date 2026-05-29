async function renderDashboard() {
  const grid = document.getElementById("metricGrid");
  const weather = document.getElementById("weatherPanel");
  const table = document.getElementById("trafficTable");
  const routes = document.getElementById("routesList");
  if (!grid && !weather && !table && !routes) return;

  const summary = await MoviliAPI.dashboard();
  if (grid) {
    const html = summary.metrics.map(m => `<article class="metric-card"><span>${m.label}</span><strong>${m.value}${m.unit}</strong><small>${m.trend}% tendencia</small></article>`).join("");
    MoviliLive.setHTML(grid, html);
  }
  if (weather) {
    MoviliLive.setHTML(weather, `
      <div class="alert-item"><strong>${summary.weather.temperature} C</strong><p>Temperatura actual - ${summary.weather.source}</p></div>
      <div class="alert-item"><strong>${summary.weather.precipitation_probability}%</strong><p>Probabilidad de lluvia</p></div>
      <div class="alert-item"><strong>${summary.incidents.length}</strong><p>Incidentes abiertos detectados</p></div>
      <div class="alert-item"><strong>${summary.commercial_api.live_segments}</strong><p>Segmentos TomTom activos</p></div>
    `);
  }
  if (table) {
    const traffic = await MoviliAPI.traffic();
    const html = traffic.traffic.map(t => `<tr><td>${t.zone}</td><td>${t.congestion_level}%</td><td>${t.average_speed} km/h</td><td>${t.incidents}</td><td>${t.status}</td></tr>`).join("");
    MoviliLive.setHTML(table, html);
  }
  if (routes) {
    const data = await MoviliAPI.routes();
    const html = data.routes.map(r => `<div class="route-item"><strong>${r.name}</strong><p>${r.distance} km - ${r.time} min - riesgo ${r.risk}%</p></div>`).join("");
    MoviliLive.setHTML(routes, html);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  MoviliLive.register(() => renderDashboard().catch(console.error), MoviliLive.intervalMs);
  const refresh = document.getElementById("refreshDashboard");
  if (refresh) refresh.addEventListener("click", () => renderDashboard());
});
