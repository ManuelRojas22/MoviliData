import pandas as pd
import numpy as np
from datetime import timedelta
from django.utils import timezone
try:
    from sklearn.ensemble import RandomForestRegressor
except ModuleNotFoundError:
    RandomForestRegressor = None
from django.db import connection
from apps.dashboard.services import current_points, get_weather, get_tomtom_incidents
from apps.alerts.models import MobilityAlert
from apps.traffic.models import TrafficRecord

MIN_TRAINING_RECORDS = 20
MIN_TRAINING_HOURS = 3
REAL_TRAFFIC_SOURCE = "TomTom Traffic API"


def ensure_prediction_history(min_records=MIN_TRAINING_RECORDS):
    """
    Completa el minimo de registros reales para que la pantalla de predicciones
    pueda entrenar el modelo cuando se abre.
    """
    since = timezone.now() - timedelta(days=30)
    current_count = TrafficRecord.objects.filter(
        recorded_at__gte=since,
        source=REAL_TRAFFIC_SOURCE,
    ).count()
    missing = max(0, min_records - current_count)
    if missing == 0:
        return 0, current_count

    now = timezone.now()
    records = []
    for p in current_points():
        if p.get("source") != REAL_TRAFFIC_SOURCE:
            continue
        records.append(TrafficRecord(
            zone=p["name"],
            latitude=p["lat"],
            longitude=p["lng"],
            congestion_level=int(p.get("congestion") or 0),
            average_speed=float(p.get("speed") or 0),
            source=REAL_TRAFFIC_SOURCE,
            recorded_at=now,
        ))
        if len(records) >= missing:
            break

    if records:
        TrafficRecord.objects.bulk_create(records)
    return len(records), current_count + len(records)


def _load_history(days=30):
    since = timezone.now() - timedelta(days=days)
    traffic_qs = TrafficRecord.objects.filter(
        recorded_at__gte=since, source=REAL_TRAFFIC_SOURCE
    ).values(
        "zone", "congestion_level", "average_speed", "recorded_at"
    )
    rows = []
    for t in traffic_qs:
        rows.append({
            "zone": t["zone"],
            "congestion_level": t["congestion_level"],
            "average_speed": float(t["average_speed"]),
            "hour": t["recorded_at"].hour,
            "day_of_week": t["recorded_at"].weekday(),
            "recorded_at": t["recorded_at"],
        })

    weather_rows = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT zone, rain_mm, temperature, recorded_at FROM weather_records "
                "WHERE recorded_at >= %s ORDER BY recorded_at DESC",
                [since],
            )
            for row in cursor.fetchall():
                key = (row[0], row[3].hour)
                if key not in weather_rows:
                    weather_rows[key] = {"rain_mm": float(row[1]), "temperature": float(row[2])}
    except Exception:
        weather_rows = {}

    accident_counts = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT zone, occurred_at FROM accidents WHERE occurred_at >= %s",
                [since],
            )
            for row in cursor.fetchall():
                key = (row[0], row[1].hour)
                accident_counts[key] = accident_counts.get(key, 0) + 1
    except Exception:
        accident_counts = {}

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["rain_mm"] = df.apply(
        lambda r: weather_rows.get((r["zone"], r["hour"]), {}).get("rain_mm", 0),
        axis=1,
    )
    df["temperature"] = df.apply(
        lambda r: weather_rows.get((r["zone"], r["hour"]), {}).get("temperature", 23),
        axis=1,
    )
    df["incident_count"] = df.apply(
        lambda r: accident_counts.get((r["zone"], r["hour"]), 0),
        axis=1,
    )
    return df


def _train_model(df):
    if RandomForestRegressor is None:
        raise RuntimeError("scikit-learn no esta instalado")
    features = ["hour", "day_of_week", "rain_mm", "temperature", "incident_count"]
    X = df[features].copy()
    y = df["congestion_level"].clip(0, 100)
    model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42, n_jobs=1)
    model.fit(X, y)
    r2_score = model.score(X, y)
    return model, features, r2_score


def _has_training_variation(df):
    if df.empty:
        return False
    return df["hour"].nunique() >= MIN_TRAINING_HOURS


def _forecast_for_zone(model, features, zone_name, lat, lng, base_hour, rain_mm, temperature, incident_count, r2_score, precip_prob=0):
    confidence = round(0.70 + max(0, r2_score) * 0.25, 2)
    confidence = max(0.70, min(0.95, confidence))
    results = []
    for offset in range(3):
        h = (base_hour + offset) % 24
        dow = timezone.now().weekday()
        row = pd.DataFrame([{
            "hour": h,
            "day_of_week": dow,
            "rain_mm": rain_mm,
            "temperature": temperature,
            "incident_count": incident_count,
        }])
        pred = float(model.predict(row)[0])
        results.append({
            "hour": h,
            "predicted_congestion": round(max(0, min(99, pred)), 1),
            "rain_probability": precip_prob,
            "confidence": confidence,
        })
    return results


def _fallback_forecast(zone_name, lat, lng, base_hour, rain_mm, temperature, incident_count, precip_prob=0):
    from django.db.models import Avg
    from apps.traffic.models import TrafficRecord
    import datetime
    now = datetime.datetime.now()
    results = []
    for offset in range(3):
        h = (base_hour + offset) % 24
        agg = TrafficRecord.objects.filter(
            zone=zone_name,
            source="TomTom Traffic API",
            recorded_at__hour=h,
            recorded_at__week_day=now.isoweekday(),
        ).aggregate(avg=Avg("congestion_level"))
        base = agg["avg"]
        if base is not None:
            congestion = round(float(base), 1)
        else:
            peak_hours = {7, 8, 9, 17, 18, 19}
            night_hours = set(range(22, 24)) | set(range(0, 6))
            seed = hash(zone_name) % 21
            if h in peak_hours:
                congestion = round(55 + seed, 1)
            elif h in night_hours:
                congestion = round(15 + seed, 1)
            else:
                congestion = round(30 + seed, 1)
        results.append({
            "hour": h,
            "predicted_congestion": congestion,
            "rain_probability": precip_prob,
            "confidence": 0.68,
        })
    return results


def _create_alerts(predictions):
    now = timezone.now()
    created = 0
    try:
        for p in predictions:
            for forecast in p["forecast"]:
                if forecast["predicted_congestion"] > 75:
                    title = f"Prediccion critica: {p['zone']}"
                    exists = MobilityAlert.objects.filter(
                        title=title,
                        created_at__gte=now - timedelta(hours=2),
                    ).exists()
                    if not exists:
                        MobilityAlert.objects.create(
                            title=title,
                            zone=p["zone"],
                            level="alta",
                            description=(
                                f"Prediccion de congestion del {forecast['predicted_congestion']}% "
                                f"a las {forecast['hour']}:00. Confianza {forecast['confidence']:.0%}."
                            ),
                            active=True,
                        )
                        created += 1
    except Exception:
        pass
    return created


def _current_weather():
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT zone, rain_mm, temperature, recorded_at FROM weather_records "
                "ORDER BY recorded_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return float(row[1]), float(row[2])
    except Exception:
        pass
    weather = get_weather()
    if weather:
        return float(weather.get("rain", 0)), float(weather.get("temperature", 23))
    return 1.2, 23


def _current_incidents():
    try:
        since = timezone.now() - timedelta(hours=1)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT zone, COUNT(*) as cnt FROM accidents "
                "WHERE occurred_at >= %s GROUP BY zone",
                [since],
            )
            return {row[0]: row[1] for row in cursor.fetchall()}
    except Exception:
        pass
    return {}


def _live_forecast(zone_name, lat, lng, base_hour, live_congestion, rain_mm, temperature, incident_count, precip_prob=0):
    """
    Genera un forecast de 3 horas usando el dato live de TomTom como ancla.
    - hora 0 → congestión real actual
    - hora +1/+2 → proyección suave basada en tendencia horaria típica
    """
    peak_hours = {7, 8, 9, 17, 18, 19}
    night_hours = set(range(22, 24)) | set(range(0, 6))

    def _hour_factor(h):
        if h in peak_hours:
            return 1.10
        elif h in night_hours:
            return 0.55
        else:
            return 0.85

    current_hour = timezone.now().hour
    current_factor = _hour_factor(current_hour) or 1.0
    base_normalized = live_congestion / max(current_factor, 0.1)
    results = []
    for offset in range(3):
        h = (base_hour + offset) % 24
        if h == current_hour:
            congestion = live_congestion
            confidence = 0.82
        else:
            # Proyectar desde el valor real hacia la tendencia horaria seleccionada.
            congestion = base_normalized * _hour_factor(h)
            congestion += rain_mm * 0.8 + incident_count * 2.5
            confidence = 0.76 if offset == 0 else 0.72
        congestion = round(max(0, min(99, congestion)), 1)
        results.append({
            "hour": h,
            "predicted_congestion": congestion,
            "rain_probability": precip_prob,
            "confidence": confidence,
            "is_realtime_based": True,
        })
    return results


def predicted_congestion(hour=None):
    if hour is None:
        hour = timezone.now().hour

    ensure_prediction_history()
    df = _load_history(days=30)
    rain_mm, temperature = _current_weather()
    weather = get_weather()
    precip_prob = int(weather.get("precipitation_probability", 0) or 0)
    incidents_by_zone = _current_incidents()
    points = current_points()

    # Indexar los datos live por zona para acceso rápido
    live_by_zone = {p["name"]: p for p in points}

    can_train_ml = (
        len(df) >= MIN_TRAINING_RECORDS
        and RandomForestRegressor is not None
        and _has_training_variation(df)
    )

    if can_train_ml:
        # Modo ML: historial suficiente → entrenar RandomForest
        model, features, r2_score = _train_model(df)
        model_type = "ml"
        record_count = len(df)
        training_source = f"{REAL_TRAFFIC_SOURCE} (datos reales)"
        forecast_fn = lambda zn, la, lo, bh, rm, tm, ic: _forecast_for_zone(
            model, features, zn, la, lo, bh, rm, tm, ic, r2_score, precip_prob
        )
    else:
        # Modo live: sin historial suficiente → anclar en dato real actual de TomTom
        model_type = "live"
        record_count = len(df)
        if len(df) >= MIN_TRAINING_RECORDS:
            if RandomForestRegressor is None:
                reason = "scikit-learn no instalado"
            else:
                reason = f"historial horario insuficiente: {df['hour'].nunique()}/{MIN_TRAINING_HOURS} horas"
        else:
            reason = f"acumulando historial: {len(df)}/{MIN_TRAINING_RECORDS} registros"
        training_source = f"{REAL_TRAFFIC_SOURCE} (tiempo real, {reason})"
        forecast_fn = None  # se aplica por zona más abajo

    output = []
    for p in points:
        zone_incidents = incidents_by_zone.get(p["name"], p.get("incidents", 0))

        if forecast_fn is not None:
            # Modo ML
            forecast = forecast_fn(p["name"], p["lat"], p["lng"], hour, rain_mm, temperature, zone_incidents)
        else:
            # Modo live: usar congestion real del punto TomTom como hora 0
            live = live_by_zone.get(p["name"], p)
            live_congestion = live.get("congestion") or 0
            forecast = _live_forecast(
                p["name"], p["lat"], p["lng"], hour,
                live_congestion, rain_mm, temperature, zone_incidents, precip_prob
            )

        output.append({
            "zone": p["name"],
            "lat": p["lat"],
            "lng": p["lng"],
            "forecast": forecast,
            "is_realtime_based": forecast_fn is None,
        })

    alerts_created = _create_alerts(output)
    return output, alerts_created, model_type, training_source, record_count
