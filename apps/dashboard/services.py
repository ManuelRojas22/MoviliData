import logging
from datetime import datetime, timedelta
from django.utils import timezone
import os

from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from django.core.cache import cache
from django.db import models

logger = logging.getLogger(__name__)
MEDELLIN_CENTER = [6.2442, -75.5812]
MEDELLIN_BBOX = "-75.6500,6.1700,-75.5100,6.3500"
TOMTOM_INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"
TOMTOM_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _get_api_key():
    return os.getenv("TOMTOM_API_KEY", "")

COMUNAS_COORDS = {
    "Popular":        (6.3050, -75.5550),
    "Santa Cruz":     (6.2960, -75.5600),
    "Manrique":       (6.2746, -75.5523),
    "Aranjuez":       (6.2860, -75.5650),
    "Castilla":       (6.2923, -75.5707),
    "Doce de Octubre":(6.2980, -75.5880),
    "Robledo":        (6.2775, -75.5909),
    "Villa Hermosa":  (6.2620, -75.5530),
    "Buenos Aires":   (6.2530, -75.5570),
    "Centro":         (6.2518, -75.5636),
    "Laureles":       (6.2459, -75.5964),
    "La América":     (6.2420, -75.5880),
    "San Javier":     (6.2355, -75.6050),
    "El Poblado":     (6.2088, -75.5678),
    "Guayabal":       (6.2107, -75.5888),
    "Belen":          (6.2311, -75.6038),
}

COMUNAS_PRINCIPALES = list(COMUNAS_COORDS.keys())
COMUNA_NUMEROS = {
    "Popular": "1",
    "Santa Cruz": "2",
    "Manrique": "3",
    "Aranjuez": "4",
    "Castilla": "5",
    "Doce de Octubre": "6",
    "Robledo": "7",
    "Villa Hermosa": "8",
    "Buenos Aires": "9",
    "Centro": "10",
    "Laureles": "11",
    "La América": "12",
    "San Javier": "13",
    "El Poblado": "14",
    "Guayabal": "15",
    "Belen": "16",
}
COMUNA_NOMBRES_COMPLETOS = {
    "Popular": "Comuna 1 — Popular",
    "Santa Cruz": "Comuna 2 — Santa Cruz",
    "Manrique": "Comuna 3 — Manrique",
    "Aranjuez": "Comuna 4 — Aranjuez",
    "Castilla": "Comuna 5 — Castilla",
    "Doce de Octubre": "Comuna 6 — Doce de Octubre",
    "Robledo": "Comuna 7 — Robledo",
    "Villa Hermosa": "Comuna 8 — Villa Hermosa",
    "Buenos Aires": "Comuna 9 — Buenos Aires",
    "Centro": "Comuna 10 — La Candelaria",
    "Laureles": "Comuna 11 — Laureles-Estadio",
    "La América": "Comuna 12 — La América",
    "San Javier": "Comuna 13 — San Javier",
    "El Poblado": "Comuna 14 — El Poblado",
    "Guayabal": "Comuna 15 — Guayabal",
    "Belen": "Comuna 16 — Belén",
}

NEIGHBORHOODS = [
    {"name": "Popular", "lat": 6.3085, "lng": -75.5579, "group": "Comuna 1 — Popular"},
    {"name": "Granizal", "lat": 6.3012, "lng": -75.5501, "group": "Comuna 1 — Popular"},
    {"name": "Santa Cruz", "lat": 6.2985, "lng": -75.5612, "group": "Comuna 2 — Santa Cruz"},
    {"name": "Villa del Socorro", "lat": 6.2930, "lng": -75.5534, "group": "Comuna 2 — Santa Cruz"},
    {"name": "Manrique", "lat": 6.2746, "lng": -75.5523, "group": "Comuna 3 — Manrique"},
    {"name": "La Cruz", "lat": 6.2810, "lng": -75.5467, "group": "Comuna 3 — Manrique"},
    {"name": "Aranjuez", "lat": 6.2860, "lng": -75.5650, "group": "Comuna 4 — Aranjuez"},
    {"name": "Brasilia", "lat": 6.2795, "lng": -75.5712, "group": "Comuna 4 — Aranjuez"},
    {"name": "Castilla", "lat": 6.2923, "lng": -75.5707, "group": "Comuna 5 — Castilla"},
    {"name": "Florencia", "lat": 6.2975, "lng": -75.5780, "group": "Comuna 5 — Castilla"},
    {"name": "Doce de Octubre", "lat": 6.2980, "lng": -75.5880, "group": "Comuna 6 — Doce de Octubre"},
    {"name": "Pedregal", "lat": 6.2912, "lng": -75.5850, "group": "Comuna 6 — Doce de Octubre"},
    {"name": "Robledo", "lat": 6.2775, "lng": -75.5909, "group": "Comuna 7 — Robledo"},
    {"name": "Pajarito", "lat": 6.2840, "lng": -75.6012, "group": "Comuna 7 — Robledo"},
    {"name": "Villa Hermosa", "lat": 6.2620, "lng": -75.5530, "group": "Comuna 8 — Villa Hermosa"},
    {"name": "La Ladera", "lat": 6.2570, "lng": -75.5490, "group": "Comuna 8 — Villa Hermosa"},
    {"name": "Buenos Aires", "lat": 6.2530, "lng": -75.5570, "group": "Comuna 9 — Buenos Aires"},
    {"name": "Miraflores", "lat": 6.2490, "lng": -75.5610, "group": "Comuna 9 — Buenos Aires"},
    {"name": "Centro", "lat": 6.2518, "lng": -75.5636, "group": "Comuna 10 — La Candelaria"},
    {"name": "Prado", "lat": 6.2560, "lng": -75.5680, "group": "Comuna 10 — La Candelaria"},
    {"name": "Laureles", "lat": 6.2459, "lng": -75.5964, "group": "Comuna 11 — Laureles-Estadio"},
    {"name": "Estadio", "lat": 6.2510, "lng": -75.5880, "group": "Comuna 11 — Laureles-Estadio"},
    {"name": "La América", "lat": 6.2420, "lng": -75.5880, "group": "Comuna 12 — La América"},
    {"name": "Calasanz", "lat": 6.2380, "lng": -75.5950, "group": "Comuna 12 — La América"},
    {"name": "San Javier", "lat": 6.2355, "lng": -75.6050, "group": "Comuna 13 — San Javier"},
    {"name": "El Salado", "lat": 6.2290, "lng": -75.6120, "group": "Comuna 13 — San Javier"},
    {"name": "El Poblado", "lat": 6.2088, "lng": -75.5678, "group": "Comuna 14 — El Poblado"},
    {"name": "Astorga", "lat": 6.2020, "lng": -75.5750, "group": "Comuna 14 — El Poblado"},
    {"name": "Guayabal", "lat": 6.2107, "lng": -75.5888, "group": "Comuna 15 — Guayabal"},
    {"name": "Tenche", "lat": 6.2050, "lng": -75.5830, "group": "Comuna 15 — Guayabal"},
    {"name": "Belen", "lat": 6.2311, "lng": -75.6038, "group": "Comuna 16 — Belén"},
    {"name": "Los Alpes", "lat": 6.2250, "lng": -75.6100, "group": "Comuna 16 — Belén"},
]

NEIGHBORHOODS_FLAT = [(n["name"], n["lat"], n["lng"], n["group"]) for n in NEIGHBORHOODS]


def _nearest_comuna(lat, lng, threshold=0.035):
    closest = min(COMUNAS_COORDS.items(), key=lambda item: abs(lat - item[1][0]) + abs(lng - item[1][1]))
    name, (clat, clng) = closest
    if abs(lat - clat) + abs(lng - clng) < threshold:
        return name
    return None


def _nearest_neighborhood(lat, lng, threshold=0.035):
    closest = min(NEIGHBORHOODS_FLAT, key=lambda n: abs(lat - n[1]) + abs(lng - n[2]))
    name, clat, clng, group = closest
    if abs(lat - clat) + abs(lng - clng) < threshold:
        return name, group
    return None, None


def get_tomtom_flow_data(lat, lng):
    api_key = _get_api_key()
    if not api_key:
        return None
    cache_key = f"tomtom_flow_{lat}_{lng}"
    cached = cache.get(cache_key)
    if cached:
        if cached.get("no_data"):
            return None
        return cached
    try:
        response = requests.get(
            TOMTOM_FLOW_URL,
            params={"key": api_key, "point": f"{lat},{lng}", "unit": "KMPH", "openLr": "false", "thickness": "1"},
            timeout=3.0,
        )
        response.raise_for_status()
        data = response.json()
        seg = data.get("flowSegmentData")
        if not seg:
            return None
        current_speed = float(seg.get("currentSpeed", 0))
        free_flow_speed = float(seg.get("freeFlowSpeed", 0))
        confidence = float(seg.get("confidence", 0))
        if current_speed <= 0 or free_flow_speed <= 0:
            return None
        congestion = round(max(0, min(100, (1 - current_speed / free_flow_speed) * 100)), 1)
        result = {
            "current_speed": round(current_speed, 1),
            "free_flow_speed": round(free_flow_speed, 1),
            "congestion": congestion,
            "confidence": confidence,
            "road_closure": congestion >= 90,
            "source": "TomTom Traffic API",
        }
        cache.set(cache_key, result, 360)
        return result
    except requests.RequestException as e:
        is_permanent = False
        try:
            body = e.response.json() if hasattr(e, 'response') and e.response else {}
            code = body.get("detailedError", {}).get("code", "")
            if code in ("InsufficientFunds", "Forbidden", "InvalidKey", "Unauthorized"):
                is_permanent = True
                logger.error("[flow] Error permanente '%s' en %s,%s — pausando 10 min", code, lat, lng)
        except Exception:
            pass
        if is_permanent:
            cache.set(cache_key, {"no_data": True}, 600)
        return None
    except (ValueError, TypeError):
        return None


def get_all_tomtom_flows():
    cached = cache.get("all_tomtom_flows")
    if cached:
        return cached
    with ThreadPoolExecutor(max_workers=8) as executor:
        fut_map = {executor.submit(get_tomtom_flow_data, lat, lng): i
                   for i, (name, (lat, lng)) in enumerate(COMUNAS_COORDS.items())}
        results = {}
        for future in as_completed(fut_map):
            results[fut_map[future]] = future.result()
    cache.set("all_tomtom_flows", results, 360)
    return results


def _distance_score(lat_a, lng_a, lat_b, lng_b):
    if lat_b is None or lng_b is None:
        return 0
    return abs(float(lat_a) - float(lat_b)) + abs(float(lng_a) - float(lng_b))


def _external_incident_count(lat, lng, accidents):
    nearby = [item for item in accidents if _distance_score(lat, lng, item.get("lat"), item.get("lng")) < 0.035]
    return len(nearby)


def _external_fatal_count(lat, lng, accidents):
    return 0


def calculate_risk(congestion, rain_probability, incidents_normalized):
    risk = congestion * 0.45 + rain_probability * 0.30 + incidents_normalized * 0.25
    return min(round(risk), 100)


def _point(name, lat, lng, i, weather=None, accidents=None, traffic_flow=None):
    weather = weather or {}
    accidents = accidents or []
    traffic_flow = traffic_flow or {}
    now = datetime.now()
    minute = now.minute
    rain_mm = float(weather.get("rain", 0) or weather.get("precipitation", 0) or 0)
    incident_count = _external_incident_count(lat, lng, accidents)

    commercial_congestion = traffic_flow.get("congestion")
    if commercial_congestion is not None:
        congestion = int(commercial_congestion)
        speed = traffic_flow.get("current_speed")
        if speed:
            speed = round(speed, 1)
        source = traffic_flow.get("source", "TomTom Traffic API")
    else:
        from apps.traffic.models import TrafficRecord
        last = TrafficRecord.objects.filter(zone=name, source="TomTom Traffic API").order_by("-recorded_at").first()
        if last and last.congestion_level and last.average_speed:
            congestion = int(last.congestion_level)
            speed = float(last.average_speed)
            source = "Histórico TomTom"
        else:
            hour = datetime.now().hour
            is_peak = (7 <= hour <= 9) or (17 <= hour <= 20)
            is_off_peak = hour < 6 or hour > 21
            base = 20 if is_off_peak else 45 if is_peak else 30
            rain_prob = int(weather.get("precipitation_probability", 30) or 30)
            congestion = min(95, base + incident_count * 5 + (10 if rain_prob > 50 else 0))
            speed = round(max(10, 55 - congestion * 0.35), 1)
            source = "Estimación local"

    rain = int(weather.get("precipitation_probability", 30) or 30)

    if congestion is not None and speed is not None:
        risk = calculate_risk(congestion, rain, min(incident_count * 10, 100))
    else:
        risk = None

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
        "source": source,
    }


def live_points(weather=None, accidents=None):
    weather = weather or get_weather()
    if accidents is not None:
        acc_list = accidents
    else:
        acc_list, _ = get_all_incidents()
    flow_results = get_all_tomtom_flows()
    points = []
    for i, name in enumerate(COMUNAS_PRINCIPALES):
        lat, lng = COMUNAS_COORDS[name]
        flow = flow_results.get(i)
        points.append(_point(name, lat, lng, i, weather=weather, accidents=acc_list, traffic_flow=flow))
    return points


def current_points():
    return live_points()


def _compute_trends(avg_congestion, alert_count, incident_count, avg_risk, weather):
    from apps.traffic.models import TrafficRecord
    now = datetime.now()
    hour = now.hour
    dow = now.weekday()

    historical = TrafficRecord.objects.filter(
        source="TomTom Traffic API",
        recorded_at__hour=hour,
        recorded_at__week_day=dow + 1,
    ).aggregate(avg=models.Avg("congestion_level"), count=models.Count("id"))

    hist_avg = historical.get("avg")
    hist_count = historical.get("count", 0)

    if hist_avg is not None and hist_count >= 3 and avg_congestion is not None:
        diff = avg_congestion - float(hist_avg)
        congestion_trend = round(diff, 1)
    else:
        congestion_trend = None

    if hist_avg is not None and hist_count >= 3:
        hist_alerts = TrafficRecord.objects.filter(
            source="TomTom Traffic API",
            recorded_at__hour=hour,
            recorded_at__week_day=dow + 1,
            congestion_level__gte=55,
        ).count()
        avg_hist_alerts = hist_alerts / max(hist_count, 1) * 16
        alert_trend = round(alert_count - avg_hist_alerts, 1) if alert_count is not None else None
    else:
        alert_trend = None

    incident_trend = None

    if hist_avg is not None and hist_count >= 3 and avg_risk is not None:
        risk_trend = round(avg_risk - float(hist_avg) * 0.45, 1)
    else:
        risk_trend = None

    return congestion_trend, alert_trend, incident_trend, risk_trend


def bootstrap_data():
    cached = cache.get("bootstrap")
    if cached:
        return cached
    weather = get_weather()
    accidents, accidents_ok = get_all_incidents()
    points = live_points(weather, accidents)
    _now_str = datetime.now().strftime("%H:%M")
    _weather_now = weather
    alerts_data = [{
        "title": (
            f"🚨 Accidente: {p['name']}" if p["incidents"] > 0
            else f"🌧️ Lluvia: {p['name']}" if float(_weather_now.get("rain", 0) or 0) > 3
            else f"🚗 Congestión: {p['name']}"
        ),
        "zone": p["name"],
        "level": "high" if p["risk"] and p["risk"] > 70 else "medium" if p["risk"] and p["risk"] > 40 else "low",
        "icon": "🔴" if p["risk"] and p["risk"] > 70 else "🟡" if p["risk"] and p["risk"] > 40 else "🟢",
        "generated_at": _now_str,
        "description": (
            f"Congestión {p['congestion']}%, velocidad {p['speed']} km/h, índice de afectación {p['risk']}%"
            + (f", {p['incidents']} incidente(s)" if p['incidents'] > 0 else "")
            + (f", lluvia {_weather_now.get('rain', 0)} mm" if float(_weather_now.get('rain', 0) or 0) > 0 else "")
        ),
        "lat": p["lat"],
        "lng": p["lng"],
        "data_source": p.get("source", "estimacion local"),
    } for p in points if p["risk"] is not None and p["risk"] >= 40]
    by_comuna = {}
    for inc in accidents:
        c = inc.get("comuna")
        if c:
            by_comuna.setdefault(c, {"jams": 0, "road_closed": 0, "road_works": 0})
            cat = inc.get("icon_category")
            if cat == 6:     by_comuna[c]["jams"] += 1
            elif cat == 8:   by_comuna[c]["road_closed"] += 1
            elif cat == 9:   by_comuna[c]["road_works"] += 1

    zones = []
    for p in points:
        c_data = by_comuna.get(p["name"], {})
        congestion = p["congestion"] or 0
        clos = c_data.get("road_closed", 0)
        wrk = c_data.get("road_works", 0)

        delay_score = congestion * 0.6 + min(clos * 5, 30) + min(wrk * 3, 15)
        delay_val = min(round(delay_score), 100)
        delay_lvl = "Alto" if delay_val >= 70 else "Medio" if delay_val >= 40 else "Bajo"

        route_score = min(clos * 8, 40) + min(wrk * 5, 20)
        if congestion >= 70:
            route_score += min(25, 4)
        elif congestion >= 40:
            route_score += min(15, 2)
        route_val = min(round(route_score), 100)
        route_lvl = "Alto" if route_val >= 70 else "Medio" if route_val >= 40 else "Bajo"

        zones.append({
            "zone": p["name"], "lat": p["lat"], "lng": p["lng"],
            "congestion_level": p["congestion"], "average_speed": round(p["speed"], 1) if p["speed"] else None,
            "status": "critico" if p["congestion"] and p["congestion"] >= 75 else "moderado" if p["congestion"] and p["congestion"] >= 55 else "normal",
            "incidents": p["incidents"], "risk": p["risk"],
            "rain_probability": p["rain_probability"], "free_flow_speed": p["free_flow_speed"],
            "flow_confidence": p["flow_confidence"], "road_closure": p["road_closure"], "source": p["source"],
            "delay_risk_value": delay_val, "delay_risk_level": delay_lvl,
            "route_risk_value": route_val, "route_risk_level": route_lvl,
        })
    delay_risk = calculate_delay_risk(accidents, points)
    route_risk = calculate_route_risk(accidents, points)

    alert_count = len(alerts_data)

    from apps.alerts.services import active_alerts as _get_alerts
    try:
        real_alerts = _get_alerts()
        alert_count = len(real_alerts)
    except Exception:
        pass

    tomtom_flows = get_all_tomtom_flows()
    tomtom_speeds = [v["current_speed"] for v in tomtom_flows.values() if v and v.get("current_speed") is not None]
    avg_speed = round(sum(tomtom_speeds) / len(tomtom_speeds), 1) if tomtom_speeds else 0

    result = {
        "zones": zones,
        "alerts": alerts_data,
        "metrics": [
            {"label": "⏱️ Riesgo de retrasos", "value": (delay_risk["value"] if delay_risk["value"] is not None else "—"), "unit": "%", "level": delay_risk["level"]},
            {"label": "🛣️ Riesgo en ruta", "value": (route_risk["value"] if route_risk["value"] is not None else "—"), "unit": "%", "level": route_risk["level"]},
            {"label": "🚗 Velocidad promedio", "value": avg_speed, "unit": " km/h", "level": "Alto" if avg_speed <= 20 else "Medio" if avg_speed <= 40 else "Bajo"},
            {"label": "🚨 Alertas activas", "value": alert_count, "unit": "", "level": "Alto" if alert_count >= 10 else "Medio" if alert_count >= 5 else "Bajo"},
        ],
        "delay_risk": delay_risk,
        "route_risk": route_risk,
        "weather": weather,
        "incidents": accidents[:200],
        "accidents_api_ok": accidents_ok,
    }
    cache.set("bootstrap", result, 60)
    return result


TOMTOM_ICON_MAP = {
    1: ("Accidente",        "🚗", "#ef4444"),
    3: ("Cond. peligrosas", "⚠️", "#f59e0b"),
    6: ("Congestión",       "🚦", "#f97316"),
    8: ("Vía cerrada",      "🚫", "#7c3aed"),
    9: ("Obras",            "🚧", "#38bdf8"),
}

TOMTOM_INCIDENTS_FIELDS = "{incidents{type,geometry{type,coordinates},properties{iconCategory,magnitudeOfDelay,startTime,endTime,from,to,length,delay,numberOfReports}}}"

# Waze Livemap — sin API key, cubre accidentes y condiciones peligrosas en Medellín
WAZE_URL = "https://www.waze.com/live-map/api/georss"
WAZE_BBOX = {
    "top":    6.3500,
    "bottom": 6.1700,
    "left":  -75.6500,
    "right": -75.5100,
}
WAZE_TYPE_MAP = {
    "ACCIDENT": 1,
    "HAZARD":   3,
}
WAZE_SUBTYPE_LABELS = {
    "ACCIDENT_MAJOR":              "Accidente mayor",
    "ACCIDENT_MINOR":              "Accidente menor",
    "HAZARD_ON_ROAD":              "Peligro en vía",
    "HAZARD_ON_ROAD_POT_HOLE":    "Hueco en vía",
    "HAZARD_ON_ROAD_OBJECT":      "Objeto en vía",
    "HAZARD_ON_ROAD_CONSTRUCTION":"Construcción",
    "HAZARD_ON_ROAD_ICE":         "Hielo en vía",
    "HAZARD_ON_ROAD_LANE_CLOSED": "Carril cerrado",
    "HAZARD_ON_SHOULDER":         "Peligro en berma",
    "HAZARD_WEATHER":             "Clima peligroso",
    "HAZARD_WEATHER_FLOOD":       "Inundación",
    "HAZARD_WEATHER_FOG":         "Neblina",
    "HAZARD_WEATHER_HEAVY_RAIN":  "Lluvia intensa",
}


def get_waze_incidents():
    """Obtiene alertas de Waze Livemap (sin API key) — actualmente deshabilitado (403)."""
    cached = cache.get("waze_incidents")
    if cached is not None:
        return cached, True

    try:
        response = requests.get(
            WAZE_URL,
            params={**WAZE_BBOX, "env": "row", "types": "alerts"},
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.waze.com/"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()

        alerts = data.get("alerts", [])
        incidents = []
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

        for alert in alerts:
            waze_type = alert.get("type", "")
            icon_cat = WAZE_TYPE_MAP.get(waze_type)
            if icon_cat is None:
                continue

            category_name, icon, color = TOMTOM_ICON_MAP[icon_cat]
            loc = alert.get("location", {})
            lat = float(loc.get("y", 0))
            lng = float(loc.get("x", 0))
            if not lat or not lng:
                continue

            subtype = alert.get("subtype", "")
            description = (
                WAZE_SUBTYPE_LABELS.get(subtype)
                or alert.get("street")
                or category_name
            )

            incidents.append({
                "source":        "Waze",
                "lat":           lat,
                "lng":           lng,
                "category":      category_name,
                "icon_category": icon_cat,
                "icon":          icon,
                "color":         color,
                "from":          alert.get("street", ""),
                "description":   description,
                "magnitude":     0,
                "severity":      "",
                "fecha_hora":    now_str,
                "confidence":    alert.get("reliability", 0),
                "thumbs_up":     alert.get("reportRating", 0),
                "comuna":        _nearest_comuna(lat, lng),
                "neighborhood":  _nearest_neighborhood(lat, lng)[0],
            })

        logger.info("[waze] devolvió %d incidentes (acc+hazard)", len(incidents))
        cache.set("waze_incidents", incidents, 120)
        return incidents, True

    except Exception as e:
        logger.warning("[waze] error al consultar Waze Livemap: %s", e)
        cache.set("waze_incidents", [], 60)
        return [], False


def get_tomtom_incidents():
    cached = cache.get("tomtom_incidents")
    if cached:
        return cached, True

    api_key = _get_api_key()
    if not api_key:
        logger.warning("TOMTOM_API_KEY no configurada en .env")
        return [], False

    try:
        response = requests.get(
            TOMTOM_INCIDENTS_URL,
            params={
                "key": api_key,
                "bbox": MEDELLIN_BBOX,
                "fields": TOMTOM_INCIDENTS_FIELDS,
                "timeValidityFilter": "present",
                "language": "es-ES",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        features = data.get("incidents", [])
        incidents = []
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

        for feature in features:
            props = feature.get("properties", {})
            icon_cat = int(props.get("iconCategory") or 0)
            if icon_cat not in TOMTOM_ICON_MAP:
                continue
            category_name, icon, color = TOMTOM_ICON_MAP[icon_cat]
            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", [0, 0])
            if coords and isinstance(coords[0], (list, tuple)):
                lng, lat = float(coords[0][0]), float(coords[0][1])
            else:
                lng, lat = float(coords[0]), float(coords[1])

            from_str = props.get("from", "") or ""
            description = from_str or category_name

            start_time = props.get("startTime", "")
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    if timezone.is_aware(dt):
                        dt = timezone.localtime(dt)
                    fecha_hora = dt.strftime("%d/%m/%Y %H:%M")
                except (ValueError, AttributeError):
                    fecha_hora = now_str
            else:
                fecha_hora = now_str

            magnitude = props.get("magnitudeOfDelay", 0)

            incidents.append({
                "source": "TomTom Traffic API",
                "lat": lat,
                "lng": lng,
                "category": category_name,
                "icon_category": icon_cat,
                "icon": icon,
                "color": color,
                "from": from_str,
                "description": description,
                "magnitude": magnitude,
                "severity": "",
                "fecha_hora": fecha_hora,
                "confidence": props.get("probabilityOfOccurrence", 0),
                "thumbs_up": props.get("numberOfReports", 0),
                "comuna": _nearest_comuna(lat, lng),
                "neighborhood": _nearest_neighborhood(lat, lng)[0],
            })

        logger.info("[incidents] TomTom devolvió %d incidentes", len(incidents))
        cache.set("tomtom_incidents", incidents, 600)
        return incidents, True

    except requests.RequestException as e:
        err_msg = getattr(e.response, 'text', str(e)) if hasattr(e, 'response') else str(e)
        logger.warning("[incidents] error al consultar TomTom API: %s", err_msg)

        is_permanent = False
        try:
            body = e.response.json() if hasattr(e, 'response') and e.response else {}
            code = body.get("detailedError", {}).get("code", "")
            if code in ("InsufficientFunds", "Forbidden", "InvalidKey", "Unauthorized"):
                is_permanent = True
        except Exception:
            pass

        ttl = 600 if is_permanent else 30
        if is_permanent:
            logger.error("[incidents] Error permanente '%s' — pausando llamadas por 10 minutos", code)
        cache.set("tomtom_incidents", [], ttl)
        return [], False


def get_all_incidents():
    """
    Retorna todos los incidentes de TomTom sin filtrar (accidentes, peligros, congestión, etc.).
    TomTom es la única fuente real.
    """
    tomtom_incidents, ok = get_tomtom_incidents()
    logger.info("[incidents] %d incidentes desde TomTom", len(tomtom_incidents))
    return tomtom_incidents, ok


def get_weather():
    cached = cache.get("weather")
    if cached:
        return cached
    params = {
        "latitude": MEDELLIN_CENTER[0],
        "longitude": MEDELLIN_CENTER[1],
        "current": "temperature_2m,apparent_temperature,precipitation,rain,relative_humidity_2m,wind_speed_10m,weather_code",
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
        result = {
            "temperature": current.get("temperature_2m", 23),
            "apparent_temperature": current.get("apparent_temperature", 23),
            "weather_code": current.get("weather_code", 0),
            "rain": current.get("rain", 0),
            "precipitation": current.get("precipitation", 0),
            "humidity": current.get("relative_humidity_2m", 0),
            "wind_speed": current.get("wind_speed_10m", 0),
            "precipitation_probability": probability,
            "source": "Open-Meteo",
        }
        cache.set("weather", result, 180)
        return result
    except requests.RequestException:
        return {"temperature": None, "apparent_temperature": None, "weather_code": 0, "rain": 0, "precipitation": 0, "humidity": None, "wind_speed": None, "precipitation_probability": 0, "source": "sin-datos-clima"}


def calculate_delay_risk(incidents, zones):
    """
    ⏱️ Riesgo de retrasos
    Evalúa congestión (cat 6), cierres (cat 8) y obras (cat 9) para estimar
    la probabilidad de sufrir retrasos en los desplazamientos.
    Usa exclusivamente datos reales de TomTom.
    """
    closures = [i for i in incidents if i.get("icon_category") == 8]
    works = [i for i in incidents if i.get("icon_category") == 9]
    congestion_zones = [z for z in zones if z.get("congestion") is not None]

    if not congestion_zones and not closures and not works:
        return {
            "value": None, "level": "Datos insuficientes",
            "last_updated": None, "details": {}
        }

    avg_congestion = sum(z["congestion"] for z in congestion_zones) / len(congestion_zones) if congestion_zones else 0
    closure_factor = len(closures) * 5
    works_factor = len(works) * 3

    score = avg_congestion * 0.6 + min(closure_factor, 30) + min(works_factor, 15)
    value = min(round(score), 100)
    level = "Alto" if value >= 70 else "Medio" if value >= 40 else "Bajo"

    return {
        "value": value,
        "level": level,
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "details": {
            "congestion_promedio": round(avg_congestion, 1),
            "vias_cerradas": [
                {"via": c.get("from", "Vía sin nombre"), "comuna": c.get("comuna", "")}
                for c in closures
            ],
            "obras_en_curso": [
                {"via": w.get("from", "Vía sin nombre"), "comuna": w.get("comuna", "")}
                for w in works
            ],
            "factor_estimado": {
                "congestion": round(avg_congestion * 0.6, 1),
                "cierres": min(closure_factor, 30),
                "obras": min(works_factor, 15),
            }
        }
    }


def calculate_route_risk(incidents, zones):
    """
    🛣️ Riesgo en ruta
    Evalúa cierres (cat 8), obras (cat 9) y congestión alta (cat 6) que afectan
    la disponibilidad y fluidez de las rutas disponibles.
    Usa exclusivamente datos reales de TomTom.
    """
    closures = [i for i in incidents if i.get("icon_category") == 8]
    works = [i for i in incidents if i.get("icon_category") == 9]
    congestion_zones = [z for z in zones if z.get("congestion") is not None]

    if not congestion_zones and not closures and not works:
        return {
            "value": None, "level": "Datos insuficientes",
            "last_updated": None, "details": {}
        }

    high_cong = [z for z in congestion_zones if z["congestion"] >= 70]
    mod_cong = [z for z in congestion_zones if 40 <= z["congestion"] < 70]

    closure_impact = len(closures) * 8
    works_impact = len(works) * 5
    high_cong_impact = len(high_cong) * 4
    mod_cong_impact = len(mod_cong) * 2

    score = min(closure_impact, 40) + min(works_impact, 20) + min(high_cong_impact, 25) + min(mod_cong_impact, 15)
    value = min(round(score), 100)
    level = "Alto" if value >= 70 else "Medio" if value >= 40 else "Bajo"

    return {
        "value": value,
        "level": level,
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "details": {
            "vias_cerradas": [
                {"via": c.get("from", "Vía sin nombre"), "comuna": c.get("comuna", "")}
                for c in closures
            ],
            "obras_en_curso": [
                {"via": w.get("from", "Vía sin nombre"), "comuna": w.get("comuna", "")}
                for w in works
            ],
            "zonas_congestion_alta": [
                {"nombre": z["name"], "congestion": z["congestion"]} for z in high_cong
            ],
            "zonas_congestion_moderada": [
                {"nombre": z["name"], "congestion": z["congestion"]} for z in mod_cong
            ],
            "factor_estimado": {
                "cierres_bloqueo": min(closure_impact, 40),
                "obras_afectacion": min(works_impact, 20),
                "congestion_alta": min(high_cong_impact, 25),
                "congestion_moderada": min(mod_cong_impact, 15),
            }
        }
    }


def city_summary():
    cached = cache.get("city_summary")
    if cached:
        return cached
    weather = get_weather()
    accidents, accidents_ok = get_all_incidents()
    points = live_points(weather, accidents)
    points = [p for p in points if p["congestion"] is not None]
    if not points:
        return {"generated_at": datetime.now().isoformat(timespec="seconds"), "metrics": [], "weather": weather, "incidents": [], "commercial_api": {"provider": "TomTom Traffic API", "enabled": bool(_get_api_key()), "live_segments": 0, "cache_ttl_seconds": 6}, "zones": [], "accidents_api_ok": accidents_ok}
    avg = sum(p["congestion"] for p in points) / len(points)
    risk_vals = [p["risk"] for p in points if p["risk"] is not None]
    avg_risk = sum(risk_vals) / len(risk_vals) if risk_vals else 0
    alerts = len([p for p in points if p["risk"] and p["risk"] >= 55])
    commercial_count = len([p for p in points if p["source"] == "TomTom Traffic API"])

    delay_risk = calculate_delay_risk(accidents, points)
    route_risk = calculate_route_risk(accidents, points)

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "metrics": [
            {"label": "⏱️ Riesgo de retrasos", "value": (delay_risk["value"] if delay_risk["value"] is not None else "—"), "unit": "%", "level": delay_risk["level"]},
            {"label": "🛣️ Riesgo en ruta", "value": (route_risk["value"] if route_risk["value"] is not None else "—"), "unit": "%", "level": route_risk["level"]},
        ],
        "delay_risk": delay_risk,
        "route_risk": route_risk,
        "weather": weather,
        "incidents": accidents[:200],
        "commercial_api": {
            "provider": "TomTom Traffic API",
            "enabled": bool(_get_api_key()),
            "live_segments": commercial_count,
            "cache_ttl_seconds": 6,
        },
        "zones": points,
        "accidents_api_ok": accidents_ok,
    }
    cache.set("city_summary", result, 60)
    return result


def _translate_maneuver(mtype, modifier):
    modifier_es = {
        "left": "a la izquierda",
        "right": "a la derecha",
        "sharp left": "fuertemente a la izquierda",
        "sharp right": "fuertemente a la derecha",
        "slight left": "levemente a la izquierda",
        "slight right": "levemente a la derecha",
        "straight": "recto",
        "uturn": "en U",
    }
    if mtype == "depart":
        return "Sal e inicia el recorrido"
    if mtype == "arrive":
        return "Llegas a tu destino"
    if mtype == "roundabout" or mtype == "rotary":
        return "Toma la rotonda"
    if mtype in ("turn", "end of road", "fork", "merge", "ramp", "on ramp", "off ramp"):
        if modifier in modifier_es:
            if modifier == "straight":
                return "Continúa recto"
            return f"Gira {modifier_es[modifier]}"
        return "Continúa"
    if mtype == "continue":
        return "Continúa recto"
    if mtype == "new name":
        return "Continúa (la vía cambia de nombre)"
    return ""


def route_options(origin_name, origin_lat, origin_lng, dest_name, dest_lat, dest_lng):
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
            f"?overview=false&steps=true"
        )
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        route = data["routes"][0]
        dist_km = round(route["distance"] / 1000, 1)
        time_min = round(route["duration"] / 60)
        risk = None
        points = live_points()
        centro_point = next((p for p in points if p["name"] == dest_name), None)
        origin_point = next((p for p in points if p["name"] == origin_name), None)
        if origin_point and origin_point.get("risk") is not None:
            risk = origin_point["risk"]

        steps_info = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                name = (step.get("name") or "").strip()
                maneuver = step.get("maneuver", {}) or {}
                mtype = maneuver.get("type")
                modifier = maneuver.get("modifier")
                instruction = _translate_maneuver(mtype, modifier)
                if not name and not instruction:
                    continue
                steps_info.append({"street": name, "instruction": instruction})

        streets = []
        for s in steps_info:
            if s["street"] and s["street"] not in streets:
                streets.append(s["street"])

        return [{
            "name": f"{origin_name} → {dest_name}",
            "origin": origin_name,
            "destination": dest_name,
            "time": time_min,
            "risk": risk,
            "distance": dist_km,
            "streets": streets,
            "steps": steps_info,
            "points": [[origin_lat, origin_lng], [dest_lat, dest_lng]],
        }]
    except Exception:
        logger.exception("route_options falló para %s -> %s", origin_name, dest_name)
        return []
