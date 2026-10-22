from decimal import Decimal
import os
import secrets

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import User
from apps.products.models import Product
from apps.shops.models import Shop, ShopCategory


BASE_LATITUDE = Decimal("22.2887")
BASE_LONGITUDE = Decimal("73.3634")
PINCODE = "391760"
CITY = "Limda, Waghodia"
# Store names follow current public listings; locations and inventory are demo approximations.

SHOP_SPECS = [
    {
        "slug": "satyam-kirana-store",
        "category": ("Grocery & Kirana", "🛒", 1),
        "name": "Satyam Kirana Store",
        "description": "Local shop listed near Parul University. Catalogue below is sample data; confirm inventory and prices with the shop.",
        "address": "Near Parul University, Limda, Waghodia, Vadodara 391760",
        "products": [
            ("Maggi Masala Noodles", "70 g", "15.00", 100),
            ("Britannia Bread", "400 g", "45.00", 40),
            ("Tata Salt", "1 kg", "28.00", 30),
            ("Parle-G Biscuits", "800 g", "85.00", 35),
        ],
    },
    {
        "slug": "the-u-mart-limda",
        "category": ("Grocery & Kirana", "🛒", 2),
        "name": "The U Mart",
        "description": "Public listing places this store at Limda Stand near Parul Hospital. Catalogue below is sample data; confirm inventory and prices with the shop.",
        "address": "Shreeji Residency Complex, Limda Stand, near Parul Hospital, Waghodia 391760",
        "products": [
            ("Banana", "1 dozen", "55.00", 50),
            ("Apple", "1 kg", "160.00", 25),
            ("Tomato", "1 kg", "40.00", 35),
            ("Onion", "1 kg", "38.00", 35),
        ],
    },
    {
        "slug": "tea-post-parul-university",
        "category": ("Bakery & Cafe", "🥐", 3),
        "name": "Tea Post",
        "description": "Public business listing at Parul University, Limda. Catalogue below is sample data; confirm inventory and prices with the shop.",
        "address": "Parul University, Limda, Waghodia, Vadodara 391760",
        "products": [
            ("Veg Puff", "1 piece", "25.00", 60),
            ("Chocolate Muffin", "1 piece", "45.00", 45),
            ("Cold Coffee", "300 ml", "70.00", 45),
            ("Veg Grilled Sandwich", "1 plate", "90.00", 30),
        ],
    },
    {
        "slug": "chhaswala-parul-university",
        "category": ("Dairy & Cold Drinks", "🥛", 4),
        "name": "Chhaswala",
        "description": "Public business listing near Parul University. Catalogue below is sample data; confirm inventory and prices with the shop.",
        "address": "Near Parul University, Limda, Waghodia, Vadodara 391760",
        "products": [
            ("Amul Taaza Milk", "1 litre", "60.00", 60),
            ("Amul Masti Curd", "400 g", "35.00", 40),
            ("Amul Buttermilk", "200 ml", "15.00", 80),
            ("Amul Cheese Slices", "200 g", "145.00", 25),
        ],
    },
    {
        "slug": "wfc-food-court-parul",
        "category": ("Food & Dining", "🍽️", 5),
        "name": "WFC Food Court",
        "description": "Public listing near Parul University. Catalogue below is sample data; confirm inventory and prices with the business.",
        "address": "Near Parul University, Waghodia, Vadodara 391760",
        "products": [
            ("Tea", "1 cup", "20.00", 80),
            ("Veg Sandwich", "1 plate", "90.00", 30),
            ("French Fries", "1 plate", "80.00", 35),
            ("Cold Coffee", "300 ml", "70.00", 30),
        ],
    },
    {
        "slug": "parul-sevashram-pharmacy",
        "category": ("Health & Personal Care", "🩹", 6),
        "name": "Parul Sevashram Pharmacy",
        "description": "Pharmacy listed at Parul Sevashram Hospital, Limda. Catalogue below is sample data; confirm inventory and prices with the pharmacy.",
        "address": "Parul Sevashram Hospital, Limda, Waghodia, Vadodara 391760",
        "products": [
            ("Basic First Aid Kit", "1 kit", "199.00", 12),
            ("Adhesive Bandages", "1 pack", "45.00", 20),
            ("Digital Thermometer", "1 piece", "160.00", 10),
            ("Hand Sanitizer", "100 ml", "55.00", 20),
        ],
    },
    {
        "slug": "limda-farsan-corner",
        "category": ("Farsan & Snacks", "🍘", 7),
        "name": "Limda Farsan Corner",
        "description": "Fresh Gujarati farsan, namkeen and evening snacks.",
        "address": "Limda Chowk, Waghodia",
        "products": [
            ("Khaman", "250 g", "60.00", 35),
            ("Samosa", "4 pieces", "50.00", 60),
            ("Fafda", "250 g", "75.00", 35),
            ("Sev Mamra", "250 g", "55.00", 40),
        ],
    },
    {
        "slug": "hostel-household-mart",
        "category": ("Home & Personal Care", "🏠", 8),
        "name": "Hostel Household Mart",
        "description": "Personal care, cleaning supplies and useful hostel essentials.",
        "address": "Parul Hostel Road, Limda",
        "products": [
            ("Dettol Handwash", "250 ml", "85.00", 35),
            ("Laundry Detergent", "1 kg", "110.00", 30),
            ("Shampoo Sachets", "10 pieces", "35.00", 50),
            ("Stainless Steel Bottle", "1 litre", "249.00", 25),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed idempotent shops and student-focused products around Parul University (391760)."

    @transaction.atomic
    def handle(self, *args, **options):
        shop_count = 0
        product_count = 0
        configured_password = os.getenv("SEED_DEMO_PASSWORD", "").strip()
        password = configured_password or secrets.token_urlsafe(18)
        generated_password = not configured_password

        for index, spec in enumerate(SHOP_SPECS, start=1):
            category_name, icon, sort_order = spec["category"]
            category, _ = ShopCategory.objects.update_or_create(
                slug=slugify(category_name),
                defaults={"name": category_name, "icon": icon, "sort_order": sort_order},
            )
            seller, created = User.objects.get_or_create(
                username=f"parul_seller_{index}",
                defaults={
                    "email": f"parul.seller{index}@example.com",
                    "role": User.Role.SELLER,
                    "phone": f"982500{index:04d}",
                    "first_name": "Parul",
                    "last_name": "Seller",
                },
            )
            if created or not seller.has_usable_password():
                seller.set_password(password)
                seller.save(update_fields=["password"])
            shop, _ = Shop.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "owner": seller,
                    "category": category,
                    "name": spec["name"],
                    "description": spec["description"],
                    "phone": seller.phone,
                    "whatsapp_number": seller.phone,
                    "address": spec["address"],
                    "city": CITY,
                    "pincode": PINCODE,
                    "latitude": BASE_LATITUDE + Decimal(index - 1) * Decimal("0.0011"),
                    "longitude": BASE_LONGITUDE + Decimal(index - 1) * Decimal("0.0009"),
                    "opening_time": "07:00",
                    "closing_time": "23:59",
                    "delivery_fee": Decimal("20.00"),
                    "min_order_amount": Decimal("0.00"),
                    "is_active": True,
                },
            )
            shop_count += 1

            for name, unit_label, price, stock in spec["products"]:
                Product.objects.update_or_create(
                    shop=shop,
                    name=name,
                    defaults={
                        "category": category_name,
                        "description": f"{name} available near Parul University.",
                        "price": Decimal(price),
                        "mrp": Decimal(price),
                        "stock": stock,
                        "unit_label": unit_label,
                        "is_active": True,
                    },
                )
                product_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Parul University data ready: {shop_count} shops and {product_count} products at {PINCODE}."
            )
        )
        if generated_password:
            self.stdout.write(f"Generated shop-owner demo password once (all new sellers): {password}")
