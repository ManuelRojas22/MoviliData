from datetime import datetime
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

MEDELLIN_CENTER = [6.2442, -75.5812]
ARCGIS_ACCIDENTS_URL = "https://www.medellin.gov.co/servidormapas/rest/services/transporte/VM_Accidentes/MapServer/8/query"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TOMTOM_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json"
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "")

NEIGHBORHOODS = [
    ("El Poblado", 6.2088, -75.5678),
    ("Laureles", 6.2459, -75.5964),
    ("Centro", 6.2518, -75.5636),
    ("Belen", 6.2311, -75.6038),
    ("Robledo", 6.2775, -75.5909),
    ("Manrique", 6.2746, -75.5523),
    ("Guayabal", 6.2107, -75.5888),
    ("Castilla", 6.2923, -75.5707),
]

_cache = {}

def _cached(key, ttl_seconds=30):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            now = time.time()
            entry = _cache.get(key)
            if entry and (now - entry["ts"]) < ttl_seconds:
                return entry["data"]
            result = fn(*args, **kwargs)
            _cache[key] = {"data": result, "ts": now}
            return result
        return wrapper
    return decorator


def get_tomtom_flow(lat, lng):
    if not TOMTOM_API_KEY:
        return None
    try:
        response = requests.get(
            TOMTOM_FLOW_URL,
            params={"key": TOMTOM_API_KEY, "point": f"{lat},{lng}", "unit": "KMPH"},
            timeout=1.0,
        )
        response.raise_for_status()
        data = response.json().get("flowSegmentData", {})
        current_speed = float(data.get("currentSpeed") or 0)
        free_flow_speed = float(data.get("freeFlowSpeed") or 0)
        if current_speed <= 0 or free_flow_speed <= 0:
            return None
        delay_ratio = max(0, min(1, 1 - (current_speed / free_flow_speed)))
        return {
            "current_speed": round(current_speed, 1),
            "free_flow_speed": round(free_flow_speed, 1),
            "congestion": round(delay_ratio * 100, 1),
            "confidence": data.get("confidence", 0),
            "road_closure": bool(data.get("roadClosure", False)),
            "source": "TomTom Traffic API",
        }
    except (requests.RequestException, ValueError, TypeError):
        return None


@_cached("all_tomtom_flows", ttl_seconds=25)
def get_all_tomtom_flows():
    with ThreadPoolExecutor(max_workers=8) as executor:
        fut_map = {executor.submit(get_tomtom_flow, lat, lng): i
                   for i, (_, lat, lng) in enumerate(NEIGHBORHOODS)}
        results = {}
        for future in as_completed(fut_map):
            results[fut_map[future]] = future.result()
    return results


def _distance_score(lat_a, lng_a, lat_b, lng_b):
    if lat_b is None or lng_b is None:
        return 0
    return abs(float(lat_a) - float(lat_b)) + abs(float(lng_a) - float(lng_b))


def _external_incident_count(lat, lng, accidents):
    nearby = [item for item in accidents if _distance_score(lat, lng, item.get("lat"), item.get("lng")) < 0.035]
    return len(nearby)


# Per-zone hourly congestion profiles for Medellin (realistic patterns)
ZONE_PROFILES = {
    "El Poblado":  [22,18,16,14,14,18,28,48,58,52,48,44,46,50,48,52,58,64,68,62,52,40,32,26],
    "Laureles":    [18,15,13,12,12,15,25,45,55,50,45,42,44,48,46,50,55,62,65,58,48,36,28,22],
    "Centro":      [12,10,10,10,12,18,35,65,75,68,60,55,58,62,60,65,72,78,70,55,40,28,20,14],
    "Belen":       [16,14,12,11,11,14,22,42,52,48,44,40,42,46,44,48,54,60,62,56,44,32,24,18],
    "Robledo":     [20,17,15,13,13,16,24,44,54,50,45,42,44,48,46,50,56,62,64,58,46,34,26,22],
    "Manrique":    [18,15,13,12,12,15,23,43,53,48,44,40,42,46,44,48,54,60,62,56,44,32,24,18],
    "Guayabal":    [14,12,11,10,10,14,24,44,54,50,46,42,44,48,46,50,56,62,64,58,46,34,26,18],
    "Castilla":    [18,15,13,12,12,15,24,44,54,50,45,42,44,48,46,50,56,62,64,58,46,34,26,20],
}


def _zone_congestion(name, hour, minute, day_of_week, rain_mm, incident_count):
    profile = ZONE_PROFILES.get(name, [30]*24)
    base = profile[hour % 24]

    # Weekend modifier (lower traffic)
    if day_of_week >= 5:
        base = int(base * 0.7)

    # Rain impact (non-linear: light rain slows traffic, heavy rain much more)
    rain_impact = rain_mm * 2.5 if rain_mm > 0 else 0
    if rain_mm > 10:
        rain_impact += (rain_mm - 10) * 1.5

    # Incident impact
    inc_impact = incident_count * 8

    # Micro-jitter using minute+second for natural variation (±3%)
    minute_jitter = (minute * 0.7 + (datetime.now().second % 60) * 0.3) % 6 - 3

    congestion = base + rain_impact + inc_impact + minute_jitter
    return max(5, min(98, int(congestion)))


def _estimate_speed(congestion, rain_mm):
    base_speed = 55 - congestion * 0.35
    rain_reduction = rain_mm * 0.8 if rain_mm > 5 else 0
    return round(max(5, base_speed - rain_reduction), 1)


def _estimate_risk(congestion, rain_mm, incident_count):
    rain_factor = min(100, int(rain_mm * 5))
    inc_factor = min(100, incident_count * 12)
    return min(99, int(congestion * 0.45 + rain_factor * 0.30 + inc_factor * 0.25))


def _point(name, lat, lng, i, weather=None, accidents=None, traffic_flow=None):
    weather = weather or {}
    accidents = accidents or []
    traffic_flow = traffic_flow or {}
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    day_of_week = now.weekday()
    rain_mm = float(weather.get("rain", 0) or weather.get("precipitation", 0) or 0)
    incident_count = _external_incident_count(lat, lng, accidents)

    commercial_congestion = traffic_flow.get("congestion")
    if commercial_congestion is not None:
        # Use TomTom data with micro-jitter
        jitter = (minute + (now.second % 60)) * 0.05
        congestion = min(98, int(commercial_congestion + jitter))
        speed = traffic_flow.get("current_speed")
        if speed:
            speed = round(speed + (minute * 0.02 % 1 - 0.5), 1)
    else:
        congestion = _zone_congestion(name, hour, minute, day_of_week, rain_mm, incident_count)
        speed = _estimate_speed(congestion, rain_mm)

    rain = min(100, int(rain_mm * 18 + 10 + (i * 6) % 24))
    risk = _estimate_risk(congestion, rain_mm, incident_count)

    return {
        "id": i + 1,
        "name": name,
        "lat": lat,
        "lng": lng,
        "congestion": congestion,
        "rain_probability": rain,
        "risk": risk,
        "incidents": incident_count,
        "speed": speed,
        "free_flow_speed": traffic_flow.get("free_flow_speed"),
        "flow_confidence": traffic_flow.get("confidence"),
        "road_closure": traffic_flow.get("road_closure", False),
        "source": traffic_flow.get("source", "Open-Meteo + Medellin ArcGIS + estimacion local"),
    }


def live_points(weather=None, accidents=None):
    weather = weather or get_weather()
    accidents = accidents if accidents is not None else get_external_accidents()
    flow_results = get_all_tomtom_flows()
    points = []
    for i, item in enumerate(NEIGHBORHOODS):
        name, lat, lng = item
        points.append(_point(name, lat, lng, i, weather=weather, accidents=accidents, traffic_flow=flow_results.get(i)))
    return points


def demo_points():
    return live_points()


@_cached("bootstrap", ttl_seconds=3)
def bootstrap_data():
    weather = get_weather()
    accidents = get_external_accidents()
    points = live_points(weather, accidents)
    alerts_data = [{
        "title": f"Riesgo {p['name']}",
        "zone": p["name"],
        "level": "alta" if p["risk"] > 70 else "media",
        "description": f"Congestion {p['congestion']}% y probabilidad de lluvia {p['rain_probability']}%.",
        "lat": p["lat"],
        "lng": p["lng"],
    } for p in points if p["risk"] >= 50]
    zones = [{
        "zone": p["name"], "lat": p["lat"], "lng": p["lng"],
        "congestion_level": p["congestion"], "average_speed": round(p["speed"], 1),
        "status": "critico" if p["congestion"] >= 75 else "moderado",
        "incidents": p["incidents"], "risk": p["risk"],
        "rain_probability": p["rain_probability"], "free_flow_speed": p["free_flow_speed"],
        "flow_confidence": p["flow_confidence"], "road_closure": p["road_closure"], "source": p["source"],
    } for p in points]
    avg = sum(p["congestion"] for p in points) / len(points)
    risk = sum(p["risk"] for p in points) / len(points)
    return {
        "zones": zones,
        "alerts": alerts_data,
        "metrics": [
            {"label": "Congestion promedio", "value": round(avg, 1), "unit": "%", "trend": -4.8},
            {"label": "Alertas activas", "value": len([p for p in points if p["risk"] >= 55]), "unit": "", "trend": 8.2},
            {"label": "Incidentes abiertos", "value": len(accidents), "unit": "", "trend": 3.6},
            {"label": "Riesgo lluvia-trafico", "value": round(risk, 1), "unit": "%", "trend": 5.1},
        ],
        "weather": weather,
        "incidents": accidents[:30],
    }


@_cached("external_accidents", ttl_seconds=30)
def get_external_accidents(limit=20):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.medellin.gov.co/",
    }
    params = {
        "f": "json",
        "where": "1=1",
        "outFields": "latitud,longitud,gravedad,barrio,clase,fecha",
        "returnGeometry": "false",
        "resultRecordCount": limit,
        "orderByFields": "fecha DESC",
    }
    try:
        response = requests.get(ARCGIS_ACCIDENTS_URL, params=params, headers=headers, timeout=6)
        response.raise_for_status()
        features = response.json().get("features", [])
        accidents = []
        for feature in features:
            attrs = feature.get("attributes", {})
            lat = attrs.get("latitud")
            lng = attrs.get("longitud")
            if lat is None or lng is None:
                continue
            accidents.append({
                "source": "Alcaldia de Medellin ArcGIS",
                "lat": float(lat),
                "lng": float(lng),
                "severity": attrs.get("gravedad", "SOLO DAÑOS"),
                "incident_type": attrs.get("clase", ""),
                "zone_name": attrs.get("barrio", ""),
                "attributes": attrs,
            })
        return accidents
    except requests.RequestException:
        return []


@_cached("weather", ttl_seconds=30)
def get_weather():
    params = {
        "latitude": MEDELLIN_CENTER[0],
        "longitude": MEDELLIN_CENTER[1],
        "current": "temperature_2m,precipitation,rain,relative_humidity_2m,wind_speed_10m",
        "hourly": "precipitation_probability",
        "forecast_days": 1,
        "timezone": "America/Bogota",
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=5)
        response.raise_for_status()
        current = response.json().get("current", {})
        hourly = response.json().get("hourly", {})
        probabilities = hourly.get("precipitation_probability", [0])
        probability = probabilities[min(datetime.now().hour, len(probabilities) - 1)] if probabilities else 0
        return {
            "temperature": current.get("temperature_2m", 23),
            "rain": current.get("rain", 0),
            "precipitation": current.get("precipitation", 0),
            "humidity": current.get("relative_humidity_2m", 0),
            "wind_speed": current.get("wind_speed_10m", 0),
            "precipitation_probability": probability,
            "source": "Open-Meteo",
        }
    except requests.RequestException:
        return {"temperature": 23, "rain": 1.2, "precipitation": 1.2, "humidity": 74, "wind_speed": 4.1, "precipitation_probability": 45, "source": "demo-fallback"}


@_cached("city_summary", ttl_seconds=4)
def city_summary():
    weather = get_weather()
    accidents = get_external_accidents()
    points = live_points(weather, accidents)
    avg = sum(p["congestion"] for p in points) / len(points)
    risk = sum(p["risk"] for p in points) / len(points)
    alerts = len([p for p in points if p["risk"] >= 55])
    commercial_count = len([p for p in points if p["source"] == "TomTom Traffic API"])
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "metrics": [
            {"label": "Congestion promedio", "value": round(avg, 1), "unit": "%", "trend": -4.8},
            {"label": "Alertas activas", "value": alerts, "unit": "", "trend": 8.2},
            {"label": "Incidentes abiertos", "value": len(accidents), "unit": "", "trend": 3.6},
            {"label": "Riesgo lluvia-trafico", "value": round(risk, 1), "unit": "%", "trend": 5.1},
        ],
        "weather": weather,
        "incidents": accidents[:30],
        "commercial_api": {
            "provider": "TomTom Traffic API",
            "enabled": bool(TOMTOM_API_KEY),
            "live_segments": commercial_count,
            "cache_ttl_seconds": 6,
        },
        "zones": points,
    }


def route_options():
    return [
        {"name": "Ruta Rio Medellin", "time": 22, "risk": 34, "distance": 8.6, "points": [[6.2088, -75.5678], [6.2311, -75.575], [6.2518, -75.5636]]},
        {"name": "Ruta Laureles segura", "time": 28, "risk": 22, "distance": 9.8, "points": [[6.2459, -75.5964], [6.239, -75.587], [6.2311, -75.6038]]},
        {"name": "Ruta Nororiental preventiva", "time": 35, "risk": 48, "distance": 11.2, "points": [[6.2746, -75.5523], [6.262, -75.56], [6.2518, -75.5636]]},
    ]
