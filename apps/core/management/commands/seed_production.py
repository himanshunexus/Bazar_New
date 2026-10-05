import secrets
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import Address, User
from apps.cart.models import Order, OrderGroup, OrderItem
from apps.products.models import Product
from apps.reviews.models import ProductReview, ShopReview
from apps.shops.models import Shop, ShopCategory


SEED = 20261005
SHOP_SPECS = [
    ("grocery-kirana", "Grocery & Kirana", "🛒", "Namma Daily Needs", "Fresh staples and household essentials"),
    ("fruits-vegetables", "Fruits & Vegetables", "🥦", "Green Basket Farms", "Fresh produce sourced every morning"),
    ("bakery", "Bakery", "🥖", "Oven Fresh Bakehouse", "Breads, cakes and everyday bakes"),
    ("dairy", "Dairy", "🥛", "Pure Dairy Corner", "Fresh milk, curd, paneer and dairy staples"),
    ("snacks-sweets", "Snacks & Sweets", "🍬", "Mithaas & Munchies", "Indian sweets and savoury favourites"),
    ("stationery", "Stationery", "📚", "WriteRight Stationers", "School, office and art supplies"),
    ("mobile-accessories", "Mobile Accessories", "📱", "Connect Mobile Hub", "Everyday mobile accessories and cables"),
    ("home-kitchen", "Home & Kitchen", "🏠", "Ghar Bazaar", "Useful products for every kitchen and home"),
]
PRODUCTS = {
    "grocery-kirana": [("Aashirvaad Atta", "5 kg", 299), ("India Gate Basmati Rice", "5 kg", 649), ("Toor Dal", "1 kg", 165), ("Fortune Sunflower Oil", "1 L", 145), ("Tata Salt", "1 kg", 28), ("Sugar", "1 kg", 48), ("Tata Tea", "500 g", 245), ("Nescafe Classic", "100 g", 275), ("Maggi Noodles", "280 g", 48), ("Moong Dal", "1 kg", 145), ("Besan", "1 kg", 92), ("Red Chilli Powder", "200 g", 78)],
    "fruits-vegetables": [("Banana", "1 dozen",  sixty) for sixty in [60]] + [("Apple", "1 kg", 180), ("Orange", "1 kg", 120), ("Potato", "1 kg", 35), ("Onion", "1 kg", 40), ("Tomato", "1 kg", 45), ("Carrot", "500 g", 35), ("Spinach", "1 bunch", 30), ("Cucumber", "1 kg", 55), ("Mango", "1 kg", 140), ("Lemon", "250 g", 25), ("Green Peas", "500 g", 70)],
    "bakery": [("Whole Wheat Bread", "400 g", 55), ("Milk Bread", "400 g", 50), ("Multigrain Bread", "400 g", 75), ("Butter Croissant", "2 pcs", 110), ("Chocolate Muffin", "2 pcs", 95), ("Veg Puff", "2 pcs", 70), ("Paneer Puff", "2 pcs", 85), ("Chocolate Cake", "500 g", 420), ("Black Forest Pastry", "1 pc", 110), ("Cookies", "250 g", 120), ("Garlic Bread", "1 loaf", 140), ("Rusk", "300 g", 95)],
    "dairy": [("Full Cream Milk", "1 L", 68), ("Toned Milk", "1 L", 58), ("Curd", "500 g", 45), ("Paneer", "200 g", 95), ("Salted Butter", "100 g", 58), ("Cheese Slices", "200 g", 150), ("Fresh Cream", "250 ml", 85), ("Buttermilk", "1 L", 55), ("Lassi", "500 ml", 60), ("Ghee", "500 ml", 350), ("Flavoured Yogurt", "400 g", 110), ("Milkshake", "300 ml", 80)],
    "snacks-sweets": [("Samosa", "4 pcs", 60), ("Kachori", "4 pcs", 70), ("Gulab Jamun", "500 g", 220), ("Rasgulla", "500 g", 210), ("Besan Ladoo", "500 g", 240), ("Kaju Katli", "250 g", 320), ("Bhujia", "400 g", 135), ("Aloo Bhujia", "400 g", 125), ("Namkeen Mix", "400 g", 140), ("Potato Chips", "150 g", 45), ("Peanut Chikki", "200 g", 90), ("Soan Papdi", "250 g", 110)],
    "stationery": [("Classmate Notebook", "172 pages", 75), ("Ball Pens Blue", "5 pcs", 50), ("Gel Pens", "5 pcs", 90), ("HB Pencils", "10 pcs", 45), ("Eraser Pack", "5 pcs", 25), ("Sharpener", "2 pcs", 30), ("A4 Copier Paper", "500 sheets", 320), ("Sticky Notes", "1 pack", 65), ("Sketch Pens", "12 pcs", 120), ("Geometry Box", "1 set", 145), ("Highlighter Set", "4 pcs", 160), ("Whiteboard Marker", "4 pcs", 110)],
    "mobile-accessories": [("Type C Cable", "1 m", 149), ("Lightning Cable", "1 m", 199), ("20W Fast Charger", "1 pc", 699), ("Power Bank", "10000 mAh", 999), ("Tempered Glass", "1 pc", 149), ("Phone Cover", "1 pc", 249), ("Wireless Earbuds", "1 pair", 1299), ("Neckband", "1 pc", 899), ("Car Charger", "1 pc", 399), ("USB C Adapter", "1 pc", 299), ("Mobile Stand", "1 pc", 199), ("Cleaning Kit", "1 set", 120)],
    "home-kitchen": [("Stainless Steel Bottle", "1 L", 299), ("Lunch Box", "1 set", 449), ("Non Stick Pan", "1 pc", 799), ("Glass Storage Jars", "3 pcs", 499), ("Kitchen Towels", "3 pcs", 180), ("Dishwash Liquid", "500 ml", 120), ("Microfiber Cloth", "4 pcs", 150), ("LED Bulb", "9 W", 110), ("Storage Basket", "1 pc", 350), ("Tea Strainer", "1 pc", 80), ("Peeler", "1 pc", 70), ("Spice Box", "1 pc", 399)],
}


class Command(BaseCommand):
    help = "Create reproducible, idempotent demo data in the configured database."

    def add_arguments(self, parser):
        parser.add_argument("--wipe-demo", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **options):
        self._require_confirmation(options["confirm"])
        if options["dry_run"]:
            self.stdout.write("Dry run: no changes written.")
            return
        with transaction.atomic():
            if options["wipe_demo"]:
                self._wipe()
            result = self._seed()
        self.stdout.write(self.style.SUCCESS(f"Seeded demo data: {result['orders']} orders, {result['products']} products."))

    def _require_confirmation(self, confirmed):
        url = settings.DATABASES["default"].get("NAME", "")
        database_url = __import__("os").environ.get("DATABASE_URL", "")
        if not database_url:
            return
        host = urlparse(database_url).hostname or str(url)
        local_hosts = {"localhost", "127.0.0.1", "::1", "db"}
        if host not in local_hosts and not confirmed:
            raise CommandError(f"Refusing seed against database host {host!r}; rerun with --confirm.")

    def _wipe(self):
        demo_users = User.objects.filter(username__startswith="demo_")
        demo_shops = Shop.objects.filter(slug__startswith="demo-")
        OrderItem.objects.filter(order__order_number__startswith="DEMO-").delete()
        Order.objects.filter(order_number__startswith="DEMO-").delete()
        OrderGroup.objects.filter(group_number__startswith="DEMO-").delete()
        ProductReview.objects.filter(user__in=demo_users).delete()
        ShopReview.objects.filter(user__in=demo_users).delete()
        Product.objects.filter(shop__in=demo_shops).delete()
        demo_shops.delete()
        Address.objects.filter(user__in=demo_users).delete()
        demo_users.delete()

    def _seed(self):
        import os

        configured_password = os.getenv("SEED_DEMO_PASSWORD", "").strip()
        demo_password = configured_password or secrets.token_urlsafe(18)
        generated_password = not configured_password
        city = os.getenv("SEED_CITY", "New Delhi")
        pincode = os.getenv("SEED_PINCODE", "110001")
        lat, lng = Decimal(str(settings.DEFAULT_LAT)), Decimal(str(settings.DEFAULT_LNG))
        categories = {}
        for index, (slug, name, icon, _, _) in enumerate(SHOP_SPECS, 1):
            categories[slug] = ShopCategory.objects.update_or_create(
                slug=slug, defaults={"name": name, "icon": icon, "sort_order": index}
            )[0]

        sellers = []
        shops = []
        for index, (key, _, _, name, description) in enumerate(SHOP_SPECS, 1):
            seller, _ = User.objects.get_or_create(
                username=f"demo_seller_{index}",
                defaults={"email": f"demo.seller{index}@example.com", "role": User.Role.SELLER, "phone": f"98100000{index:02d}", "first_name": "Demo"},
            )
            if not seller.has_usable_password():
                seller.set_password(demo_password)
                seller.save(update_fields=["password"])
            sellers.append(seller)
            shop, created = Shop.objects.get_or_create(
                slug=f"demo-{key}",
                defaults={"owner": seller, "category": categories[key], "name": name, "description": description, "phone": seller.phone, "whatsapp_number": seller.phone, "address": f"Demo Market Road {index}", "city": city, "pincode": pincode, "latitude": lat + Decimal(str((index - 4) * 0.005)), "longitude": lng + Decimal(str((index - 4) * 0.004)), "delivery_fee": Decimal("0.00") if index % 2 else Decimal("20.00"), "min_order_amount": Decimal("199.00") if index % 3 == 0 else Decimal("0.00")},
            )
            if not created:
                changed = {}
                for field, value in {"description": description, "city": city, "pincode": pincode}.items():
                    if not getattr(shop, field):
                        changed[field] = value
                if changed:
                    for field, value in changed.items():
                        setattr(shop, field, value)
                    shop.save(update_fields=[*changed, "updated_at"])
            shops.append(shop)

        products = []
        for shop, (key, *_rest) in zip(shops, SHOP_SPECS):
            for index, (name, unit, price) in enumerate(PRODUCTS[key]):
                product, created = Product.objects.get_or_create(
                    shop=shop,
                    slug=f"demo-{slugify(name)}",
                    defaults={"name": name, "category": shop.category.name, "description": f"Demo {name} for everyday use.", "price": Decimal(price), "mrp": Decimal(price) * Decimal("1.10") if index % 3 == 0 else None, "stock": 10 + (index * 7) % 91, "unit_label": unit},
                )
                if created or not product.description:
                    product.description = product.description or f"Demo {name} for everyday use."
                    product.save(update_fields=["description", "updated_at"])
                products.append(product)

        customers = []
        for index in range(1, 4):
            customer, _ = User.objects.get_or_create(
                username=f"demo_customer_{index}",
                defaults={"email": f"demo.customer{index}@example.com", "role": User.Role.CUSTOMER, "phone": f"98200000{index:02d}", "first_name": "Demo"},
            )
            if not customer.has_usable_password():
                customer.set_password(demo_password)
                customer.save(update_fields=["password"])
            customers.append(customer)
            Address.objects.get_or_create(user=customer, label="Home", defaults={"full_name": f"Demo Customer {index}", "phone": customer.phone, "line1": f"Demo Residency, Block {index}", "city": city, "pincode": pincode, "latitude": lat, "longitude": lng, "is_default": True})

        for order_index in range(1, 401):
            shop = shops[(order_index - 1) % len(shops)]
            customer = customers[(order_index - 1) % len(customers)]
            product_offset = shops.index(shop) * 12
            basket = [
                products[product_offset + ((order_index // len(shops)) * 2) % 12],
                products[product_offset + ((order_index // len(shops)) * 2 + 1) % 12],
                products[product_offset + ((order_index // len(shops)) * 2 + 2) % 12],
            ]
            group_number = f"DEMO-{order_index:06d}"
            group, _ = OrderGroup.objects.get_or_create(group_number=group_number, defaults={"customer": customer, "delivery_name": customer.get_full_name() or customer.username, "delivery_phone": customer.phone, "delivery_address_line": f"Demo Residency, Block {shops.index(shop) + 1}", "delivery_city": city, "delivery_pincode": pincode, "delivery_latitude": lat, "delivery_longitude": lng, "payment_method": "COD"})
            order, created = Order.objects.get_or_create(order_number=group_number, defaults={"group": group, "shop": shop, "customer": customer, "status": Order.Status.DELIVERED, "payment_method": "COD", "payment_status": Order.PaymentStatus.PAID, "paid_at": timezone.now() - timedelta(days=order_index % 60), "delivery_fee": shop.delivery_fee})
            if created:
                subtotal = Decimal("0.00")
                for product in basket:
                    quantity = 1 + (order_index % 2)
                    line_total = product.price * quantity
                    OrderItem.objects.create(order=order, product=product, product_name=product.name, unit_price=product.price, quantity=quantity, line_total=line_total)
                    subtotal += line_total
                order.subtotal = subtotal
                order.total = subtotal + shop.delivery_fee
                order.created_at = timezone.now() - timedelta(days=order_index % 60)
                order.save(update_fields=["subtotal", "total", "created_at", "updated_at"])
                group.grand_total = order.total
                group.save(update_fields=["grand_total"])

        for index, customer in enumerate(customers):
            for shop in shops:
                ShopReview.objects.get_or_create(user=customer, shop=shop, defaults={"rating": 4 + (index % 2), "comment": "Reliable demo purchase."})
        for product in products[:24]:
            reviewer = customers[products.index(product) % len(customers)]
            if Order.objects.filter(customer=reviewer, status=Order.Status.DELIVERED, items__product=product).exists():
                ProductReview.objects.get_or_create(user=reviewer, product=product, defaults={"rating": 5, "comment": "Good demo product."})
        if generated_password:
            self.stdout.write(f"Generated demo password once: {demo_password}")
        return {"orders": Order.objects.filter(order_number__startswith="DEMO-").count(), "products": len(products)}
