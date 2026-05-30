import heapq
import json
import urllib.request
from apps.dashboard.services import demo_points, NEIGHBORHOODS


def _get_osrm_route(waypoints):
    coords = ";".join(f"{lng},{lat}" for lat, lng in waypoints)
    url = f"https://router.project-osrm.org/route/v1/driving/{coords}?geometries=geojson&overview=full&steps=false"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MoviliData/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        if data.get("code") == "Ok" and data["routes"]:
            route = data["routes"][0]
            coords = route["geometry"]["coordinates"]
            polyline = [[round(c[1], 6), round(c[0], 6)] for c in coords]
            dist_km = round(route["distance"] / 1000, 1)
            time_min = max(1, round(route["duration"] / 60))
            return polyline, dist_km, time_min
    except Exception:
        pass
    return None


def _haversine_km(lat1, lng1, lat2, lng2):
    import math
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _build_all_edges(zones):
    zone_map = {z["name"]: z for z in zones}
    edges = {}
    names = list(zone_map.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            za, zb = zone_map[a], zone_map[b]
            lat_a = za.get("lat", 6.2)
            lng_a = za.get("lng", -75.58)
            lat_b = zb.get("lat", 6.2)
            lng_b = zb.get("lng", -75.58)
            dist = _haversine_km(lat_a, lng_a, lat_b, lng_b)
            risk_avg = (za.get("risk", 50) + zb.get("risk", 50)) / 2
            cong_avg = (za.get("congestion", 50) + zb.get("congestion", 50)) / 2
            rain_avg = (za.get("rain_probability", 30) + zb.get("rain_probability", 30)) / 2
            dist_norm = (dist / 15) * 100
            weight = risk_avg * 0.35 + dist_norm * 0.35 + cong_avg * 0.20 + rain_avg * 0.10
            edges[(a, b)] = round(weight, 2)
    return edges


def _build_graph(zones):
    zone_map = {z["name"]: z for z in zones}
    graph = {name: {} for name in zone_map}
    all_edges = _build_all_edges(zones)
    for (a, b), weight in all_edges.items():
        if a in zone_map and b in zone_map:
            graph[a][b] = weight
            graph[b][a] = weight
    return graph, zone_map


def _dijkstra(graph, start, end):
    distances = {node: float("inf") for node in graph}
    distances[start] = 0
    prev = {node: None for node in graph}
    pq = [(0, start)]
    while pq:
        d, node = heapq.heappop(pq)
        if node == end:
            path = []
            while node:
                path.append(node)
                node = prev[node]
            return list(reversed(path)), distances[end]
        if d > distances[node]:
            continue
        for neighbor, weight in graph[node].items():
            nd = d + weight
            if nd < distances[neighbor]:
                distances[neighbor] = nd
                prev[neighbor] = node
                heapq.heappush(pq, (nd, neighbor))
    return [], float("inf")


def _nearest_zone(zone_map, name):
    if name in zone_map:
        return name
    lower = name.lower().strip()
    for zname in zone_map:
        if zname.lower() == lower:
            return zname
    for zname in zone_map:
        if lower in zname.lower() or zname.lower() in lower:
            return zname
    return next(iter(zone_map))


def recommended_routes(origin=None, destination=None):
    points = demo_points()
    zones = [{
        "name": p["name"],
        "lat": p["lat"],
        "lng": p["lng"],
        "congestion": p["congestion"],
        "rain_probability": p["rain_probability"],
        "risk": p["risk"],
        "speed": p["speed"],
    } for p in points]

    zone_map = {z["name"]: z for z in zones}

    if origin and destination:
        src = _nearest_zone(zone_map, origin)
        dst = _nearest_zone(zone_map, destination)
        if src and dst and src != dst:
            graph, _ = _build_graph(zones)
            path, total_risk = _dijkstra(graph, src, dst)
            if path:
                return [_build_route_result(path, total_risk, zone_map, use_osrm=True)]

    combos = []
    names = [z["name"] for z in zones]
    for i, src in enumerate(names):
        for dst in names[i + 1:]:
            graph, _ = _build_graph(zones)
            path, risk = _dijkstra(graph, src, dst)
            if path:
                combos.append((risk, path))
    combos.sort(key=lambda x: x[0])
    results = []
    seen = set()
    for risk, path in combos[:5]:
        key = tuple(path)
        if key not in seen:
            seen.add(key)
            results.append(_build_route_result(path, risk, zone_map, use_osrm=False))
    return sorted(results, key=lambda r: r["risk"])[:3]


def _build_route_result(path, risk, zone_map, use_osrm=True):
    name = f"Ruta {' → '.join(path)}"
    path_len = len(path)
    if use_osrm:
        waypoints = [[zone_map[z]["lat"], zone_map[z]["lng"]] for z in path if z in zone_map]
        if len(waypoints) >= 2:
            result = _get_osrm_route(waypoints)
            if result:
                polyline, dist_km, time_min = result
                return {
                    "name": name,
                    "origin": path[0],
                    "destination": path[-1],
                    "distance": dist_km,
                    "time": time_min,
                    "risk": min(99, round(risk / max(path_len, 1))),
                    "points": polyline,
                }
    total_dist = 0
    total_time = 0
    polyline = []
    for i, z in enumerate(path):
        zdata = zone_map.get(z, {})
        polyline.append([zdata.get("lat", 6.2), zdata.get("lng", -75.58)])
        if i > 0:
            prev = zone_map.get(path[i - 1], {})
            dist = _haversine_km(
                float(prev.get("lat", 0)), float(prev.get("lng", 0)),
                float(zdata.get("lat", 0)), float(zdata.get("lng", 0)),
            )
            total_dist += dist
            avg_speed = (float(prev.get("speed", 25)) + float(zdata.get("speed", 25))) / 2
            total_time += (dist / max(avg_speed, 1)) * 60
    return {
        "name": name,
        "origin": path[0],
        "destination": path[-1],
        "distance": round(total_dist, 1),
        "time": max(1, round(total_time)),
        "risk": min(99, round(risk / max(path_len, 1))),
        "points": polyline,
    }
