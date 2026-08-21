import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Create an admin superuser from environment variables (ADMIN_HANDLE, ADMIN_PIN)"

    def handle(self, *args, **options):
        handle = os.environ.get("ADMIN_HANDLE", "admin")
        pin = os.environ.get("ADMIN_PIN", "000000")

        if User.objects.filter(username=handle).exists():
            user = User.objects.get(username=handle)
            if not user.is_superuser:
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Existing user @{handle} promoted to admin."
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Admin @{handle} already exists."
                ))
        else:
            User.objects.create_superuser(username=handle, password=pin)
            self.stdout.write(self.style.SUCCESS(
                f"Admin @{handle} created successfully."
            ))
