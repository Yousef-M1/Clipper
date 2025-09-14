from rest_framework.throttling import UserRateThrottle
from core.models import UserCredits


class PlanBasedThrottle(UserRateThrottle):
    """
    Throttle that adjusts rate limits based on user's subscription plan
    """
    scope_mapping = {
        'free': 'free',
        'pro': 'pro',
        'premium': 'premium'
    }

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            # Get user's plan
            try:
                user_credits = UserCredits.objects.get(user=request.user)
                plan_name = user_credits.plan.name if user_credits.plan else 'free'
            except UserCredits.DoesNotExist:
                plan_name = 'free'

            # Override the scope based on user's plan
            self.scope = self.scope_mapping.get(plan_name, 'free')

        return super().get_cache_key(request, view)


class VideoProcessingThrottle(UserRateThrottle):
    """
    Special throttle for video processing endpoints with plan-based limits
    """
    scope_mapping = {
        'free': 'video_processing_free',
        'pro': 'video_processing_pro',
        'premium': 'video_processing_premium'
    }

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            # Get user's plan
            try:
                user_credits = UserCredits.objects.get(user=request.user)
                plan_name = user_credits.plan.name if user_credits.plan else 'free'
            except UserCredits.DoesNotExist:
                plan_name = 'free'

            # Override the scope based on user's plan
            self.scope = self.scope_mapping.get(plan_name, 'video_processing_free')

        return super().get_cache_key(request, view)


class BurstProtectionThrottle(UserRateThrottle):
    """
    Short-term burst protection to prevent rapid-fire requests
    """
    scope = 'burst'


class PaymentThrottle(UserRateThrottle):
    """
    Special throttle for payment-related endpoints
    """
    scope = 'payment'

    def get_cache_key(self, request, view):
        # Payment endpoints get more restrictive limits
        return super().get_cache_key(request, view)


class AdminBypassThrottle(UserRateThrottle):
    """
    Throttle that bypasses limits for admin users
    """
    def allow_request(self, request, view):
        # Bypass throttling for admin users
        if request.user.is_authenticated and request.user.is_staff:
            return True
        return super().allow_request(request, view)


class WebhookThrottle(UserRateThrottle):
    """
    Special throttle for webhook endpoints (high volume expected)
    """
    scope = 'webhook'

    def get_cache_key(self, request, view):
        # Use IP-based throttling for webhooks since they're not user-authenticated
        return f"webhook_{self.get_ident(request)}"