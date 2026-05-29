from django.http import JsonResponse
from django.shortcuts import render
from .services import predicted_congestion


def predictions(request):
    return render(request, "predictions/predictions.html")


def api_predictions(request):
    hour = int(request.GET.get("hour", 18))
    return JsonResponse({"predictions": predicted_congestion(hour)})
