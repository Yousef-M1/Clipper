from django.urls import path
from . import views, webhooks

urlpatterns = [
    # Subscription management
    path('plans/', views.get_available_plans, name='get-plans'),
    path('subscribe/', views.create_subscription, name='create-subscription'),
    path('cancel-subscription/', views.cancel_subscription, name='cancel-subscription'),

    # Credit purchases
    path('credit-packages/', views.get_credit_packages, name='get-credit-packages'),
    path('purchase-credits/', views.purchase_credits, name='purchase-credits'),

    # Payment and billing info
    path('payment-history/', views.get_payment_history, name='payment-history'),
    path('billing-info/', views.get_billing_info, name='billing-info'),

    # Stripe integration
    path('stripe-config/', views.get_stripe_config, name='stripe-config'),
    path('create-portal-session/', views.create_portal_session, name='create-portal-session'),

    # Webhooks
    path('webhook/stripe/', webhooks.stripe_webhook, name='stripe-webhook'),
]