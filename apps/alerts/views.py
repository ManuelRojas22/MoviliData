from django.http import JsonResponse
from django.shortcuts import render
from apps.dashboard.services import bootstrap_data
from apps.alerts.services import active_alerts


def alerts(request):
    boot = bootstrap_data()
    boot["alerts"] = active_alerts()
    return render(request, "alerts/alerts.html", {"boot": boot})


def api_alerts(request):
    return JsonResponse({"alerts": active_alerts()})
