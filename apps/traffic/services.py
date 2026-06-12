from datetime import timedelta
from django.utils import timezone
from apps.dashboard.services import current_points
from apps.traffic.models import TrafficRecord


def traffic_snapshot():
    """Devuelve estado actual del tráfico. Prioriza datos de APIs externas."""
    return current_points()


def traffic_history(hours=24):
    """Devuelve registros históricos reales almacenados en BD."""
    since = timezone.now() - timedelta(hours=hours)
    qs = TrafficRecord.objects.filter(recorded_at__gte=since).order_by("-recorded_at")
    return list(qs.values(
        "zone", "latitude", "longitude",
        "congestion_level", "average_speed", "recorded_at"
    ))


def has_real_history(min_records=20):
    """True si hay suficientes datos históricos reales para ML."""
    return TrafficRecord.objects.count() >= min_records
