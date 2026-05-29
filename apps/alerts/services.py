from apps.dashboard.services import demo_points


def active_alerts():
    return [p for p in demo_points() if p["risk"] >= 50]
