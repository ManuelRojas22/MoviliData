from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from apps.dashboard.services import COMUNAS_PRINCIPALES
from .services import ensure_prediction_history, predicted_congestion


def predictions(request):
    ensure_prediction_history()
    return render(request, "predictions/predictions.html")


def api_predictions(request):
    hour = int(request.GET.get("hour", timezone.now().hour))
    output, alerts_created, model_type, training_source, record_count = predicted_congestion(hour)
    output = [p for p in output if p["zone"] in COMUNAS_PRINCIPALES]
    is_realtime_based = any(p.get("is_realtime_based", False) for p in output)
    return JsonResponse({
        "predictions": output,
        "alerts_created": alerts_created,
        "forecast_hours": [hour % 24, (hour + 1) % 24, (hour + 2) % 24],
        "model_type": model_type,
        "training_source": training_source,
        "record_count": record_count,
        "is_realtime_based": is_realtime_based,
    })
