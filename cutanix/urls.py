import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.views import PaymentWebhookView

admin_url = os.getenv("DJANGO_ADMIN_URL", "admin/")

urlpatterns = [
    path(admin_url, admin.site.urls),
    path(
        "payment/callback/",
        PaymentWebhookView.as_view(),
        name="root-payment-callback",
    ),
    path("api/", include("api.urls")),
    path("", include("webapp.urls")),
]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATICFILES_DIRS[0],
    )

    urlpatterns += [
        path(
            "__debug__/",
            include(debug_toolbar.urls),
        ),
    ]
