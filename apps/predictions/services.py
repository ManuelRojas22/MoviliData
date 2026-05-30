import pandas as pd
import numpy as np
from datetime import timedelta
from django.utils import timezone
from sklearn.ensemble import RandomForestRegressor
from django.db import connection
from apps.dashboard.services import demo_points, NEIGHBORHOODS, get_weather, get_external_accidents
from apps.alerts.models import MobilityAlert
from apps.traffic.models import TrafficRecord


def _load_history(days=30):
    since = timezone.now() - timedelta(days=days)
    traffic_qs = TrafficRecord.objects.filter(recorded_at__gte=since).values(
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

    accident_counts = {}
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT zone, occurred_at FROM accidents WHERE occurred_at >= %s",
            [since],
        )
        for row in cursor.fetchall():
            key = (row[0], row[1].hour)
            accident_counts[key] = accident_counts.get(key, 0) + 1

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
    features = ["hour", "day_of_week", "rain_mm", "temperature", "incident_count"]
    X = df[features].copy()
    y = df["congestion_level"].clip(0, 100)
    model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42, n_jobs=1)
    model.fit(X, y)
    r2_score = model.score(X, y)
    return model, features, r2_score


def _forecast_for_zone(model, features, zone_name, lat, lng, base_hour, rain_mm, temperature, incident_count, r2_score):
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
            "rain_probability": min(100, int(rain_mm * 18 + 10)),
            "confidence": confidence,
        })
    return results


def _fallback_forecast(zone_name, lat, lng, base_hour, rain_mm, temperature, incident_count):
    results = []
    for offset in range(3):
        h = (base_hour + offset) % 24
        peak = 18 if h in [7, 8, 17, 18, 19] else 0
        congestion = min(98, 40 + peak + rain_mm * 3 + incident_count * 5)
        results.append({
            "hour": h,
            "predicted_congestion": round(congestion, 1),
            "rain_probability": min(100, int(rain_mm * 18 + 10)),
            "confidence": 0.65,
        })
    return results


def _create_alerts(predictions):
    now = timezone.now()
    created = 0
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


def predicted_congestion(hour=None):
    if hour is None:
        hour = timezone.now().hour

    df = _load_history(days=30)
    rain_mm, temperature = _current_weather()
    incidents_by_zone = _current_incidents()
    points = demo_points()

    if len(df) > 20:
        model, features, r2_score = _train_model(df)
        model_type = "ml"
        forecast_fn = lambda zn, la, lo, bh, rm, tm, ic: _forecast_for_zone(
            model, features, zn, la, lo, bh, rm, tm, ic, r2_score
        )
    else:
        model_type = "heuristic"
        forecast_fn = _fallback_forecast

    output = []
    for p in points:
        zone_incidents = incidents_by_zone.get(p["name"], p.get("incidents", 0))
        forecast = forecast_fn(p["name"], p["lat"], p["lng"], hour, rain_mm, temperature, zone_incidents)
        output.append({
            "zone": p["name"],
            "lat": p["lat"],
            "lng": p["lng"],
            "forecast": forecast,
        })

    alerts_created = _create_alerts(output)
    return output, alerts_created, model_type
