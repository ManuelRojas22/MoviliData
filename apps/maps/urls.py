from django.urls import path
from . import views

urlpatterns = [
    path("risk-zones/", views.risk_zones, name="risk_zones"),
    path("comuna/<str:comuna_name>/", views.comuna_detail, name="comuna_detail"),
    path("api/maps", views.api_maps, name="api_maps"),
    path("api/incidents", views.api_incidents, name="api_incidents"),
    path("api/comuna/<str:comuna_name>/", views.api_comuna_detail, name="api_comuna_detail"),
]
