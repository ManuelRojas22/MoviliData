from django.http import JsonResponse
from django.shortcuts import render
from .services import city_summary


def landing(request):
    return render(request, "landing/index.html", {"summary": city_summary()})


def dashboard(request):
    return render(request, "dashboard/dashboard.html")


def statistics(request):
    return render(request, "dashboard/statistics.html")


def api_dashboard(request):
    return JsonResponse(city_summary())
