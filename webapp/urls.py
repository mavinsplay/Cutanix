from django.urls import re_path, path

from webapp import views

__all__ = []

app_name = "webapp"

urlpatterns = [
    path("payment/return/", views.payment_return, name="payment-return"),
    re_path(
        r"^(?!api/|admin/|static/).*$",
        views.serve_index,
        name="index",
    ),
]
