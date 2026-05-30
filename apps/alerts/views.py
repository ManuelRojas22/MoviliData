from django.http import JsonResponse
from django.shortcuts import render
from apps.dashboard.services import demo_points, bootstrap_data


def alerts(request):
    return render(request, "alerts/alerts.html", {"boot": bootstrap_data()})


def api_alerts(request):
    alerts_data = [{
        "title": f"Riesgo {p['name']}",
        "zone": p["name"],
        "level": "alta" if p["risk"] > 70 else "media",
        "description": f"Congestion {p['congestion']}% y probabilidad de lluvia {p['rain_probability']}%.",
        "lat": p["lat"],
        "lng": p["lng"],
    } for p in demo_points() if p["risk"] >= 50]
    return JsonResponse({"alerts": alerts_data})
