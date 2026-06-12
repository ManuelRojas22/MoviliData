import json
import logging
import sys
import traceback

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .services import MODE_LABELS, _enrich_with_real_data, recommended_routes

logger = logging.getLogger(__name__)

NEIGHBORHOODS = [
    {"name": "Popular", "lat": 6.3085, "lng": -75.5579, "group": "📍 Comuna 1 — Popular"},
    {"name": "Granizal", "lat": 6.3012, "lng": -75.5501, "group": "📍 Comuna 1 — Popular"},
    {"name": "Santa Cruz", "lat": 6.2985, "lng": -75.5612, "group": "📍 Comuna 2 — Santa Cruz"},
    {"name": "Villa del Socorro", "lat": 6.2930, "lng": -75.5534, "group": "📍 Comuna 2 — Santa Cruz"},
    {"name": "Manrique", "lat": 6.2746, "lng": -75.5523, "group": "📍 Comuna 3 — Manrique"},
    {"name": "La Cruz", "lat": 6.2810, "lng": -75.5467, "group": "📍 Comuna 3 — Manrique"},
    {"name": "Aranjuez", "lat": 6.2860, "lng": -75.5650, "group": "📍 Comuna 4 — Aranjuez"},
    {"name": "Brasilia", "lat": 6.2795, "lng": -75.5712, "group": "📍 Comuna 4 — Aranjuez"},
    {"name": "Castilla", "lat": 6.2923, "lng": -75.5707, "group": "📍 Comuna 5 — Castilla"},
    {"name": "Florencia", "lat": 6.2975, "lng": -75.5780, "group": "📍 Comuna 5 — Castilla"},
    {"name": "Doce de Octubre", "lat": 6.2980, "lng": -75.5880, "group": "📍 Comuna 6 — Doce de Octubre"},
    {"name": "Pedregal", "lat": 6.2912, "lng": -75.5850, "group": "📍 Comuna 6 — Doce de Octubre"},
    {"name": "Robledo", "lat": 6.2775, "lng": -75.5909, "group": "📍 Comuna 7 — Robledo"},
    {"name": "Pajarito", "lat": 6.2840, "lng": -75.6012, "group": "📍 Comuna 7 — Robledo"},
    {"name": "Villa Hermosa", "lat": 6.2620, "lng": -75.5530, "group": "📍 Comuna 8 — Villa Hermosa"},
    {"name": "La Ladera", "lat": 6.2570, "lng": -75.5490, "group": "📍 Comuna 8 — Villa Hermosa"},
    {"name": "Buenos Aires", "lat": 6.2530, "lng": -75.5570, "group": "📍 Comuna 9 — Buenos Aires"},
    {"name": "Miraflores", "lat": 6.2490, "lng": -75.5610, "group": "📍 Comuna 9 — Buenos Aires"},
    {"name": "Centro", "lat": 6.2518, "lng": -75.5636, "group": "📍 Comuna 10 — La Candelaria"},
    {"name": "Prado", "lat": 6.2560, "lng": -75.5680, "group": "📍 Comuna 10 — La Candelaria"},
    {"name": "Laureles", "lat": 6.2459, "lng": -75.5964, "group": "📍 Comuna 11 — Laureles-Estadio"},
    {"name": "Estadio", "lat": 6.2510, "lng": -75.5880, "group": "📍 Comuna 11 — Laureles-Estadio"},
    {"name": "La América", "lat": 6.2420, "lng": -75.5880, "group": "📍 Comuna 12 — La América"},
    {"name": "Calasanz", "lat": 6.2380, "lng": -75.5950, "group": "📍 Comuna 12 — La América"},
    {"name": "San Javier", "lat": 6.2355, "lng": -75.6050, "group": "📍 Comuna 13 — San Javier"},
    {"name": "El Salado", "lat": 6.2290, "lng": -75.6120, "group": "📍 Comuna 13 — San Javier"},
    {"name": "El Poblado", "lat": 6.2088, "lng": -75.5678, "group": "📍 Comuna 14 — El Poblado"},
    {"name": "Astorga", "lat": 6.2020, "lng": -75.5750, "group": "📍 Comuna 14 — El Poblado"},
    {"name": "Guayabal", "lat": 6.2107, "lng": -75.5888, "group": "📍 Comuna 15 — Guayabal"},
    {"name": "Tenche", "lat": 6.2050, "lng": -75.5830, "group": "📍 Comuna 15 — Guayabal"},
    {"name": "Belen", "lat": 6.2311, "lng": -75.6038, "group": "📍 Comuna 16 — Belén"},
    {"name": "Los Alpes", "lat": 6.2250, "lng": -75.6100, "group": "📍 Comuna 16 — Belén"},
]


def _float_or_none(val):
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "."))
    except (TypeError, ValueError):
        return None


def routes(request):
    origin = request.GET.get("origin", "")
    destination = request.GET.get("destination", "")
    origin_lat = _float_or_none(request.GET.get("origin_lat"))
    origin_lng = _float_or_none(request.GET.get("origin_lng"))
    dest_lat = _float_or_none(request.GET.get("dest_lat"))
    dest_lng = _float_or_none(request.GET.get("dest_lng"))
    neighborhoods = []
    for nh in NEIGHBORHOODS:
        nhc = dict(nh)
        nhc["lat_str"] = f"{nh['lat']:.6f}"
        nhc["lng_str"] = f"{nh['lng']:.6f}"
        neighborhoods.append(nhc)
    return render(request, "routes/routes.html", {
        "origin": origin,
        "destination": destination,
        "origin_lat": origin_lat or "",
        "origin_lng": origin_lng or "",
        "dest_lat": dest_lat or "",
        "dest_lng": dest_lng or "",
        "neighborhoods": sorted(neighborhoods, key=lambda x: x["group"]),
    })


@csrf_exempt
def api_routes(request):
    # POST: enriquecer rutas ya calculadas por el frontend con datos TomTom
    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"routes": []}, status=400)
        try:
            origin_name = (body.get("origin") or "").strip()
            dest_name = (body.get("destination") or "").strip()
            routes_data = body.get("routes_data")
            if not routes_data:
                return JsonResponse({"routes": []})
            enriched = []
            for r in routes_data:
                try:
                    route = _enrich_with_real_data(
                        origin_name, dest_name,
                        r["dist"], r["time"], r["points"], r["mode"]
                    )
                    if r.get("source") == "estimado":
                        route["source"] = "estimado (sin conexión OSRM)"
                except Exception:
                    logger.warning(
                        "[api_routes] fallback para ruta %s→%s modo=%s",
                        origin_name, dest_name, r.get("mode")
                    )
                    route = {
                        "name": f"{MODE_LABELS.get(r['mode'], '🚗')}: {origin_name} → {dest_name}",
                        "origin": origin_name,
                        "destination": dest_name,
                        "mode": r["mode"],
                        "distance": r["dist"],
                        "time": r["time"],
                        "risk": None,
                        "congestion": None,
                        "speed": None,
                        "incidents": 0,
                        "rain_probability": None,
                        "source": "OSRM (sin TomTom)",
                        "points": r["points"],
                    }
                enriched.append(route)
            order = {"driving": 0, "cycling": 1, "walking": 2}
            enriched.sort(key=lambda x: order.get(x["mode"], 99))
            return JsonResponse({"routes": enriched})
        except Exception as e:
            logger.exception("[api_routes] POST error: %s", e)
            traceback.print_exc(file=sys.stderr)
            return JsonResponse({"routes": [], "error": str(e)}, status=500)

    # GET legacy: sin routes_data, usa OSRM desde el backend
    origin = request.GET.get("origin", "")
    destination = request.GET.get("destination", "")
    origin_lat = _float_or_none(request.GET.get("origin_lat"))
    origin_lng = _float_or_none(request.GET.get("origin_lng"))
    dest_lat = _float_or_none(request.GET.get("dest_lat"))
    dest_lng = _float_or_none(request.GET.get("dest_lng"))
    mode = request.GET.get("mode", "all")
    origin_coords = (origin_lat, origin_lng) if origin_lat is not None and origin_lng is not None else None
    dest_coords = (dest_lat, dest_lng) if dest_lat is not None and dest_lng is not None else None
    routes_result = recommended_routes(
        origin, destination,
        origin_coords=origin_coords, dest_coords=dest_coords,
        mode=mode
    )
    return JsonResponse({"routes": routes_result})
