from django.urls import path
from . import views

urlpatterns = [
    path("routes/", views.routes, name="routes"),
    path("api/routes", views.api_routes, name="api_routes"),
]
