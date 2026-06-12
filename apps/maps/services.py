from datetime import datetime

from django.core.cache import cache
from apps.dashboard.services import MEDELLIN_CENTER, current_points, get_all_incidents, calculate_delay_risk, calculate_route_risk, COMUNAS_PRINCIPALES


def risk_zone_layer():
    return current_points()


def map_statistics_payload(force_refresh=False):
    if not force_refresh:
        cached = cache.get("map_statistics")
        if cached:
            return cached
    points = risk_zone_layer()
    points = [p for p in points if p["name"] in COMUNAS_PRINCIPALES]
    incidents, _ = get_all_incidents()
    delay_risk = calculate_delay_risk(incidents, points)
    route_risk = calculate_route_risk(incidents, points)

    closures_per_zone = {}
    works_per_zone = {}
    for inc in incidents:
        comuna = inc.get("comuna")
        cat = inc.get("icon_category")
        if comuna and cat == 8:
            closures_per_zone[comuna] = closures_per_zone.get(comuna, 0) + 1
        if comuna and cat == 9:
            works_per_zone[comuna] = works_per_zone.get(comuna, 0) + 1

    zones = [{
        "name": p["name"],
        "lat": p["lat"],
        "lng": p["lng"],
        "risk_score": p["risk"] or 0,
        "heat": round((p["risk"] or 0) / 100, 2),
        "congestion": p["congestion"] or 0,
        "rain_probability": p["rain_probability"] or 0,
        "closures": closures_per_zone.get(p["name"], 0),
        "works": works_per_zone.get(p["name"], 0),
        "average_speed": round(p["speed"] or 0, 1),
        "reason": (
            f"Congestión {p['congestion'] or 0}%"
            + (f", {closures_per_zone.get(p['name'], 0)} vía(s) cerrada(s)" if closures_per_zone.get(p['name'], 0) else "")
            + (f", {works_per_zone.get(p['name'], 0)} obra(s)" if works_per_zone.get(p['name'], 0) else "")
            + f", lluvia {p['rain_probability'] or 0}%"
        ),
        "source": p["source"],
        "delay_risk_value": delay_risk.get("value"),
        "delay_risk_level": delay_risk.get("level"),
        "route_risk_value": route_risk.get("value"),
        "route_risk_level": route_risk.get("level"),
    } for p in points]

    result = {
        "center": MEDELLIN_CENTER,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cache_ttl_seconds": 0,
        "risk_zones": zones,
        "delay_risk": delay_risk,
        "route_risk": route_risk,
    }
    cache.set("map_statistics", result, 60)
    return result
