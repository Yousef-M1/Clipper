from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import UserCredits, Plan
import requests
import time

User = get_user_model()


class Command(BaseCommand):
    help = 'Test rate limiting functionality'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='http://localhost:8000', help='API host')
        parser.add_argument('--email', required=True, help='User email to test with')

    def handle(self, *args, **options):
        host = options['host']
        email = options['email']

        try:
            user = User.objects.get(email=email)
            token = user.auth_token.key if hasattr(user, 'auth_token') else None

            if not token:
                self.stdout.write(self.style.ERROR(f'No auth token found for user {email}'))
                return

            # Test general API rate limiting
            self.stdout.write(f'Testing rate limits for user: {email}')

            headers = {'Authorization': f'Token {token}'}

            # Make rapid requests to test rate limiting
            for i in range(5):
                response = requests.get(f'{host}/api/clipper/dashboard/summary/', headers=headers)

                # Print rate limit headers
                limit = response.headers.get('X-RateLimit-Limit', 'Unknown')
                remaining = response.headers.get('X-RateLimit-Remaining', 'Unknown')
                plan = response.headers.get('X-RateLimit-Plan', 'Unknown')

                self.stdout.write(
                    f'Request {i+1}: Status {response.status_code} | '
                    f'Plan: {plan} | Limit: {limit} | Remaining: {remaining}'
                )

                if response.status_code == 429:
                    self.stdout.write(self.style.WARNING('Rate limit hit!'))
                    break

                time.sleep(0.1)  # Small delay

            self.stdout.write(self.style.SUCCESS('Rate limit testing completed'))

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {email} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))