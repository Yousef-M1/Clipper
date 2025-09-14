import stripe
import json
import logging
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from rest_framework.decorators import throttle_classes
from core.throttling import WebhookThrottle
from .stripe_service import StripeService

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        logger.info(f"Received Stripe webhook event: {event['type']}")

    except ValueError as e:
        logger.error(f"Invalid payload in Stripe webhook: {e}")
        return HttpResponseBadRequest("Invalid payload")

    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature in Stripe webhook: {e}")
        return HttpResponseBadRequest("Invalid signature")

    # Handle the event
    try:
        if event['type'] == 'payment_intent.succeeded':
            handle_payment_succeeded(event['data']['object'])

        elif event['type'] == 'payment_intent.payment_failed':
            handle_payment_failed(event['data']['object'])

        elif event['type'] == 'customer.subscription.created':
            handle_subscription_created(event['data']['object'])

        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])

        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])

        elif event['type'] == 'invoice.payment_succeeded':
            handle_invoice_payment_succeeded(event['data']['object'])

        elif event['type'] == 'invoice.payment_failed':
            handle_invoice_payment_failed(event['data']['object'])

        else:
            logger.info(f"Unhandled Stripe webhook event: {event['type']}")

    except Exception as e:
        logger.error(f"Error handling Stripe webhook {event['type']}: {str(e)}")
        return HttpResponse(status=500)

    return HttpResponse(status=200)


def handle_payment_succeeded(payment_intent):
    """Handle successful payment intent"""
    try:
        logger.info(f"Payment succeeded: {payment_intent['id']}")
        StripeService.handle_successful_payment(payment_intent['id'])

    except Exception as e:
        logger.error(f"Error handling payment success {payment_intent['id']}: {str(e)}")


def handle_payment_failed(payment_intent):
    """Handle failed payment intent"""
    try:
        from core.models import PaymentHistory

        payment_history = PaymentHistory.objects.get(
            stripe_payment_intent_id=payment_intent['id']
        )
        payment_history.status = 'failed'
        payment_history.save()

        logger.info(f"Payment failed: {payment_intent['id']}")

    except PaymentHistory.DoesNotExist:
        logger.warning(f"Payment history not found for failed payment: {payment_intent['id']}")
    except Exception as e:
        logger.error(f"Error handling payment failure {payment_intent['id']}: {str(e)}")


def handle_subscription_created(subscription):
    """Handle subscription creation"""
    try:
        logger.info(f"Subscription created: {subscription['id']}")
        # The subscription is already created in our database when user subscribes
        # This webhook confirms it was processed successfully
        StripeService.handle_subscription_update(subscription['id'], subscription['status'])

    except Exception as e:
        logger.error(f"Error handling subscription creation {subscription['id']}: {str(e)}")


def handle_subscription_updated(subscription):
    """Handle subscription updates"""
    try:
        logger.info(f"Subscription updated: {subscription['id']} - Status: {subscription['status']}")
        StripeService.handle_subscription_update(subscription['id'], subscription['status'])

    except Exception as e:
        logger.error(f"Error handling subscription update {subscription['id']}: {str(e)}")


def handle_subscription_deleted(subscription):
    """Handle subscription deletion/cancellation"""
    try:
        logger.info(f"Subscription deleted: {subscription['id']}")
        StripeService.handle_subscription_update(subscription['id'], 'canceled')

        # Optionally, revert user to free plan
        from core.models import Subscription, Plan, UserCredits
        try:
            db_subscription = Subscription.objects.get(stripe_subscription_id=subscription['id'])

            # Set user to free plan
            free_plan = Plan.objects.get(name='free')
            user_credits, created = UserCredits.objects.get_or_create(user=db_subscription.user)
            user_credits.plan = free_plan
            user_credits.save()

            logger.info(f"Reverted user {db_subscription.user.email} to free plan")

        except (Subscription.DoesNotExist, Plan.DoesNotExist) as e:
            logger.warning(f"Could not revert to free plan for subscription {subscription['id']}: {str(e)}")

    except Exception as e:
        logger.error(f"Error handling subscription deletion {subscription['id']}: {str(e)}")


def handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment (recurring subscriptions)"""
    try:
        subscription_id = invoice['subscription']
        if subscription_id:
            logger.info(f"Invoice payment succeeded for subscription: {subscription_id}")

            # Reset monthly credits for the user
            from core.models import Subscription, UserCredits
            try:
                db_subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
                user_credits, created = UserCredits.objects.get_or_create(user=db_subscription.user)

                # Reset credits for new billing period
                user_credits.reset_credits()
                logger.info(f"Reset monthly credits for user {db_subscription.user.email}")

            except Subscription.DoesNotExist:
                logger.warning(f"Subscription not found in database: {subscription_id}")

        # Record payment in history
        from core.models import PaymentHistory, User
        customer_id = invoice['customer']

        try:
            from core.models import StripeCustomer
            stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)

            PaymentHistory.objects.create(
                user=stripe_customer.user,
                stripe_invoice_id=invoice['id'],
                payment_type='subscription',
                amount=invoice['amount_paid'] / 100,  # Convert cents to dollars
                status='succeeded',
                description=f"Subscription payment - Invoice {invoice['number']}"
            )

        except StripeCustomer.DoesNotExist:
            logger.warning(f"Stripe customer not found: {customer_id}")

    except Exception as e:
        logger.error(f"Error handling invoice payment success {invoice['id']}: {str(e)}")


def handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment"""
    try:
        subscription_id = invoice['subscription']
        if subscription_id:
            logger.warning(f"Invoice payment failed for subscription: {subscription_id}")

            # You might want to notify the user or take other actions
            from core.models import Subscription
            try:
                db_subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
                logger.warning(f"Payment failed for user {db_subscription.user.email}")

                # Optionally send notification email to user
                # send_payment_failure_notification(db_subscription.user)

            except Subscription.DoesNotExist:
                logger.warning(f"Subscription not found in database: {subscription_id}")

        # Record failed payment in history
        from core.models import StripeCustomer, PaymentHistory
        customer_id = invoice['customer']

        try:
            stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)

            PaymentHistory.objects.create(
                user=stripe_customer.user,
                stripe_invoice_id=invoice['id'],
                payment_type='subscription',
                amount=invoice['amount_due'] / 100,  # Convert cents to dollars
                status='failed',
                description=f"Failed subscription payment - Invoice {invoice['number']}"
            )

        except StripeCustomer.DoesNotExist:
            logger.warning(f"Stripe customer not found: {customer_id}")

    except Exception as e:
        logger.error(f"Error handling invoice payment failure {invoice['id']}: {str(e)}")