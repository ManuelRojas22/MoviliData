from django.http import JsonResponse
from django.shortcuts import render
from .services import recommended_routes
from apps.dashboard.services import NEIGHBORHOODS


def routes(request):
    origin = request.GET.get("origin", "")
    destination = request.GET.get("destination", "")
    return render(request, "routes/routes.html", {
        "origin": origin,
        "destination": destination,
        "neighborhoods": NEIGHBORHOODS,
    })


def api_routes(request):
    origin = request.GET.get("origin", "")
    destination = request.GET.get("destination", "")
    routes_data = recommended_routes(origin, destination)
    return JsonResponse({"routes": routes_data})
