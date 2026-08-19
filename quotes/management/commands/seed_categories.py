from django.core.management.base import BaseCommand
from quotes.views import seed_categories


class Command(BaseCommand):
    help = "Seed default memory categories"

    def handle(self, *args, **options):
        seed_categories()
        self.stdout.write(self.style.SUCCESS("Default categories seeded successfully."))
