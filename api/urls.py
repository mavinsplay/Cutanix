from django.urls import path

from api import views

__all__ = []

app_name = "api"

urlpatterns = [
    path(
        "user/profile/",
        views.ProfileView.as_view(),
        name="profile",
    ),
    path(
        "analysis/",
        views.AnalysisCreateView.as_view(),
        name="analysis-create",
    ),
    path(
        "analysis/<uuid:task_id>/",
        views.AnalysisStatusView.as_view(),
        name="analysis-status",
    ),
    path(
        "history/",
        views.HistoryView.as_view(),
        name="history",
    ),
    path(
        "pricing/",
        views.PricingView.as_view(),
        name="pricing",
    ),
    path(
        "payment/create/",
        views.PaymentCreateView.as_view(),
        name="payment-create",
    ),
    path(
        "payment/webhook/",
        views.PaymentWebhookView.as_view(),
        name="payment-webhook",
    ),
]
