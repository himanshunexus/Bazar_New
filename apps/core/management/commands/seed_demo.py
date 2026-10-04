from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.products.models import Product
from apps.shops.models import Shop, ShopCategory


class Command(BaseCommand):
    help = "Create sample BAZAR users, shops and products around DEFAULT_LAT/DEFAULT_LNG."

    @transaction.atomic
    def handle(self, *args, **options):
        customer, _ = User.objects.get_or_create(
            username="demo_customer",
            defaults={"email": "customer@example.com", "role": User.Role.CUSTOMER, "phone": "9876543210"},
        )
        customer.set_password("password123")
        customer.save()

        categories = [
            ShopCategory.objects.get_or_create(name="Grocery", slug="grocery", defaults={"icon": "🛒", "sort_order": 1})[0],
            ShopCategory.objects.get_or_create(name="Pharmacy", slug="pharmacy", defaults={"icon": "💊", "sort_order": 2})[0],
            ShopCategory.objects.get_or_create(name="Bakery", slug="bakery", defaults={"icon": "🥖", "sort_order": 3})[0],
        ]
        products = [
            ("Fresh Mart", categories[0], "Aashirvaad Atta", "5 kg", "299.00"),
            ("Care Pharmacy", categories[1], "Vitamin C Tablets", "30 tabs", "180.00"),
            ("Daily Bakery", categories[2], "Whole Wheat Bread", "400 g", "55.00"),
        ]
        for i, (shop_name, category, product_name, unit, price) in enumerate(products):
            seller, _ = User.objects.get_or_create(
                username=f"seller_{i+1}",
                defaults={"email": f"seller{i+1}@example.com", "role": User.Role.SELLER, "phone": f"98765432{i+11}"},
            )
            seller.set_password("password123")
            seller.save()
            shop, _ = Shop.objects.get_or_create(
                owner=seller,
                defaults={
                    "category": category,
                    "name": shop_name,
                    "slug": shop_name.lower().replace(" ", "-"),
                    "phone": seller.phone,
                    "whatsapp_number": seller.phone,
                    "address": f"Market road {i+1}",
                    "city": "Delhi",
                    "pincode": "110001",
                    "latitude": Decimal(str(settings.DEFAULT_LAT + (i * 0.01))),
                    "longitude": Decimal(str(settings.DEFAULT_LNG + (i * 0.01))),
                    "delivery_fee": Decimal("20.00"),
                },
            )
            Product.objects.get_or_create(
                shop=shop,
                name=product_name,
                defaults={"price": Decimal(price), "stock": 25, "unit_label": unit, "category": category.name},
            )
        self.stdout.write(self.style.SUCCESS("Demo data ready. Login password is password123."))
