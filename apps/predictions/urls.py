from django.urls import path
from . import views

urlpatterns = [
    path("predictions/", views.predictions, name="predictions"),
    path("api/predictions", views.api_predictions, name="api_predictions"),
]
