from django.urls import path
from . import views

urlpatterns = [
    path("risk-zones/", views.risk_zones, name="risk_zones"),
    path("api/maps", views.api_maps, name="api_maps"),
]
