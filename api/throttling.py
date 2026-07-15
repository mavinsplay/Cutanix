from rest_framework.throttling import (
    AnonRateThrottle,
    UserRateThrottle,
)

__all__ = [
    "AnalysisBurstThrottle",
    "AnalysisSustainedThrottle",
    "BurstAnonThrottle",
]


class AnalysisBurstThrottle(UserRateThrottle):
    """Short-window limit on LLM analysis requests per user."""

    scope = "analysis_burst"

    def get_cache_key(self, request, view):
        user = request.user
        ident = getattr(user, "telegram_id", None)
        if ident is None:
            ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class AnalysisSustainedThrottle(UserRateThrottle):
    """Daily cap on LLM analysis requests per user."""

    scope = "analysis_sustained"

    def get_cache_key(self, request, view):
        user = request.user
        ident = getattr(user, "telegram_id", None)
        if ident is None:
            ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class BurstAnonThrottle(AnonRateThrottle):
    """Per-IP limit for unauthenticated endpoints."""

    scope = "anon_burst"
