let chartRefs = {};

function upsertChart(id, type, labels, data, label, color = "#38bdf8") {
  const canvas = document.getElementById(id);
  if (!canvas || !window.Chart) return;
  if (chartRefs[id]) chartRefs[id].destroy();
  chartRefs[id] = new Chart(canvas, {
    type,
    data: {labels, datasets: [{label, data, borderColor: color, backgroundColor: color + "55", tension: .35, fill: type === "line"}]},
    options: {responsive: true, plugins: {legend: {labels: {color: "#dbeafe"}}}, scales: {x: {ticks: {color: "#9fb2cf"}, grid: {color: "rgba(255,255,255,.08)"}}, y: {ticks: {color: "#9fb2cf"}, grid: {color: "rgba(255,255,255,.08)"}}}}
  });
}

async function renderCoreCharts() {
  const targets = ["congestionChart", "accidentChart", "rainChart", "landingChart"];
  if (!targets.some(id => document.getElementById(id))) return;
  const traffic = await MoviliAPI.traffic();
  const labels = traffic.traffic.map(x => x.zone);
  upsertChart("congestionChart", "bar", labels, traffic.traffic.map(x => x.congestion_level), "Congestion", "#38bdf8");
  upsertChart("accidentChart", "line", ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"], [18, 22, 20, 29, 33, 27, 24], "Accidentes", "#ef4444");
  upsertChart("rainChart", "line", labels, traffic.traffic.map(x => Math.max(10, x.congestion_level - 15)), "Lluvia vs trafico", "#22c55e");
  upsertChart("landingChart", "doughnut", labels.slice(0, 4), traffic.traffic.slice(0, 4).map(x => x.congestion_level), "Riesgo", "#2563eb");
}

async function renderPredictionChart(hour = 18) {
  if (!document.getElementById("predictionChart")) return;
  const data = await MoviliAPI.predictions(hour);
  upsertChart("predictionChart", "bar", data.predictions.map(x => x.zone), data.predictions.map(x => x.predicted_congestion), `Hora ${hour}:00`, "#f59e0b");
}

document.addEventListener("DOMContentLoaded", () => {
  MoviliLive.register(() => renderCoreCharts().catch(console.error), MoviliLive.intervalMs);
  const range = document.getElementById("hourRange");
  MoviliLive.register(() => renderPredictionChart(range ? range.value : 18).catch(console.error), MoviliLive.intervalMs);
  if (range) range.addEventListener("input", event => renderPredictionChart(event.target.value));
});
