const levelLabel = { alta: "Alta", media: "Media", baja: "Baja" };

function alertMarkup(alert) {
  const label = levelLabel[alert.level] || alert.level;
  return `<article class="alert-card ${alert.level} panel">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
      <span class="badge-risk">${alert.icon || ""} ${label}</span>
      <small style="color:var(--text-muted);font-size:.7rem;">🕐 ${alert.generated_at || ""}</small>
    </div>
    <h2 style="font-size:.9rem;margin-bottom:4px;">${alert.title}</h2>
    <p style="font-size:.8rem;color:var(--text-soft);margin-bottom:4px;">${alert.description}</p>
    <small style="color:var(--text-muted);">📍 ${alert.zone}</small>
  </article>`;
}

async function renderAlerts() {
  const page = document.getElementById("alertsPage");
  if (!page) return;
  let data;
  try {
    data = await MoviliAPI.alerts();
  } catch {
    const boot = await MoviliAPI.bootstrap();
    data = boot;
  }
  const alerts = data && data.alerts ? data.alerts : [];
  const html = alerts.length
    ? alerts.map(alertMarkup).join("")
    : '<article class="alert-card panel"><p class="text-muted">Sin alertas activas</p></article>';
  MoviliLive.setHTML(page, html);
  page.dataset.state = "loaded";
}

document.addEventListener("DOMContentLoaded", () => {
  MoviliLive.register(() => renderAlerts().catch(console.error), MoviliLive.intervalMs);
});
