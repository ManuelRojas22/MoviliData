document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  if (toggle && sidebar) toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/pwa/service-worker.js").catch(() => {});
});

window.MoviliLive = {
  intervalMs: 20000,
  timers: [],
  register(fn, intervalMs = 20000) {
    fn();
    const timer = window.setInterval(fn, intervalMs);
    this.timers.push(timer);
    return timer;
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
  }
};
