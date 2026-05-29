from django.http import JsonResponse
from django.shortcuts import render
from apps.dashboard.services import route_options


def routes(request):
    return render(request, "routes/routes.html")


def api_routes(request):
    return JsonResponse({"routes": route_options()})
