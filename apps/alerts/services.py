from apps.dashboard.services import current_points, get_weather, get_all_incidents
from apps.alerts.models import MobilityAlert
import datetime


def _level_and_icon(risk):
    if risk >= 75:
        return "alta", "🔴"
    if risk >= 55:
        return "media", "🟡"
    return "baja", "🟢"


def active_alerts():
    now = datetime.datetime.now()
    now_ts = now.timestamp()
    now_str = now.strftime("%d/%m/%Y %H:%M")
    weather = get_weather()
    points = current_points()
    accidents_list, accidents_ok = get_all_incidents()
    alerts = []

    def _parse_ts(fecha_hora):
        try:
            return datetime.datetime.strptime(fecha_hora, "%d/%m/%Y %H:%M").timestamp()
        except (ValueError, TypeError):
            return now_ts

    for p in points:
        risk = p["risk"] or 0
        if risk < 40:
            continue
        level, icon = _level_and_icon(risk)
        if p["incidents"] > 0:
            kind, kind_icon = "incidente", "🚨"
        elif float(weather.get("rain", 0) or 0) > 3:
            kind, kind_icon = "lluvia", "🌧️"
        elif p.get("road_closure"):
            kind, kind_icon = "via cerrada", "🚫"
        else:
            kind, kind_icon = "congestión", "🚗"
        alerts.append({
            "title": f"{kind_icon} {kind.capitalize()}: {p['name']}",
            "zone": p["name"],
            "level": level,
            "icon": icon,
            "tipo": kind,
            "description": (
                f"Congestión {p['congestion']}%, velocidad {p['speed']} km/h, "
                f"índice de afectación {risk}%"
                + (f", {p['incidents']} incidente(s)" if p["incidents"] > 0 else "")
                + (f", lluvia {weather.get('rain', 0)} mm" if float(weather.get('rain', 0) or 0) > 0 else "")
            ),
            "lat": p["lat"],
            "lng": p["lng"],
            "generated_at": now_str,
            "data_source": p.get("source", "Estimación local"),
            "category": "zona",
            "_ts": now_ts,
        })

    for inc in accidents_list:
        cat = inc.get("category", "Incidente")
        icon_cat = inc.get("icon_category", 0)
        level = "alta" if icon_cat in (1, 8) else "media" if icon_cat in (3, 6) else "baja"
        alerts.append({
            "title": f"{inc.get('icon', '⚠️')} {cat}: {inc.get('from', inc.get('description', ''))}",
            "zone": inc.get("comuna") or inc.get("neighborhood") or "Medellín",
            "level": level,
            "icon": "🔴" if level == "alta" else "🟡" if level == "media" else "🟢",
            "tipo": cat.lower(),
            "description": inc.get("description", cat),
            "lat": inc.get("lat"),
            "lng": inc.get("lng"),
            "generated_at": inc.get("fecha_hora", now_str),
            "data_source": inc.get("source", "TomTom / Waze"),
            "category": "incidente",
            "_ts": _parse_ts(inc.get("fecha_hora")),
        })

    rain = float(weather.get("rain", 0) or 0)
    precip_prob = int(weather.get("precipitation_probability", 0) or 0)
    temp = float(weather.get("temperature", 23) or 23)
    if rain > 10:
        alerts.append({
            "title": "🌧️ Lluvia intensa en Medellín",
            "zone": "Medellín", "level": "alta", "icon": "🔴", "tipo": "lluvia",
            "description": f"Precipitación de {rain} mm, probabilidad de lluvia {precip_prob}%. Conduzca con precaución.",
            "lat": 6.2442, "lng": -75.5812, "generated_at": now_str,
            "data_source": "Open-Meteo", "category": "clima", "_ts": now_ts,
        })
    elif rain > 3:
        alerts.append({
            "title": "🌧️ Lluvia moderada",
            "zone": "Medellín", "level": "media", "icon": "🟡", "tipo": "lluvia",
            "description": f"Precipitación de {rain} mm. Posibles afectaciones viales.",
            "lat": 6.2442, "lng": -75.5812, "generated_at": now_str,
            "data_source": "Open-Meteo", "category": "clima", "_ts": now_ts,
        })
    if temp > 30:
        alerts.append({
            "title": "🌡️ Temperatura alta",
            "zone": "Medellín", "level": "media", "icon": "🟡", "tipo": "calor",
            "description": f"Temperatura actual de {temp}°C. Manténgase hidratado.",
            "lat": 6.2442, "lng": -75.5812, "generated_at": now_str,
            "data_source": "Open-Meteo", "category": "clima", "_ts": now_ts,
        })

    try:
        db_alerts = MobilityAlert.objects.filter(active=True).order_by("-created_at")[:20]
        for a in db_alerts:
            alerts.append({
                "title": a.title, "zone": a.zone, "level": a.level,
                "icon": "🔴" if a.level == "alta" else "🟡" if a.level == "media" else "🟢",
                "tipo": "predicción", "description": a.description,
                "lat": None, "lng": None,
                "generated_at": a.created_at.strftime("%d/%m/%Y %H:%M"),
                "data_source": "Modelo de predicción", "category": "prediccion",
                "_ts": a.created_at.timestamp(),
            })
    except Exception:
        pass

    tomtom_count = sum(1 for p in points if p.get("source") == "TomTom Traffic API")
    total_points = len(points)
    if total_points > 0 and tomtom_count < total_points:
        degraded = total_points - tomtom_count
        alerts.append({
            "title": "⚠️ Degradación de datos TomTom",
            "zone": "Medellín", "level": "media", "icon": "🟡", "tipo": "sistema",
            "description": (
                f"{degraded} de {total_points} zonas usan estimación local "
                f"(TomTom Traffic API no disponible). Los datos pueden no reflejar la congestión real."
            ),
            "lat": 6.2442, "lng": -75.5812, "generated_at": now_str,
            "data_source": "Sistema", "category": "sistema", "_ts": now_ts,
        })

    for p in points:
        if p.get("road_closure"):
            alerts.append({
                "title": f"🚫 Vía cerrada: {p['name']}",
                "zone": p["name"], "level": "alta", "icon": "🔴", "tipo": "via cerrada",
                "description": f"Congestión del {p['congestion']}% — posible cierre de vía en {p['name']}.",
                "lat": p["lat"], "lng": p["lng"], "generated_at": now_str,
                "data_source": p.get("source", "TomTom Traffic API"),
                "category": "incidente", "_ts": now_ts,
            })

    LEVEL_ORDER = {"alta": 0, "media": 1, "baja": 2}
    alerts.sort(key=lambda a: (a.get("_ts", 0), -LEVEL_ORDER.get(a.get("level", "baja"), 2)), reverse=True)
    return alerts
