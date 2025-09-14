from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.db import models
from core.models import Plan, Subscription, PaymentHistory, CreditPurchase
from core.throttling import PlanBasedThrottle, PaymentThrottle, BurstProtectionThrottle
from .stripe_service import StripeService
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def get_available_plans(request):
    """Get all available subscription plans"""
    plans = Plan.objects.all()
    plans_data = []

    for plan in plans:
        plan_data = {
            'name': plan.name,
            'monthly_credits': plan.monthly_credits,
            'credit_per_clip': plan.credit_per_clip,
            'has_stripe_integration': plan.name in settings.STRIPE_PRICE_IDS and settings.STRIPE_PRICE_IDS[plan.name] is not None
        }

        # Add pricing information (you can customize this)
        pricing = {
            'free': {'price': 0, 'description': 'Free plan with limited credits'},
            'pro': {'price': 19.99, 'description': 'Professional plan for regular users'},
            'premium': {'price': 39.99, 'description': 'Premium plan for power users'}
        }

        if plan.name in pricing:
            plan_data.update(pricing[plan.name])

        plans_data.append(plan_data)

    return Response({
        'plans': plans_data,
        'current_plan': request.user.usercredits.plan.name if hasattr(request.user, 'usercredits') and request.user.usercredits.plan else 'free'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([PaymentThrottle, BurstProtectionThrottle])
def create_subscription(request):
    """Create a new subscription for the user"""
    try:
        plan_name = request.data.get('plan_name')

        if not plan_name:
            return Response({'error': 'Plan name is required'}, status=status.HTTP_400_BAD_REQUEST)

        if plan_name == 'free':
            return Response({'error': 'Cannot create subscription for free plan'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already has an active subscription
        active_subscription = StripeService.get_active_subscription(request.user)
        if active_subscription:
            return Response({
                'error': 'User already has an active subscription',
                'current_plan': active_subscription.plan.name
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create subscription
        result = StripeService.create_subscription(request.user, plan_name)

        return Response({
            'message': 'Subscription created successfully',
            'client_secret': result['client_secret'],
            'subscription_id': result['subscription_id'],
            'status': result['status']
        })

    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancel user's current subscription"""
    try:
        active_subscription = StripeService.get_active_subscription(request.user)

        if not active_subscription:
            return Response({'error': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)

        # Cancel subscription
        StripeService.cancel_subscription(request.user, active_subscription.stripe_subscription_id)

        return Response({
            'message': 'Subscription canceled successfully',
            'canceled_plan': active_subscription.plan.name
        })

    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_credit_packages(request):
    """Get available credit packages for one-time purchase"""
    packages = [
        {'credits': 50, 'price': 9.99, 'description': '50 credits for occasional use'},
        {'credits': 100, 'price': 19.99, 'description': '100 credits - most popular'},
        {'credits': 250, 'price': 39.99, 'description': '250 credits - best value'},
    ]

    return Response({
        'packages': packages,
        'current_credits': request.user.usercredits.remaining_credits if hasattr(request.user, 'usercredits') else 0
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([PaymentThrottle, BurstProtectionThrottle])
def purchase_credits(request):
    """Create payment intent for purchasing credits"""
    try:
        credit_package = request.data.get('credits')

        if not credit_package or credit_package not in [50, 100, 250]:
            return Response({'error': 'Invalid credit package'}, status=status.HTTP_400_BAD_REQUEST)

        result = StripeService.create_payment_intent_for_credits(request.user, credit_package)

        return Response({
            'message': 'Payment intent created successfully',
            'client_secret': result['client_secret'],
            'amount': result['amount'],
            'credits': result['credits']
        })

    except Exception as e:
        logger.error(f"Error creating payment intent for credits: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_history(request):
    """Get user's payment history"""
    try:
        limit = int(request.GET.get('limit', 10))
        payments = StripeService.get_payment_history(request.user, limit)

        payments_data = []
        for payment in payments:
            payment_data = {
                'id': payment.id,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'status': payment.status,
                'payment_type': payment.payment_type,
                'description': payment.description,
                'credits_added': payment.credits_added,
                'created_at': payment.created_at,
            }
            payments_data.append(payment_data)

        return Response({
            'payments': payments_data,
            'total_payments': PaymentHistory.objects.filter(user=request.user).count()
        })

    except Exception as e:
        logger.error(f"Error getting payment history: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_billing_info(request):
    """Get comprehensive billing information for user"""
    try:
        user = request.user

        # Get active subscription
        active_subscription = StripeService.get_active_subscription(user)

        # Get credit information
        user_credits = getattr(user, 'usercredits', None)

        # Get recent payments
        recent_payments = StripeService.get_payment_history(user, 5)

        response_data = {
            'subscription': None,
            'credits': {
                'remaining': 0,
                'monthly_allowance': 0,
                'used_this_month': 0,
                'plan': 'free'
            },
            'recent_payments': [],
            'total_spent': 0
        }

        if active_subscription:
            response_data['subscription'] = {
                'plan': active_subscription.plan.name,
                'status': active_subscription.status,
                'current_period_start': active_subscription.current_period_start,
                'current_period_end': active_subscription.current_period_end,
                'monthly_credits': active_subscription.plan.monthly_credits,
                'credit_per_clip': active_subscription.plan.credit_per_clip
            }

        if user_credits:
            response_data['credits'] = {
                'remaining': user_credits.remaining_credits,
                'monthly_allowance': user_credits.plan.monthly_credits if user_credits.plan else 0,
                'used_this_month': user_credits.used_credits,
                'plan': user_credits.plan.name if user_credits.plan else 'free'
            }

        # Recent payments
        for payment in recent_payments:
            response_data['recent_payments'].append({
                'amount': float(payment.amount),
                'status': payment.status,
                'payment_type': payment.payment_type,
                'description': payment.description,
                'created_at': payment.created_at
            })

        # Calculate total spent
        total_spent = PaymentHistory.objects.filter(
            user=user,
            status='succeeded'
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        response_data['total_spent'] = float(total_spent)

        return Response(response_data)

    except Exception as e:
        logger.error(f"Error getting billing info: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_portal_session(request):
    """Create Stripe customer portal session for subscription management"""
    try:
        portal_url = StripeService.create_portal_session(request.user)

        return Response({
            'portal_url': portal_url
        })

    except Exception as e:
        logger.error(f"Error creating portal session: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stripe_config(request):
    """Get Stripe publishable key for frontend"""
    return Response({
        'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
    })
