import json
import logging
import math
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from apps.dashboard.services import current_points

logger = logging.getLogger(__name__)

OSRM_PROFILES = {"driving": "driving", "cycling": "cycling", "walking": "walking"}

OSRM_URLS = {
    "driving": "https://router.project-osrm.org/route/v1/driving/{coords}",
    "cycling": "https://routing.openstreetmap.de/routed-bike/route/v1/driving/{coords}",
    "walking": "https://routing.openstreetmap.de/routed-foot/route/v1/driving/{coords}",
}

MODE_LABELS = {
    "driving": "🚗 En carro",
    "cycling": "🚲 En bicicleta",
    "walking": "🚶 A pie",
}

# Velocidades de referencia en km/h para estimar tiempo cuando OSRM no responde
FALLBACK_SPEEDS = {"driving": 30, "cycling": 15, "walking": 5}


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return round(R * 2 * math.asin(math.sqrt(a)) * 1.35, 2)


def _get_osrm_route(waypoints, mode="driving"):
    """
    Consulta OSRM y devuelve (polyline, dist_km, time_min) o None si falla.
    Cada perfil usa infraestructura vial real distinta:
      - driving: calles vehiculares, autopistas
      - cycling: ciclovías, calles tranquilas, rutas compartidas
      - walking:  senderos peatonales, pasos, zonas sin vehículos
    """
    coords = ";".join(f"{lng},{lat}" for lat, lng in waypoints)
    url_template = OSRM_URLS.get(mode, OSRM_URLS["driving"])
    url = url_template.format(coords=coords) + "?geometries=geojson&overview=full&steps=false&alternatives=false"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MoviliData/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            raw_coords = route["geometry"]["coordinates"]
            polyline = [[round(c[1], 6), round(c[0], 6)] for c in raw_coords]
            dist_km = round(route["distance"] / 1000, 2)
            # OSRM devuelve duración en segundos con su propio modelo de velocidad por perfil
            time_min = max(1, round(route["duration"] / 60))
            return polyline, dist_km, time_min
    except Exception as e:
        logger.warning("[OSRM] perfil=%s error=%s url=%s", mode, e, url)
    return None


def _enrich_with_real_data(origin_name, dest_name, dist_km, time_min, polyline, mode):
    """
    Enriquece una ruta con datos reales de TomTom + lluvia + incidentes.

    Estrategia de riesgo real:
      1. Busca en current_points() el punto cuyo nombre coincida con origin o dest.
      2. Si encuentra TomTom en alguno, toma el mayor risk entre origen y destino
         (el tramo más congestionado manda).
      3. Ajusta el riesgo según el modo: ciclistas y peatones tienen mayor exposición
         a lluvia y menos protección, así que se suma un bonus si hay lluvia.
      4. Si no hay datos TomTom, retorna risk=None (honesto, no un 50 inventado).
    """
    points = current_points()
    point_map = {p["name"].lower(): p for p in points}

    origin_pt = point_map.get(origin_name.lower())
    dest_pt = point_map.get(dest_name.lower())

    # Tomar el mayor riesgo entre origen y destino (el peor tramo)
    risks = []
    rain_prob = 0
    for pt in [origin_pt, dest_pt]:
        if pt is None:
            continue
        if pt.get("risk") is not None:
            risks.append(pt["risk"])
        if pt.get("rain_probability") is not None:
            rain_prob = max(rain_prob, pt["rain_probability"])

    if not risks:
        base_risk = None
    else:
        base_risk = max(risks)

    # Ajuste por modo: ciclistas y peatones más expuestos a lluvia
    if base_risk is not None:
        if mode == "cycling" and rain_prob > 50:
            base_risk = min(100, base_risk + 10)
        elif mode == "walking" and rain_prob > 50:
            base_risk = min(100, base_risk + 15)

    # Congestion y speed reales del origen (el punto de partida)
    congestion = origin_pt.get("congestion") if origin_pt else None
    speed = origin_pt.get("speed") if origin_pt else None
    incidents = (origin_pt.get("incidents", 0) if origin_pt else 0) + (dest_pt.get("incidents", 0) if dest_pt else 0)
    source = origin_pt.get("source", "sin datos") if origin_pt else "sin datos"

    return {
        "name": f"{MODE_LABELS[mode]}: {origin_name} \u2192 {dest_name}",
        "origin": origin_name,
        "destination": dest_name,
        "mode": mode,
        "distance": dist_km,
        "time": time_min,          # tiempo real de OSRM para ese perfil
        "risk": base_risk,         # None = sin datos TomTom; int = riesgo real 0-100
        "congestion": congestion,
        "speed": speed,
        "incidents": incidents,
        "rain_probability": rain_prob,
        "source": source,
        "points": polyline,
    }


def _geocode_nominatim(name):
    """
    Geocodifica un nombre o dirección libre contra Nominatim OSM.
    Retorna (lat, lng) como floats, o (None, None) si falla.
    Auto-apende ", Medellín, Colombia" si no está presente.
    """
    if "medell" not in name.lower():
        name = name.strip() + ", Medellín, Colombia"
    query = urllib.parse.quote(name)
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={query}&format=json&limit=1&countrycodes=co"
        "&viewbox=-75.75,6.05,-75.45,6.45&bounded=0"
    )
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "MoviliData/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        if data:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            logger.info(
                "[Nominatim] '%s' \u2192 %.6f, %.6f (type=%s)",
                name, lat, lng, data[0].get("type", "?")
            )
            return lat, lng
    except Exception as e:
        logger.warning("[Nominatim] fallo geocodificando '%s': %s", name, e)
    return None, None


def recommended_routes(
    origin=None,
    destination=None,
    origin_coords=None,
    dest_coords=None,
    mode="all",
    avoid_tolls="0",
    routes_data=None,
):
    """
    Enriquece rutas con datos TomTom.

    Si routes_data es una lista de dicts (calculados en el frontend),
    solo enriquece con TomTom y devuelve. Como fallback legacy, si
    vienen origin_coords/dest_coords, consulta OSRM desde el backend.
    """
    if not origin and not destination:
        return []

    try:
        origin_name = (origin or "Origen").strip()
        dest_name   = (destination or "Destino").strip()

        # Si el frontend envió las rutas ya calculadas, solo enriquecer con TomTom
        if routes_data:
            results = []
            for r in routes_data:
                route = _enrich_with_real_data(
                    origin_name, dest_name,
                    r["dist"], r["time"], r["points"], r["mode"]
                )
                if r.get("source") == "estimado":
                    route["source"] = "estimado (sin conexión OSRM)"
                results.append(route)
            order = {"driving": 0, "cycling": 1, "walking": 2}
            results.sort(key=lambda x: order.get(x["mode"], 99))
            return results

        # Fallback legacy: si no vienen rutas del frontend, intentar con coords
        if origin_coords and None not in origin_coords and dest_coords and None not in dest_coords:
            origin_lat, origin_lng = float(origin_coords[0]), float(origin_coords[1])
            dest_lat,   dest_lng   = float(dest_coords[0]),   float(dest_coords[1])
            modes_to_run = ["driving", "cycling", "walking"] if mode == "all" else [mode if mode in OSRM_PROFILES else "driving"]
            results = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(_get_osrm_route, [[origin_lat, origin_lng], [dest_lat, dest_lng]], m): m
                    for m in modes_to_run
                }
                for future in as_completed(futures):
                    m = futures[future]
                    osrm_result = future.result()
                    if osrm_result is None:
                        dist_km = _haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
                        speed   = FALLBACK_SPEEDS[m]
                        time_min = max(1, round(dist_km / speed * 60))
                        polyline = [[origin_lat, origin_lng], [dest_lat, dest_lng]]
                        route = _enrich_with_real_data(
                            origin_name, dest_name, dist_km, time_min, polyline, m
                        )
                        route["source"] = "estimado (OSRM no disponible)"
                        results.append(route)
                        continue
                    polyline, dist_km, time_min = osrm_result
                    route = _enrich_with_real_data(
                        origin_name, dest_name, dist_km, time_min, polyline, m
                    )
                    results.append(route)
            order = {"driving": 0, "cycling": 1, "walking": 2}
            results.sort(key=lambda r: order.get(r["mode"], 99))
            return results

        logger.warning(
            "[recommended_routes] coordenadas no resueltas — "
            "origen='%s' destino='%s'",
            origin_name, dest_name
        )
        return []

    except Exception as e:
        logger.exception("[recommended_routes] error inesperado: %s", e)
        return []
