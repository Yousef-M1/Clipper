import time
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class WebhookThrottleMiddleware(MiddlewareMixin):
    """
    Middleware to throttle webhook endpoints based on IP address
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        # Only apply to webhook endpoints
        if not request.path.startswith('/api/payments/webhook/'):
            return None

        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Create cache key
        cache_key = f"webhook_throttle_{ip}"

        # Get current request count
        current_time = int(time.time())
        hour_start = current_time - (current_time % 3600)  # Start of current hour

        request_data = cache.get(cache_key, {})
        if not isinstance(request_data, dict):
            request_data = {}

        # Clean old data
        request_data = {k: v for k, v in request_data.items() if k >= hour_start - 3600}

        # Count requests in current hour
        current_hour_requests = sum(count for timestamp, count in request_data.items() if timestamp >= hour_start)

        # Check if limit exceeded (1000 requests per hour for webhooks)
        if current_hour_requests >= 1000:
            logger.warning(f"Webhook throttle limit exceeded for IP {ip}")
            return HttpResponse(
                "Rate limit exceeded. Too many webhook requests.",
                status=429,
                content_type="text/plain"
            )

        # Update request count
        minute_start = current_time - (current_time % 60)  # Current minute
        request_data[minute_start] = request_data.get(minute_start, 0) + 1

        # Save back to cache (expire after 2 hours)
        cache.set(cache_key, request_data, timeout=7200)

        return None


class RateLimitHeaderMiddleware(MiddlewareMixin):
    """
    Middleware to add rate limit headers to responses
    """

    def process_response(self, request, response):
        # Only add headers to API endpoints
        if not request.path.startswith('/api/'):
            return response

        # Get user's plan to determine their limits
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                from core.models import UserCredits
                user_credits = UserCredits.objects.get(user=request.user)
                plan_name = user_credits.plan.name if user_credits.plan else 'free'
            except:
                plan_name = 'free'

            # Define limits based on plan
            plan_limits = {
                'free': 50,
                'pro': 200,
                'premium': 500
            }

            limit = plan_limits.get(plan_name, 50)

            # Add rate limit headers
            response['X-RateLimit-Limit'] = str(limit)
            response['X-RateLimit-Plan'] = plan_name

            # Try to get remaining requests from cache (simplified)
            try:
                from django.core.cache import cache
                from rest_framework.throttling import UserRateThrottle

                throttle = UserRateThrottle()
                throttle.scope = plan_name
                cache_key = throttle.get_cache_key(request, None)
                if cache_key:
                    history = cache.get(cache_key, [])
                    remaining = max(0, limit - len(history))
                    response['X-RateLimit-Remaining'] = str(remaining)
            except:
                # If we can't determine remaining, just set it
                response['X-RateLimit-Remaining'] = str(limit)

        return response