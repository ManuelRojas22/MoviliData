async function renderDashboard() {
  const grid = document.getElementById("metricGrid");
  const weather = document.getElementById("weatherPanel");
  const table = document.getElementById("trafficTable");
  const routes = document.getElementById("routesList");
  const feed = document.getElementById("alertsFeed");
  if (!grid && !weather && !table && !routes && !feed) return;

  const [boot] = await MoviliAPI.fetchAll(MoviliAPI.bootstrap);

  if (grid && boot && boot.metrics) {
    const levelClass={'Alto':'risk-high','Medio':'risk-mid','Bajo':'risk-low','Datos insuficientes':'risk-na'};
    const html = boot.metrics.map(m => {
      const lvl = m.level || '—';
      return `<article class="metric-card ${levelClass[lvl]||''}"><span>${m.label}</span><strong>${m.value}${m.unit}</strong><small>${lvl}</small></article>`;
    }).join("");
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
    const html = boot.zones.map(t => {
      const cg=Number(t.congestion_level), sp=Number(t.average_speed), ic=Number(t.incidents);
      const cgCl=cg>=75?'cg-high':cg>=55?'cg-mid':'cg-low';
      const spCl=sp>40?'sp-fast':sp>=20?'sp-mid':'sp-slow';
      const icCl=ic>15?'ic-high':ic>=6?'ic-mid':ic>0?'ic-low':'ic-none';
      const src=t.source==='TomTom Traffic API'?'🛰️ TomTom':'📊 Estimado';
      return `<tr><td>${t.zone}</td><td><span class="congestion ${cgCl}">${cg}%</span></td><td><span class="speed ${spCl}">${sp}</span> km/h</td><td><span class="incidents ${icCl}">${ic}</span></td><td>${src}</td></tr>`;
    }).join("");
    MoviliLive.setHTML(table, html);
  }
  if (feed && boot && boot.alerts && boot.alerts.length) {
    const html = boot.alerts.map(a => `<article class="alert-card ${a.level}"><span class="badge-risk">${a.level}</span><h2>${a.title}</h2><p>${a.description}</p><small>${a.zone}</small></article>`).join("");
    MoviliLive.setHTML(feed, html);
  }
  if (boot && boot.accidents_api_ok === false) {
    const feed = document.getElementById("alertsFeed");
    if (feed) {
      const warning = document.createElement("article");
      warning.className = "alert-card medium";
      warning.innerHTML = '<span class="badge-risk">aviso</span><h2>⚠️ Incidentes TomTom no disponibles</h2><p>La API de incidentes de tr\u00e1fico no est\u00e1 respondiendo. Los conteos de incidentes por zona pueden estar en 0.</p><small>Los datos de flujo y congesti\u00f3n no se ven afectados</small>';
      feed.prepend(warning);
    }
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
