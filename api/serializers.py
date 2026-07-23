from rest_framework import serializers

from analysis.models import AnalysisTask
from users.models import TelegramUser

__all__ = [
    "UserProfileSerializer",
    "AnalysisTaskSerializer",
    "AnalysisResultSerializer",
    "HistorySerializer",
    "PricingSerializer",
    "PaymentCreateSerializer",
]


class UserProfileSerializer(serializers.ModelSerializer):
    is_subscription_active = serializers.BooleanField(read_only=True)
    is_admin = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    admin_url = serializers.SerializerMethodField()
    subscription_tier = serializers.SerializerMethodField()

    def get_is_admin(self, obj):
        from django.conf import settings

        return obj.telegram_id in settings.ADMIN_TELEGRAM_IDS

    def get_subscription_tier(self, obj):
        if obj.subscription_tier:
            return obj.subscription_tier.name
        return None

    def get_photo_url(self, obj):
        url = obj.photo_url
        if not url:
            return ""
        return url

    def get_admin_url(self, obj):
        from django.urls import reverse

        return reverse("admin:index")

    class Meta:
        model = TelegramUser
        fields = (
            "telegram_id",
            "username",
            "first_name",
            "last_name",
            "photo_url",
            "admin_url",
            "subscription_tier",
            "subscription_expires",
            "requests_used",
            "requests_limit",
            "is_subscription_active",
            "is_admin",
            "created_at",
        )


class AnalysisTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisTask
        fields = (
            "task_id",
            "status",
            "input_text",
            "image",
            "result",
            "created_at",
        )
        read_only_fields = (
            "task_id",
            "status",
            "result",
            "created_at",
        )


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisTask
        fields = (
            "task_id",
            "status",
            "result",
            "created_at",
        )


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisTask
        fields = (
            "task_id",
            "input_text",
            "image",
            "status",
            "result",
            "created_at",
        )


class PricingSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    price_rub = serializers.IntegerField()
    period_days = serializers.IntegerField()
    requests_limit = serializers.IntegerField()
    features = serializers.ListField(child=serializers.CharField())
    is_featured = serializers.BooleanField()


class PaymentCreateSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    months = serializers.IntegerField(min_value=1, max_value=12, default=1)
    payment_method = serializers.IntegerField(default=10, required=False)
