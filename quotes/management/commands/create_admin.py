import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Create or promote an admin user (options: --handle, --pin)"

    def add_arguments(self, parser):
        parser.add_argument("--handle", type=str, help="Vault handle for admin account")
        parser.add_argument("--pin", type=str, help="6-digit PIN for admin account")

    def handle(self, *args, **options):
        handle = (options.get("handle") or os.environ.get("ADMIN_HANDLE") or "admin").strip().lstrip("@").lower()
        pin = (options.get("pin") or os.environ.get("ADMIN_PIN") or "000000").strip()

        if User.objects.filter(username=handle).exists():
            user = User.objects.get(username=handle)
            user.is_staff = True
            user.is_superuser = True
            user.set_password(pin)
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"Existing user @{handle} successfully promoted to admin with updated PIN."
            ))
        else:
            User.objects.create_superuser(username=handle, password=pin)
            self.stdout.write(self.style.SUCCESS(
                f"Admin @{handle} created successfully with PIN {pin}."
            ))
