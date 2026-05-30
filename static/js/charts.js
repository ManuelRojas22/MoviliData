let chartRefs = {};
let chartsLoaded = false;

function hideChartSpinner(id) {
  const spinner = document.getElementById(`spinner-${id}`);
  if (spinner) spinner.style.display = "none";
}

function upsertChart(id, type, labels, data, label, color = "#38bdf8") {
  const canvas = document.getElementById(id);
  if (!canvas || !window.Chart) return;
  hideChartSpinner(id);
  if (chartRefs[id]) {
    const chart = chartRefs[id];
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.data.datasets[0].label = label;
    chart.data.datasets[0].borderColor = color;
    chart.data.datasets[0].backgroundColor = color + "55";
    chart.update("none");
    return;
  }
  chartRefs[id] = new Chart(canvas, {
    type,
    data: {labels, datasets: [{label, data, borderColor: color, backgroundColor: color + "55", tension: .35, fill: type === "line"}]},
    options: {responsive: true, animation: false, plugins: {legend: {labels: {color: "#dbeafe"}}}, scales: {x: {ticks: {color: "#9fb2cf"}, grid: {color: "rgba(255,255,255,.08)"}}, y: {ticks: {color: "#9fb2cf"}, grid: {color: "rgba(255,255,255,.08)"}}}}
  });
}

function isChartVisible(id) {
  const el = document.getElementById(id);
  if (!el) return false;
  if ("IntersectionObserver" in window) return el.dataset.lazyLoaded === "1";
  return true;
}

async function renderCoreCharts() {
  const targets = ["congestionChart", "accidentChart", "rainChart", "landingChart"];
  const visible = targets.filter(isChartVisible);
  if (!visible.length) return;

  const [boot] = await MoviliAPI.fetchAll(MoviliAPI.bootstrap);
  if (!boot || !boot.zones) return;

  const labels = boot.zones.map(x => x.zone);

  if (visible.includes("congestionChart")) {
    upsertChart("congestionChart", "bar", labels,
      boot.zones.map(x => x.congestion_level), "Congestion", "#38bdf8");
  }

  if (visible.includes("accidentChart")) {
    const zoneCoords = boot.zones.map(t => ({name: t.zone, lat: t.lat, lng: t.lng}));
    const incidentsByZone = {};
    (boot.incidents || []).forEach(inc => {
      const ilat = inc.lat, ilng = inc.lng;
      if (!ilat || !ilng) return;
      let nearest = "Desconocido", minDist = 0.05;
      zoneCoords.forEach(z => {
        const d = Math.abs(ilat - z.lat) + Math.abs(ilng - z.lng);
        if (d < minDist) { minDist = d; nearest = z.name; }
      });
      incidentsByZone[nearest] = (incidentsByZone[nearest] || 0) + 1;
    });
    const incLabels = Object.keys(incidentsByZone);
    if (incLabels.length) {
      upsertChart("accidentChart", "bar", incLabels, incLabels.map(z => incidentsByZone[z]), "Incidentes", "#ef4444");
    } else {
      const count = (boot.incidents || []).length;
      upsertChart("accidentChart", "bar", ["Medellin"], [count], "Incidentes", "#ef4444");
    }
  }

  if (visible.includes("rainChart")) {
    const rainProb = boot.weather ? boot.weather.precipitation_probability : 30;
    const rainData = boot.zones.map(x => rainProb);
    upsertChart("rainChart", "line", labels, rainData, "Prob. lluvia %", "#22c55e");
  }

  if (visible.includes("landingChart")) {
    upsertChart("landingChart", "doughnut", labels.slice(0, 4),
      boot.zones.slice(0, 4).map(x => x.congestion_level), "Riesgo", "#2563eb");
  }

  chartsLoaded = true;
}

async function renderPredictionChart(hour = 18) {
  if (!document.getElementById("predictionChart")) return;
  hideChartSpinner("predictionChart");
  const data = await MoviliAPI.predictions(hour);
  const offset = document.getElementById("forecastOffset") ? parseInt(document.getElementById("forecastOffset").value) : 0;
  const zoneLabels = data.predictions.map(x => x.zone);
  const values = data.predictions.map(p => {
    const f = p.forecast && p.forecast[offset] ? p.forecast[offset] : p.forecast && p.forecast[0] ? p.forecast[0] : {predicted_congestion: 50};
    return f.predicted_congestion;
  });
  const forecastHour = (parseInt(hour) + offset) % 24;
  upsertChart("predictionChart", "bar", zoneLabels, values, `Hora ${forecastHour}:00`, "#f59e0b");
}

function upsertMultiDatasetChart(id, type, labels, datasets) {
  const canvas = document.getElementById(id);
  if (!canvas || !window.Chart) return;
  hideChartSpinner(id);
  if (chartRefs[id]) {
    const chart = chartRefs[id];
    chart.data.labels = labels;
    datasets.forEach((ds, i) => {
      if (chart.data.datasets[i]) {
        chart.data.datasets[i].data = ds.data;
        chart.data.datasets[i].label = ds.label;
        chart.data.datasets[i].borderColor = ds.color;
        chart.data.datasets[i].backgroundColor = ds.color + "55";
      } else {
        chart.data.datasets.push({
          label: ds.label, data: ds.data,
          borderColor: ds.color, backgroundColor: ds.color + "55",
          tension: .35, fill: type === "line",
        });
      }
    });
    chart.update("none");
    return;
  }
  chartRefs[id] = new Chart(canvas, {
    type,
    data: {
      labels,
      datasets: datasets.map(ds => ({
        label: ds.label, data: ds.data,
        borderColor: ds.color, backgroundColor: ds.color + "55",
        tension: .35, fill: type === "line",
      })),
    },
    options: {
      responsive: true, animation: false,
      plugins: {legend: {labels: {color: "#dbeafe"}}},
      scales: {
        x: {ticks: {color: "#9fb2cf"}, grid: {color: "rgba(255,255,255,.08)"}},
        y: {ticks: {color: "#9fb2cf"}, grid: {color: "rgba(255,255,255,.08)"}},
      },
    },
  });
}

function renderStatisticsCharts(boot) {
  if (!boot || !boot.zones) return;
  const labels = boot.zones.map(x => x.zone);

  // Congestion semanal — barras
  upsertChart("congestionChart", "bar", labels,
    boot.zones.map(x => x.congestion_level), "Congestion", "#38bdf8");

  // Accidentalidad — barras con conteo de incidentes por zona
  const zoneCoords = boot.zones.map(t => ({name: t.zone, lat: t.lat, lng: t.lng}));
  const incidentsByZone = {};
  (boot.incidents || []).forEach(inc => {
    const ilat = inc.lat, ilng = inc.lng;
    if (!ilat || !ilng) return;
    let nearest = "Desconocido", minDist = 0.05;
    zoneCoords.forEach(z => {
      const d = Math.abs(ilat - z.lat) + Math.abs(ilng - z.lng);
      if (d < minDist) { minDist = d; nearest = z.name; }
    });
    incidentsByZone[nearest] = (incidentsByZone[nearest] || 0) + 1;
  });
  const incData = labels.map(z => incidentsByZone[z] || 0);
  upsertChart("accidentChart", "bar", labels, incData, "Incidentes", "#ef4444");

  // Lluvia vs trafico — linea doble
  const rainProb = boot.weather ? boot.weather.precipitation_probability : 30;
  const rainData = boot.zones.map(() => rainProb);
  upsertMultiDatasetChart("rainChart", "line", labels, [
    {label: "Prob. lluvia %", data: rainData, color: "#22c55e"},
    {label: "Congestion %", data: boot.zones.map(x => x.congestion_level), color: "#f59e0b"},
  ]);
}

function observeLazyCharts() {
  if (!("IntersectionObserver" in window)) return;
  const targets = ["congestionChart", "accidentChart", "rainChart", "landingChart", "predictionChart"];
  const observer = new IntersectionObserver((entries) => {
    let needsRender = false;
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.dataset.lazyLoaded = "1";
        observer.unobserve(entry.target);
        needsRender = true;
      }
    });
    if (needsRender && !chartsLoaded) renderCoreCharts().catch(console.error);
  }, {rootMargin: "200px"});
  targets.forEach(id => {
    const el = document.getElementById(id);
    if (el) observer.observe(el);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  observeLazyCharts();
  MoviliLive.register(() => renderCoreCharts().catch(console.error), MoviliLive.intervalMs);
  const range = document.getElementById("hourRange");
  MoviliLive.register(() => renderPredictionChart(range ? range.value : 18).catch(console.error), MoviliLive.intervalMs);
  if (range) range.addEventListener("input", event => renderPredictionChart(event.target.value));
  const offsetSlider = document.getElementById("forecastOffset");
  if (offsetSlider) {
    offsetSlider.addEventListener("input", () => {
      const range = document.getElementById("hourRange");
      renderPredictionChart(range ? range.value : 18);
    });
  }
});
