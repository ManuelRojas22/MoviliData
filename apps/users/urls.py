from django.urls import path
from . import views

urlpatterns = [
    path("users/login/", views.login_view, name="login"),
    path("users/register/", views.register_view, name="register"),
    path("users/logout/", views.logout_view, name="logout"),
    path("users/profile/", views.profile, name="profile"),
]
