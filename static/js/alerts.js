function alertMarkup(alert) {
  return `<article class="alert-card ${alert.level}"><span class="badge-risk">${alert.level}</span><h2>${alert.title}</h2><p>${alert.description}</p><small>${alert.zone}</small></article>`;
}

async function renderAlerts() {
  const feed = document.getElementById("alertsFeed");
  const page = document.getElementById("alertsPage");
  if (!feed && !page) return;
  const data = await MoviliAPI.alerts();
  const html = data.alerts.map(alertMarkup).join("");
  if (feed) MoviliLive.setHTML(feed, html);
  if (page) MoviliLive.setHTML(page, html);
}

document.addEventListener("DOMContentLoaded", () => {
  MoviliLive.register(() => renderAlerts().catch(console.error), MoviliLive.intervalMs);
});
