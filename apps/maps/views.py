from django.http import JsonResponse
from django.shortcuts import render
from apps.maps.services import map_statistics_payload


def risk_zones(request):
    return render(request, "maps/risk-zones.html", {"maps_data": map_statistics_payload()})


def api_maps(request):
    return JsonResponse(map_statistics_payload())
