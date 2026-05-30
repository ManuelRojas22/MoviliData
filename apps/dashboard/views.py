from django.http import JsonResponse
from django.shortcuts import render
from .services import city_summary, bootstrap_data


def landing(request):
    return render(request, "landing/index.html")


def dashboard(request):
    return render(request, "dashboard/dashboard.html", {"boot": bootstrap_data()})


def statistics(request):
    return render(request, "dashboard/statistics.html", {"boot": bootstrap_data()})


def api_dashboard(request):
    return JsonResponse(city_summary())


def api_bootstrap(request):
    return JsonResponse(bootstrap_data())
