import pandas as pd
from sklearn.linear_model import LinearRegression
from apps.dashboard.services import demo_points


def build_prediction_model(points):
    history = []
    for hour in range(6, 23):
        for point in points:
            rain = point["rain_probability"]
            peak = 18 if hour in [7, 8, 17, 18, 19] else 0
            congestion = min(98, point["congestion"] + peak + rain * 0.18)
            history.append([hour, rain, point["risk"], congestion])
    df = pd.DataFrame(history, columns=["hour", "rain", "risk", "congestion"])
    model = LinearRegression()
    model.fit(df[["hour", "rain", "risk"]], df["congestion"])
    return model


def predicted_congestion(hour=18):
    points = demo_points()
    model = build_prediction_model(points)
    output = []
    for point in points:
        features = pd.DataFrame([{
            "hour": hour,
            "rain": point["rain_probability"],
            "risk": point["risk"],
        }])
        value = float(model.predict(features)[0])
        output.append({
            "zone": point["name"],
            "lat": point["lat"],
            "lng": point["lng"],
            "predicted_congestion": round(min(99, max(0, value)), 1),
            "rain_probability": point["rain_probability"],
            "confidence": 0.86,
        })
    return output
