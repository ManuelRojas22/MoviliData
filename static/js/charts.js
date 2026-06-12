let chartRefs = {};
let chartsLoaded = false;
let predictionChartRequestId = 0;

function hideChartSpinner(id) {
  const spinner = document.getElementById(`spinner-${id}`);
  if (spinner) spinner.style.display = "none";
}

function upsertChart(id, type, labels, data, label, color = "#38bdf8") {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  if (!window.Chart) { console.warn("[charts] Chart.js no disponible para", id); return; }
  hideChartSpinner(id);
  if (chartRefs[id]) {
    const chart = chartRefs[id];
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.data.datasets[0].label = label;
    chart.data.datasets[0].borderColor = color;
    chart.data.datasets[0].backgroundColor = color + "55";
    chart.update({duration:800,easing:'easeOutQuart'});
    const panel=canvas.closest('.panel');if(panel&&window.MoviliLive)MoviliLive.flash(panel);
    return;
  }
  chartRefs[id] = new Chart(canvas, {
    type,
    data: {labels, datasets: [{label, data, borderColor: color, backgroundColor: color + "55", tension: .35, fill: type === "line"}]},
    options: {responsive: true, animation: {duration:0}, plugins: {legend: {labels: {color: "#dbeafe"}}}, scales: {x: {ticks: {color: "#9fb2cf"}, grid: {color: "rgba(255,255,255,.08)"}}, y: {ticks: {color: "#9fb2cf"}, grid: {color: "rgba(255,255,255,.08)"}}}}
  });
}

function isChartVisible(id) {
  const el = document.getElementById(id);
  if (!el) return false;
  if ("IntersectionObserver" in window) return el.dataset.lazyLoaded === "1";
  return true;
}

function isStatisticsPage() {
  return !!document.getElementById("statsMetrics");
}

async function renderCoreCharts() {
  // Skip if statistics page has its own rendering
  if (isStatisticsPage()) return;

  const targets = ["accidentChart", "rainChart", "landingChart", "speedChart", "incidentChart"];
  const visible = targets.filter(isChartVisible);
  if (!visible.length) return;

  const [boot] = await MoviliAPI.fetchAll(MoviliAPI.bootstrap);
  if (!boot || !boot.zones) return;

  const labels = boot.zones.map(x => x.zone);

  if (visible.includes("speedChart")) {
    upsertChart("speedChart", "bar", labels,
      boot.zones.map(x => x.average_speed || 0), "🚗 Velocidad km/h", "#22c55e");
  }

  if (visible.includes("incidentChart")) {
    upsertChart("incidentChart", "bar", labels,
      boot.zones.map(x => x.incidents || 0), "🚧 Incidentes", "#ef4444");
  }

  if (visible.includes("rainChart")) {
    const rainData = boot.zones.map(x => x.rain_probability || 0);
    upsertChart("rainChart", "line", labels, rainData, "Prob. lluvia %", "#22c55e");
  }

  if (visible.includes("landingChart")) {
    upsertChart("landingChart", "doughnut", labels.slice(0, 4),
      boot.zones.slice(0, 4).map(x => x.congestion_level), "Riesgo", "#2563eb");
  }

  chartsLoaded = true;
}

async function renderPredictionChart(hour = 18) {
  const canvas = document.getElementById("predictionChart");
  if (!canvas) return;
  const requestId = ++predictionChartRequestId;
  hideChartSpinner("predictionChart");
  try {
    const data = await MoviliAPI.predictions(hour);
    if (requestId !== predictionChartRequestId) return;
    const offset = document.getElementById("forecastOffset") ? parseInt(document.getElementById("forecastOffset").value) : 0;
    const predictions = data && data.predictions;
    if (!predictions || !predictions.length) {
      if (chartRefs["predictionChart"]) chartRefs["predictionChart"].destroy();
      delete chartRefs["predictionChart"];
      return;
    }
    const zoneLabels = predictions.map(x => x.zone);
    const values = predictions.map(p => {
      const f = p.forecast && p.forecast[offset] ? p.forecast[offset] : p.forecast && p.forecast[0] ? p.forecast[0] : null;
      return f ? f.predicted_congestion : null;
    });
    const forecastHour = (parseInt(hour) + offset) % 24;
    if (!canvas || !window.Chart) return;
    if (chartRefs["predictionChart"]) {
      const chart = chartRefs["predictionChart"];
      chart.data.labels = zoneLabels;
      chart.data.datasets[0].data = values;
      chart.data.datasets[0].label = `Hora ${forecastHour}:00`;
      chart.update({duration:800,easing:'easeOutQuart'});
      return;
    }
    chartRefs["predictionChart"] = new Chart(canvas, {
      type: "bar",
      data: {labels: zoneLabels, datasets: [{label: `Hora ${forecastHour}:00`, data: values, borderColor: "#22d3ee", backgroundColor: "#22d3ee55"}]},
      options: {
        responsive: true, maintainAspectRatio: true, animation: {duration:0},
        plugins: {legend: {labels: {color: "#dbeafe", font: {size: 11}}}},
        scales: {
          x: {ticks: {color: "#9fb2cf", font: {size: 10}, maxRotation: 45, minRotation: 30, autoSkip: false}, grid: {display: false}},
          y: {ticks: {color: "#9fb2cf", font: {size: 10}}, grid: {color: "rgba(255,255,255,.08)"}, beginAtZero: true, max: 100},
        },
      },
    });
  } catch (e) {
    console.error("Error rendering prediction chart:", e);
  }
}

window.renderPredictionChart = renderPredictionChart;

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
    chart.update({duration:800,easing:'easeOutQuart'});
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
      responsive: true, animation: {duration:0},
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

  // Accidentalidad — barras con conteo de incidentes por zona
  const zoneCoords = boot.zones.map(t => ({name: t.zone, lat: t.lat, lng: t.lng}));
  const incidentsByZone = {};
  (boot.incidents || []).forEach(inc => {
    const ilat = inc.lat, ilng = inc.lng;
    if (!ilat || !ilng) return;
    let nearest = null, minDist = Infinity;
    zoneCoords.forEach(z => {
      const d = Math.abs(ilat - z.lat) + Math.abs(ilng - z.lng);
      if (d < minDist) { minDist = d; nearest = z.name; }
    });
    if (nearest) incidentsByZone[nearest] = (incidentsByZone[nearest] || 0) + 1;
  });
  const incData = labels.map(z => incidentsByZone[z] || 0);
  upsertChart("accidentChart", "bar", labels, incData, "Incidentes", "#ef4444");

  // Riesgo por zona — linea doble con delay_risk y route_risk (varían por comuna)
  upsertMultiDatasetChart("rainChart", "line", labels, [
    {label: "⏱️ Riesgo retrasos", data: boot.zones.map(x => x.delay_risk_value || 0), color: "#f97316"},
    {label: "🛣️ Riesgo ruta", data: boot.zones.map(x => x.route_risk_value || 0), color: "#8b5cf6"},
  ]);
}

function observeLazyCharts() {
  const targets = ["accidentChart", "rainChart", "landingChart", "predictionChart", "speedChart", "incidentChart"];
  const visible = targets.filter(id => !!document.getElementById(id));
  if (!visible.length) return;
  // Mark all existing chart canvases as visible
  visible.forEach(id => { document.getElementById(id).dataset.lazyLoaded = "1"; });
  // Render immediately
  renderCoreCharts().catch(console.error);
  if (document.getElementById("predictionChart")) renderPredictionChart().catch(console.error);
  // Lazy-load via IntersectionObserver if available
  if (!("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !chartsLoaded) {
        entry.target.dataset.lazyLoaded = "1";
        observer.unobserve(entry.target);
        renderCoreCharts().catch(console.error);
      }
    });
  }, {rootMargin: "200px"});
  visible.forEach(id => observer.observe(document.getElementById(id)));
}

document.addEventListener("DOMContentLoaded", () => {
  observeLazyCharts();
  MoviliLive.register(() => renderCoreCharts().catch(console.error), MoviliLive.intervalMs);
  const range = document.getElementById("hourRange");
  MoviliLive.register(() => renderPredictionChart(range ? range.value : 18).catch(console.error), MoviliLive.intervalMs);
  if (range) {
    const updatePredictionChart = event => renderPredictionChart(event.target.value);
    range.addEventListener("input", updatePredictionChart);
    range.addEventListener("change", updatePredictionChart);
  }
  const offsetSlider = document.getElementById("forecastOffset");
  if (offsetSlider) {
    const updatePredictionChart = () => {
      const range = document.getElementById("hourRange");
      renderPredictionChart(range ? range.value : 18);
    };
    offsetSlider.addEventListener("input", updatePredictionChart);
    offsetSlider.addEventListener("change", updatePredictionChart);
  }
});
