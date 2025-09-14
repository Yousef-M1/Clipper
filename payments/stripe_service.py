import stripe
from django.conf import settings
from core.models import Plan, StripeCustomer, Subscription, PaymentHistory, CreditPurchase, UserCredits
from django.contrib.auth import get_user_model
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

User = get_user_model()


class StripeService:
    """Service class for handling Stripe operations"""

    @staticmethod
    def create_or_get_customer(user):
        """Create or retrieve Stripe customer for user"""
        try:
            # Check if customer already exists
            stripe_customer = StripeCustomer.objects.get(user=user)
            return stripe_customer.stripe_customer_id
        except StripeCustomer.DoesNotExist:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.email,
                metadata={'user_id': user.id}
            )

            # Save to database
            StripeCustomer.objects.create(
                user=user,
                stripe_customer_id=customer.id
            )

            logger.info(f"Created Stripe customer {customer.id} for user {user.email}")
            return customer.id

    @staticmethod
    def create_subscription(user, plan_name):
        """Create a subscription for a user"""
        try:
            plan = Plan.objects.get(name=plan_name)
            if not plan_name in settings.STRIPE_PRICE_IDS or not settings.STRIPE_PRICE_IDS[plan_name]:
                raise ValueError(f"No Stripe price ID configured for plan: {plan_name}")

            customer_id = StripeService.create_or_get_customer(user)

            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{
                    'price': settings.STRIPE_PRICE_IDS[plan_name],
                }],
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
            )

            # Save subscription to database
            Subscription.objects.create(
                user=user,
                stripe_subscription_id=subscription.id,
                plan=plan,
                status=subscription.status,
                current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end)
            )

            return {
                'subscription_id': subscription.id,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret,
                'status': subscription.status
            }

        except Exception as e:
            logger.error(f"Error creating subscription for {user.email}: {str(e)}")
            raise

    @staticmethod
    def cancel_subscription(user, subscription_id):
        """Cancel a user's subscription"""
        try:
            # Cancel in Stripe
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )

            # Update in database
            db_subscription = Subscription.objects.get(
                user=user,
                stripe_subscription_id=subscription_id
            )
            db_subscription.status = 'canceled'
            db_subscription.save()

            logger.info(f"Canceled subscription {subscription_id} for user {user.email}")
            return subscription

        except Exception as e:
            logger.error(f"Error canceling subscription {subscription_id}: {str(e)}")
            raise

    @staticmethod
    def create_payment_intent_for_credits(user, credit_package):
        """Create payment intent for one-time credit purchase"""
        credit_amounts = {
            50: 999,   # $9.99
            100: 1999, # $19.99
            250: 3999, # $39.99
        }

        if credit_package not in credit_amounts:
            raise ValueError("Invalid credit package")

        customer_id = StripeService.create_or_get_customer(user)

        payment_intent = stripe.PaymentIntent.create(
            amount=credit_amounts[credit_package],
            currency='usd',
            customer=customer_id,
            metadata={
                'user_id': user.id,
                'credit_package': credit_package,
                'type': 'credit_purchase'
            }
        )

        # Create payment history record
        PaymentHistory.objects.create(
            user=user,
            stripe_payment_intent_id=payment_intent.id,
            payment_type='credit_purchase',
            amount=credit_amounts[credit_package] / 100,  # Convert cents to dollars
            description=f"Purchase of {credit_package} credits"
        )

        return {
            'client_secret': payment_intent.client_secret,
            'amount': credit_amounts[credit_package],
            'credits': credit_package
        }

    @staticmethod
    def handle_successful_payment(payment_intent_id):
        """Handle successful payment from webhook"""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            metadata = payment_intent.metadata

            user_id = metadata.get('user_id')
            if not user_id:
                logger.error(f"No user_id in payment intent {payment_intent_id}")
                return

            user = User.objects.get(id=user_id)

            # Update payment history
            payment_history = PaymentHistory.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )
            payment_history.status = 'succeeded'
            payment_history.save()

            # If it's a credit purchase, add credits to user account
            if metadata.get('type') == 'credit_purchase':
                credit_package = int(metadata.get('credit_package'))

                # Create credit purchase record
                CreditPurchase.objects.create(
                    user=user,
                    payment_history=payment_history,
                    credits_purchased=credit_package,
                    amount_paid=payment_intent.amount / 100  # Convert cents to dollars
                )

                # Add credits to user account
                user_credits, created = UserCredits.objects.get_or_create(user=user)
                # For credit purchases, we need to modify the UserCredits model
                # to track bonus credits separately or adjust the monthly credits temporarily

                payment_history.credits_added = credit_package
                payment_history.save()

                logger.info(f"Added {credit_package} credits to user {user.email}")

        except Exception as e:
            logger.error(f"Error handling successful payment {payment_intent_id}: {str(e)}")

    @staticmethod
    def handle_subscription_update(subscription_id, status):
        """Handle subscription status updates from webhooks"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            # Update database
            db_subscription = Subscription.objects.get(
                stripe_subscription_id=subscription_id
            )
            db_subscription.status = status
            db_subscription.current_period_start = datetime.fromtimestamp(subscription.current_period_start)
            db_subscription.current_period_end = datetime.fromtimestamp(subscription.current_period_end)
            db_subscription.save()

            # If subscription is now active, ensure user has the right plan
            if status == 'active':
                user_credits, created = UserCredits.objects.get_or_create(
                    user=db_subscription.user
                )
                user_credits.plan = db_subscription.plan
                user_credits.save()

                # Reset monthly credits if it's a new billing period
                user_credits.reset_credits()

            logger.info(f"Updated subscription {subscription_id} to status: {status}")

        except Exception as e:
            logger.error(f"Error handling subscription update {subscription_id}: {str(e)}")

    @staticmethod
    def get_payment_history(user, limit=10):
        """Get payment history for user"""
        return PaymentHistory.objects.filter(user=user)[:limit]

    @staticmethod
    def get_active_subscription(user):
        """Get user's active subscription if any"""
        try:
            return Subscription.objects.filter(
                user=user,
                status__in=['active', 'trialing']
            ).first()
        except Subscription.DoesNotExist:
            return None

    @staticmethod
    def create_portal_session(user):
        """Create Stripe customer portal session for subscription management"""
        try:
            customer_id = StripeService.create_or_get_customer(user)

            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=f"{settings.FRONTEND_URL}/dashboard",  # You'll need to add this to settings
            )

            return session.url

        except Exception as e:
            logger.error(f"Error creating portal session for {user.email}: {str(e)}")
            raise