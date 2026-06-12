from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("statistics/", views.statistics, name="statistics"),
    path("weather/", views.weather, name="weather"),
    path("api/dashboard", views.api_dashboard, name="api_dashboard"),
    path("api/bootstrap", views.api_bootstrap, name="api_bootstrap"),
    path("api/weather", views.api_weather, name="api_weather"),
    path("api/movibot", views.api_movibot, name="api_movibot"),
]
