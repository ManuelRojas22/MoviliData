from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("statistics/", views.statistics, name="statistics"),
    path("api/dashboard", views.api_dashboard, name="api_dashboard"),
]
