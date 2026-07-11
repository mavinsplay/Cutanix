from django.urls import re_path

from webapp import views

__all__ = []

app_name = "webapp"

urlpatterns = [
    re_path(
        r"^(?!api/|admin/|static/).*$",
        views.serve_index,
        name="index",
    ),
]
