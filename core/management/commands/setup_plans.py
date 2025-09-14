from django.core.management.base import BaseCommand
from core.models import Plan


class Command(BaseCommand):
    help = 'Create initial subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'free',
                'monthly_credits': 5,
                'credit_per_clip': 1,
            },
            {
                'name': 'pro',
                'monthly_credits': 100,
                'credit_per_clip': 1,
            },
            {
                'name': 'premium',
                'monthly_credits': 300,
                'credit_per_clip': 1,
            },
        ]

        for plan_data in plans:
            plan, created = Plan.objects.get_or_create(
                name=plan_data['name'],
                defaults={
                    'monthly_credits': plan_data['monthly_credits'],
                    'credit_per_clip': plan_data['credit_per_clip'],
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.name} with {plan.monthly_credits} monthly credits')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Plan {plan.name} already exists')
                )

        self.stdout.write(self.style.SUCCESS('Successfully set up all plans!'))