from datetime import datetime

from apps.dashboard.services import MEDELLIN_CENTER, demo_points


def risk_zone_layer():
    return demo_points()


def map_statistics_payload(force_refresh=False):
    points = risk_zone_layer()
    zones = [{
        "name": p["name"],
        "lat": p["lat"],
        "lng": p["lng"],
        "risk_score": p["risk"],
        "heat": round(p["risk"] / 100, 2),
        "congestion": p["congestion"],
        "rain_probability": p["rain_probability"],
        "incidents": p["incidents"],
        "average_speed": round(p["speed"], 1),
        "reason": f"Congestion {p['congestion']}%, lluvia {p['rain_probability']}%, incidentes {p['incidents']}",
        "source": p["source"],
    } for p in points]

    return {
        "center": MEDELLIN_CENTER,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cache_ttl_seconds": 0,
        "risk_zones": zones,
    }
