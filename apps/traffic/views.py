from django.http import JsonResponse
from django.shortcuts import render
from apps.dashboard.services import demo_points, bootstrap_data


def traffic(request):
    return render(request, "traffic/traffic.html", {"boot": bootstrap_data()})


def api_traffic(request):
    try:
        records = [{
            "zone": p["name"],
            "lat": p["lat"],
            "lng": p["lng"],
            "congestion_level": p["congestion"],
            "average_speed": round(p["speed"], 1),
            "status": "critico" if p["congestion"] >= 75 else "moderado",
            "incidents": p["incidents"],
            "free_flow_speed": p["free_flow_speed"],
            "flow_confidence": p["flow_confidence"],
            "road_closure": p["road_closure"],
            "source": p["source"],
        } for p in demo_points()]
        return JsonResponse({"traffic": records})
    except Exception as e:
        return JsonResponse({"traffic": [], "error": str(e)}, status=200)
