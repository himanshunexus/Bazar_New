import csv

from django.core.management.base import BaseCommand

from apps.cart.models import OrderItem


class Command(BaseCommand):
    help = "Export order_id,user_id,product_id rows for ML retraining."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        rows = OrderItem.objects.filter(
            product__isnull=False,
            order__status="DELIVERED",
        ).select_related("order", "product").values_list(
            "order_id", "order__customer_id", "product_id"
        )
        with open(options["path"], "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["order_id", "user_id", "product_id"])
            writer.writerows(rows)
        self.stdout.write(self.style.SUCCESS(f"Exported orders to {options['path']}"))
