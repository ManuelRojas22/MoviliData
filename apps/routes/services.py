from apps.dashboard.services import route_options


def recommended_routes():
    return sorted(route_options(), key=lambda route: route["risk"])
