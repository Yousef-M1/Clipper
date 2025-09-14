from django.contrib import admin
from core.models import StripeCustomer, Subscription, PaymentHistory, CreditPurchase

@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'stripe_customer_id', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'stripe_customer_id')
    readonly_fields = ('stripe_customer_id', 'created_at', 'updated_at')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'current_period_start', 'current_period_end', 'created_at')
    list_filter = ('status', 'plan', 'created_at')
    search_fields = ('user__email', 'stripe_subscription_id')
    readonly_fields = ('stripe_subscription_id', 'created_at', 'updated_at')

@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'payment_type', 'amount', 'currency', 'status', 'credits_added', 'created_at')
    list_filter = ('payment_type', 'status', 'currency', 'created_at')
    search_fields = ('user__email', 'stripe_payment_intent_id', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CreditPurchase)
class CreditPurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'credits_purchased', 'amount_paid', 'created_at')
    list_filter = ('credits_purchased', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at',)
