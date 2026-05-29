const MoviliAPI = {
  async get(url) {
    const separator = url.includes("?") ? "&" : "?";
    const response = await fetch(`${url}${separator}_=${Date.now()}`, {
      cache: "no-store",
      headers: {"Accept": "application/json"}
    });
    if (!response.ok) throw new Error(`API ${url} ${response.status}`);
    if (window.MoviliLive) window.MoviliLive.touch();
    return response.json();
  },
  dashboard: () => MoviliAPI.get("/api/dashboard"),
  traffic: () => MoviliAPI.get("/api/traffic"),
  routes: () => MoviliAPI.get("/api/routes"),
  alerts: () => MoviliAPI.get("/api/alerts"),
  predictions: (hour = 18) => MoviliAPI.get(`/api/predictions?hour=${hour}`),
  maps: () => MoviliAPI.get("/api/maps")
};
