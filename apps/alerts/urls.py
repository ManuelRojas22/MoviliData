from django.urls import path
from . import views

urlpatterns = [
    path("alerts/", views.alerts, name="alerts"),
    path("api/alerts", views.api_alerts, name="api_alerts"),
]
