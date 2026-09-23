import time
import logging
from django.core.management.base import BaseCommand
from quotes.views import dispatch_due_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dispatch Web Push notifications for due memories and reminders"

    def add_arguments(self, parser):
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Run continuously as a background daemon, polling every 60 seconds",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="Polling interval in seconds when running in daemon mode (default: 60)",
        )

    def handle(self, *args, **options):
        is_daemon = options.get("daemon", False)
        interval = max(5, options.get("interval", 60))

        if is_daemon:
            self.stdout.write(
                self.style.SUCCESS(f"[*] Starting Memora Reminder Daemon (polling every {interval}s)... Press Ctrl+C to exit.")
            )
            try:
                while True:
                    result = dispatch_due_reminders()
                    sent = result.get("sent_notifications", 0)
                    due = result.get("due_memories", 0)
                    errors = result.get("errors", 0)
                    if due > 0 or sent > 0 or errors > 0:
                        self.stdout.write(
                            f"[+] Processed: {due} due, {sent} sent, {errors} errors"
                        )
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n[!] Daemon stopped by user."))
        else:
            result = dispatch_due_reminders()
            if result.get("status") == "error":
                self.stderr.write(self.style.ERROR(f"[-] Push failed: {result.get('error')}"))
            else:
                sent = result.get("sent_notifications", 0)
                due = result.get("due_memories", 0)
                errors = result.get("errors", 0)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[+] Reminders dispatched successfully: {due} due, {sent} sent, {errors} errors."
                    )
                )
