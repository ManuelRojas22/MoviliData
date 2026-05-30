document.addEventListener("DOMContentLoaded", () => {
  MoviliLive.initRefresh();
  const toggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  if (toggle && sidebar) toggle.addEventListener("click", () => sidebar.classList.toggle("open"));

  if ("serviceWorker" in navigator) {
    const registerSW = () => navigator.serviceWorker.register("/pwa/service-worker.js").catch(() => {});
    if (document.readyState === "complete") registerSW();
    else window.addEventListener("load", registerSW);
  }

  // Prefetch cache: API data stored between page navigations
  window.__prefetchCache = window.__prefetchCache || {};

  // Map sidebar/navbar href paths to their API endpoints
  const API_MAP = {
    "/dashboard/": "/api/bootstrap",
    "/traffic/": "/api/bootstrap",
    "/routes/": "/api/routes",
    "/predictions/": "/api/predictions",
    "/alerts/": "/api/bootstrap",
    "/risk-zones/": "/api/maps",
    "/statistics/": "/api/bootstrap",
  };

  // Hover-based API data prefetch for sidebar + navbar links
  document.querySelectorAll(".sidebar a[href], .topbar a[href]").forEach(link => {
    let timer;
    let path;
    try { path = new URL(link.href, location.origin).pathname; } catch(e) { return; }
    const apiUrl = API_MAP[path];
    if (!apiUrl) return;

    const prefetchAPI = () => {
      const cached = window.__prefetchCache[apiUrl];
      if (cached && Date.now() - cached.ts < 10000) return;
      fetch(apiUrl + "?_=" + Date.now(), { headers: { Accept: "application/json" } })
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (data) window.__prefetchCache[apiUrl] = { data, ts: Date.now() }; })
        .catch(() => {});
    };

    link.addEventListener("mouseenter", () => { timer = setTimeout(prefetchAPI, 80); });
    link.addEventListener("mouseleave", () => clearTimeout(timer));
    link.addEventListener("touchstart", prefetchAPI, { once: true });
  });

  // Keep existing HTML page prefetch for non-sidebar/navbar links
  document.querySelectorAll("a[href]:not(.sidebar a):not(.topbar a)").forEach(link => {
    let timer;
    const prefetch = () => {
      const href = link.href;
      if (!href || href.startsWith("javascript") || href.startsWith("#")) return;
      const el = document.createElement("link");
      el.rel = "prefetch";
      el.href = href;
      el.as = "document";
      document.head.appendChild(el);
    };
    link.addEventListener("mouseenter", () => { timer = setTimeout(prefetch, 80); });
    link.addEventListener("mouseleave", () => clearTimeout(timer));
    link.addEventListener("touchstart", prefetch, { once: true });
  });
});

window.MoviliLive = {
  intervalMs: 5000,
  timers: [],
  _fns: [],
  register(fn, intervalMs = 20000) {
    this._fns.push(fn);
    if (document.visibilityState === "visible") fn();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") fn();
    }, intervalMs);
    this.timers.push(timer);
    return timer;
  },
  refreshAll() {
    this._fns.forEach(fn => fn());
  },
  touch() {
    const status = document.getElementById("liveStatus");
    if (!status) return;
    status.textContent = `Actualizado ${new Date().toLocaleTimeString("es-CO", {hour: "2-digit", minute: "2-digit", second: "2-digit"})}`;
    status.classList.remove("live-flash");
    void status.offsetWidth;
    status.classList.add("live-flash");
  },
  flash(element) {
    if (!element) return;
    element.classList.remove("live-flash");
    void element.offsetWidth;
    element.classList.add("live-flash");
  },
  setHTML(element, html) {
    if (!element || element.dataset.lastHtml === html) return;
    element.dataset.lastHtml = html;
    element.innerHTML = html;
    this.flash(element);
  },
  initRefresh() {
    document.addEventListener("click", e => {
      const btn = e.target.closest("[data-refresh]");
      if (btn) { this.refreshAll(); if (window.Swal) this.toast("Actualizando datos...", "info", 1500); }
    });
  },
  toast(message, icon = "success", duration = 4000) {
    if (!window.Swal) return;
    Swal.fire({ toast: true, position: "top-end", icon, title: message, showConfirmButton: false, timer: duration, timerProgressBar: true, background: "#101b2c", color: "#f4f7fb", iconColor: icon === "success" ? "#28d17c" : icon === "error" ? "#f15d5d" : "#f5b84b" });
  },
  showSpinner(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.classList.add("skeleton-container");
  },
  hideSpinner(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.classList.remove("skeleton-container");
  }
};