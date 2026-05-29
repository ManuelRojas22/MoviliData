from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from apps.dashboard.views import landing

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", landing, name="landing"),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.traffic.urls")),
    path("", include("apps.routes.urls")),
    path("", include("apps.predictions.urls")),
    path("", include("apps.alerts.urls")),
    path("", include("apps.maps.urls")),
    path("", include("apps.users.urls")),
    path("pwa/<path:path>", serve, {"document_root": settings.BASE_DIR / "pwa"}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
