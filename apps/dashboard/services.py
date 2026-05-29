from datetime import datetime
import os
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


def get_tomtom_flow(lat, lng):
    if not TOMTOM_API_KEY:
        return None
    try:
        response = requests.get(
            TOMTOM_FLOW_URL,
            params={"key": TOMTOM_API_KEY, "point": f"{lat},{lng}", "unit": "KMPH"},
            timeout=2.5,
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


def _distance_score(lat_a, lng_a, lat_b, lng_b):
    if lat_b is None or lng_b is None:
        return 0
    return abs(float(lat_a) - float(lat_b)) + abs(float(lng_a) - float(lng_b))


def _external_incident_count(lat, lng, accidents):
    nearby = [item for item in accidents if _distance_score(lat, lng, item.get("lat"), item.get("lng")) < 0.035]
    return len(nearby)


def _point(name, lat, lng, i, weather=None, accidents=None, traffic_flow=None):
    weather = weather or {}
    accidents = accidents or []
    traffic_flow = traffic_flow or {}
    hour = datetime.now().hour
    peak_load = 24 if hour in [6, 7, 8, 17, 18, 19] else 8 if hour in [12, 13, 14, 15, 16, 20] else 0
    rain_mm = float(weather.get("rain", 0) or weather.get("precipitation", 0) or 0)
    rain = min(100, int(rain_mm * 18 + 10 + (i * 6) % 24))
    incident_count = _external_incident_count(lat, lng, accidents)
    baseline = 26 + (i * 7) % 34
    estimated_congestion = baseline + peak_load + rain * 0.22 + incident_count * 6
    commercial_congestion = traffic_flow.get("congestion")
    congestion = min(98, int(commercial_congestion if commercial_congestion is not None else estimated_congestion))
    risk = min(99, int(congestion * 0.50 + rain * 0.30 + min(100, incident_count * 18) * 0.20))
    speed = traffic_flow.get("current_speed")
    return {
        "id": i + 1,
        "name": name,
        "lat": lat,
        "lng": lng,
        "congestion": congestion,
        "rain_probability": rain,
        "risk": risk,
        "incidents": incident_count,
        "speed": speed or round(max(7, 48 - congestion * 0.35 - rain * 0.05), 1),
        "free_flow_speed": traffic_flow.get("free_flow_speed"),
        "flow_confidence": traffic_flow.get("confidence"),
        "road_closure": traffic_flow.get("road_closure", False),
        "source": traffic_flow.get("source", "Open-Meteo + Medellin ArcGIS + estimacion local"),
    }


def live_points(weather=None, accidents=None):
    weather = weather or get_weather()
    accidents = accidents if accidents is not None else get_external_accidents()
    points = []
    for i, item in enumerate(NEIGHBORHOODS):
        _, lat, lng = item
        points.append(_point(*item, i, weather=weather, accidents=accidents, traffic_flow=get_tomtom_flow(lat, lng)))
    return points


def demo_points():
    return live_points()


def get_external_accidents(limit=20):
    params = {
        "f": "json",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "resultRecordCount": limit,
    }
    try:
        response = requests.get(ARCGIS_ACCIDENTS_URL, params=params, timeout=6)
        response.raise_for_status()
        features = response.json().get("features", [])
        accidents = []
        for feature in features:
            attrs = feature.get("attributes", {})
            lat = attrs.get("latitud") or feature.get("geometry", {}).get("y")
            lng = attrs.get("longitud") or feature.get("geometry", {}).get("x")
            accidents.append({
                "source": "Alcaldia de Medellin ArcGIS",
                "lat": lat,
                "lng": lng,
                "attributes": attrs,
            })
        return accidents
    except requests.RequestException:
        return []


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
            "cache_ttl_seconds": 0,
        },
        "zones": points,
    }


def route_options():
    return [
        {"name": "Ruta Rio Medellin", "time": 22, "risk": 34, "distance": 8.6, "points": [[6.2088, -75.5678], [6.2311, -75.575], [6.2518, -75.5636]]},
        {"name": "Ruta Laureles segura", "time": 28, "risk": 22, "distance": 9.8, "points": [[6.2459, -75.5964], [6.239, -75.587], [6.2311, -75.6038]]},
        {"name": "Ruta Nororiental preventiva", "time": 35, "risk": 48, "distance": 11.2, "points": [[6.2746, -75.5523], [6.262, -75.56], [6.2518, -75.5636]]},
    ]
