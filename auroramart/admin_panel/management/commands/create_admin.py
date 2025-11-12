from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates the admin superuser with predefined credentials'

    def handle(self, *args, **options):
        username = 'admin'
        password = 'P@55W0RD'
        email = 'admin@auroramart.com'

        # Remove any legacy admin accounts that stored credentials in plain text fields
        legacy_usernames = ['admin_user', 'admin_password']
        deleted_count, _ = User.objects.filter(username__in=legacy_usernames).delete()
        if deleted_count:
            self.stdout.write(
                self.style.WARNING(
                    f'Removed {deleted_count} legacy admin credential record(s).'
                )
            )

        # Always recreate the canonical admin account to guarantee the expected credentials
        User.objects.filter(username=username).delete()
        self.stdout.write(
            self.style.WARNING(f'Removed existing admin account "{username}" (if it existed).')
        )

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created admin superuser:\n'
                f'  Username: {username}\n'
                f'  Password: {password}\n'
                f'  Email: {email}'
            )
        )
