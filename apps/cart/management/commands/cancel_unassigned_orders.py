from django.core.management.base import BaseCommand

from apps.cart.services import cancel_unassigned_orders


class Command(BaseCommand):
    help = "Cancel orders that have been waiting five minutes without an assigned rider."

    def handle(self, *args, **options):
        count = cancel_unassigned_orders()
        self.stdout.write(self.style.SUCCESS(f"Cancelled {count} orders without an assigned rider."))
