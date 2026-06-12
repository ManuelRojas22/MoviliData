from django.urls import path
from . import views

urlpatterns = [
    path("traffic/", views.traffic, name="traffic"),
    path("api/traffic", views.api_traffic, name="api_traffic"),
]
