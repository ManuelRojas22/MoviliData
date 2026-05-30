from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from .services import predicted_congestion


def predictions(request):
    return render(request, "predictions/predictions.html")


def api_predictions(request):
    hour = int(request.GET.get("hour", timezone.now().hour))
    output, alerts_created, model_type = predicted_congestion(hour)
    return JsonResponse({
        "predictions": output,
        "alerts_created": alerts_created,
        "forecast_hours": [hour % 24, (hour + 1) % 24, (hour + 2) % 24],
        "model_type": model_type,
    })
