from django.conf import settings
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

    def get_is_admin(self, obj):
        return obj.telegram_id in settings.ADMIN_TELEGRAM_IDS

    class Meta:
        model = TelegramUser
        fields = (
            "telegram_id",
            "username",
            "first_name",
            "last_name",
            "photo_url",
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
    tier = serializers.CharField()
    period_days = serializers.IntegerField()
    price_kopeks = serializers.IntegerField()
    price_rub = serializers.FloatField()
    features = serializers.ListField(child=serializers.CharField())
    is_featured = serializers.BooleanField()


class PaymentCreateSerializer(serializers.Serializer):
    tier = serializers.ChoiceField(choices=["pro", "ultra"])
    period_days = serializers.ChoiceField(choices=[30, 60, 90])
