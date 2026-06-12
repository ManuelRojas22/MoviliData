import json
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from apps.maps.services import map_statistics_payload
from apps.dashboard.services import get_all_incidents, calculate_delay_risk, calculate_route_risk, COMUNAS_COORDS, COMUNA_NUMEROS, COMUNA_NOMBRES_COMPLETOS, current_points, get_weather


def risk_zones(request):
    ctx = {
        "maps_data": map_statistics_payload(),
        "comunas_json": json.dumps(list(COMUNAS_COORDS.keys())),
        "comunas_coords_json": json.dumps(COMUNAS_COORDS),
    }
    return render(request, "maps/risk-zones.html", ctx)


def comuna_detail(request, comuna_name):
    comuna_name = comuna_name.replace("-", " ").title()
    if comuna_name == "El Poblado":
        comuna_name = "El Poblado"
    elif comuna_name == "Doce De Octubre":
        comuna_name = "Doce de Octubre"
    elif comuna_name == "San Javier":
        comuna_name = "San Javier"
    elif comuna_name == "La America":
        comuna_name = "La América"
    if comuna_name not in COMUNAS_COORDS:
        raise Http404("Comuna no encontrada")
    points = current_points()
    comuna_data = next((p for p in points if p["name"] == comuna_name), None)
    incidents, ok = get_all_incidents()
    comuna_incidents = [i for i in incidents if i.get("comuna") == comuna_name]
    weather = get_weather()
    delay_risk = calculate_delay_risk(incidents, points)
    route_risk = calculate_route_risk(incidents, points)
    ctx = {
        "comuna": {
            "name": comuna_name,
            "full_name": COMUNA_NOMBRES_COMPLETOS.get(comuna_name, comuna_name),
            "numero": COMUNA_NUMEROS.get(comuna_name, "?"),
            "lat": COMUNAS_COORDS[comuna_name][0],
            "lng": COMUNAS_COORDS[comuna_name][1],
            "data": comuna_data,
            "incidents": comuna_incidents[:50],
            "incident_count": len(comuna_incidents),
            "delay_risk": delay_risk,
            "route_risk": route_risk,
        },
        "weather": weather,
        "all_comunas": list(COMUNAS_COORDS.keys()),
    }
    return render(request, "maps/comuna-detail.html", ctx)


def api_comuna_detail(request, comuna_name):
    comuna_name = comuna_name.replace("-", " ").title()
    if comuna_name == "El Poblado":
        comuna_name = "El Poblado"
    elif comuna_name == "Doce De Octubre":
        comuna_name = "Doce de Octubre"
    elif comuna_name == "San Javier":
        comuna_name = "San Javier"
    elif comuna_name == "La America":
        comuna_name = "La América"
    if comuna_name not in COMUNAS_COORDS:
        return JsonResponse({"error": "Comuna no encontrada"}, status=404)
    points = current_points()
    comuna_data = next((p for p in points if p["name"] == comuna_name), None)
    incidents, ok = get_all_incidents()
    comuna_incidents = [i for i in incidents if i.get("comuna") == comuna_name]
    return JsonResponse({
        "comuna": comuna_name,
        "numero": COMUNA_NUMEROS.get(comuna_name),
        "full_name": COMUNA_NOMBRES_COMPLETOS.get(comuna_name),
        "data": comuna_data,
        "incidents": comuna_incidents[:50],
        "incident_count": len(comuna_incidents),
        "total_incidents": len(comuna_incidents),
    })


def api_maps(request):
    return JsonResponse(map_statistics_payload())


@never_cache
def api_incidents(request):
    incidents, ok = get_all_incidents()
    points = current_points()
    delay_risk = calculate_delay_risk(incidents, points)
    route_risk = calculate_route_risk(incidents, points)
    accidents   = sum(1 for i in incidents if i.get("icon_category") == 1)
    jams        = sum(1 for i in incidents if i.get("icon_category") == 6)
    road_closed = sum(1 for i in incidents if i.get("icon_category") == 8)
    road_works  = sum(1 for i in incidents if i.get("icon_category") == 9)

    by_comuna = {}
    by_neighborhood = {}
    for inc in incidents:
        c = inc.get("comuna")
        if c:
            by_comuna.setdefault(c, {"total": 0, "accidents": 0, "jams": 0, "road_closed": 0, "road_works": 0})
            by_comuna[c]["total"] += 1
            cat = inc.get("icon_category")
            if cat == 1:     by_comuna[c]["accidents"] += 1
            elif cat == 6:   by_comuna[c]["jams"] += 1
            elif cat == 8:   by_comuna[c]["road_closed"] += 1
            elif cat == 9:   by_comuna[c]["road_works"] += 1

        n = inc.get("neighborhood")
        if n:
            by_neighborhood.setdefault(n, {"total": 0, "jams": 0, "road_closed": 0, "road_works": 0})
            by_neighborhood[n]["total"] += 1
            cat = inc.get("icon_category")
            if cat == 6:     by_neighborhood[n]["jams"] += 1
            elif cat == 8:   by_neighborhood[n]["road_closed"] += 1
            elif cat == 9:   by_neighborhood[n]["road_works"] += 1

    points_map = {p["name"]: p for p in points}
    for c_name, c_data in by_comuna.items():
        pt = points_map.get(c_name, {})
        congestion = pt.get("congestion", 0) or 0
        clos = c_data.get("road_closed", 0)
        wrk = c_data.get("road_works", 0)

        delay_score = congestion * 0.6 + min(clos * 5, 30) + min(wrk * 3, 15)
        delay_val = min(round(delay_score), 100)
        c_data["delay_risk_value"] = delay_val
        c_data["delay_risk_level"] = "Alto" if delay_val >= 70 else "Medio" if delay_val >= 40 else "Bajo"

        route_score = min(clos * 8, 40) + min(wrk * 5, 20)
        if congestion >= 70:
            route_score += min(25, 4)
        elif congestion >= 40:
            route_score += min(15, 2)
        route_val = min(round(route_score), 100)
        c_data["route_risk_value"] = route_val
        c_data["route_risk_level"] = "Alto" if route_val >= 70 else "Medio" if route_val >= 40 else "Bajo"

    return JsonResponse({
        "ok": ok,
        "total": len(incidents),
        "delay_risk": delay_risk,
        "route_risk": route_risk,
        "accidents": accidents,
        "jams": jams,
        "road_closed": road_closed,
        "road_works": road_works,
        "incidents": incidents,
        "by_comuna": by_comuna,
        "by_neighborhood": by_neighborhood,
    })
