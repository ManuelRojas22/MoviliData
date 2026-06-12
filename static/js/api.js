const MoviliAPI = {
  _cacheTTL: 4000,

  _cacheKey(url) {
    return `mc_${url}`;
  },

  _fromCache(url) {
    try {
      const raw = sessionStorage.getItem(this._cacheKey(url));
      if (!raw) return null;
      const entry = JSON.parse(raw);
      if (Date.now() - entry.ts > this._cacheTTL) {
        sessionStorage.removeItem(this._cacheKey(url));
        return null;
      }
      return entry.data;
    } catch {
      return null;
    }
  },

  _toCache(url, data) {
    try {
      sessionStorage.setItem(this._cacheKey(url), JSON.stringify({ts: Date.now(), data}));
    } catch {}
  },

  async get(url) {
    const cached = this._fromCache(url);
    if (cached) return cached;
    const separator = url.includes("?") ? "&" : "?";
    const response = await fetch(`${url}${separator}_=${Date.now()}`, {
      cache: "no-store",
      headers: {"Accept": "application/json"}
    });
    if (!response.ok) throw new Error(`API ${url} ${response.status}`);
    const data = await response.json();
    this._toCache(url, data);
    if (window.MoviliLive) window.MoviliLive.touch();
    return data;
  },

  fetchAll(...fetchers) {
    return Promise.all(fetchers.map(f => (typeof f === "function" ? f() : this.get(f))));
  },

  dashboard: () => MoviliAPI.get("/api/dashboard"),
  traffic: () => MoviliAPI.get("/api/traffic"),
  routes: () => MoviliAPI.get("/api/routes"),
  alerts: () => MoviliAPI.get("/api/alerts"),
  predictions: (hour = 18) => MoviliAPI.get(`/api/predictions?hour=${hour}`),
  maps: () => MoviliAPI.get("/api/maps"),
  bootstrap: async () => {
    if (window.__bootData) {
      const d = window.__bootData;
      window.__bootData = null;
      MoviliAPI._toCache("/api/bootstrap", d);
      return d;
    }
    return MoviliAPI.get("/api/bootstrap");
  }
};
