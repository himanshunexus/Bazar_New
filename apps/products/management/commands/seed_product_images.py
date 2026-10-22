import json
import re
from pathlib import Path

import requests
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.products.models import Product, ProductImage


CATALOG_PATH = Path(__file__).resolve().parents[2] / "unsplash_seed_photos.json"
SEEDED_SHOP_SLUGS = {
    "demo-grocery-kirana", "demo-fruits-vegetables", "demo-bakery", "demo-dairy",
    "demo-snacks-sweets", "demo-stationery", "demo-mobile-accessories", "demo-home-kitchen",
    "satyam-kirana-store", "the-u-mart-limda", "tea-post-parul-university",
    "chhaswala-parul-university", "wfc-food-court-parul", "parul-sevashram-pharmacy",
    "limda-farsan-corner", "hostel-household-mart",
}


def _photo_groups(product):
    name = product.name.casefold()
    shop_slug = product.shop.slug

    if shop_slug.endswith("pharmacy") or any(word in name for word in ("bandage", "thermometer", "first aid", "sanitizer")):
        return ["pharmacy-medicine"]
    if "stationery" in shop_slug or any(word in name for word in ("notebook", "pen", "pencil", "paper", "eraser", "sharpener", "geometry", "sticky notes", "sketch pens", "marker", "highlighter")):
        return ["school-stationery"]
    if "mobile-accessories" in shop_slug or any(word in name for word in ("cable", "charger", "phone cover", "earbuds", "neckband", "power bank", "tempered glass", "adapter", "mobile stand", "cleaning kit")):
        return ["mobile-phone-accessories"]
    if any(word in name for word in ("bread", "puff", "muffin", "croissant", "cake", "pastry", "cookies", "rusk", "garlic bread")):
        return ["bakery-bread-pastry", "indian-street-food"]
    if "chips" in name:
        return ["snacks-food", "indian-street-food"]
    if any(word in name for word in ("banana", "apple", "orange", "potato", "onion", "tomato", "carrot", "spinach", "cucumber", "mango", "lemon", "peas")):
        return ["fresh-fruits-vegetables", "grocery-food"]
    if any(word in name for word in ("milk", "curd", "yogurt", "paneer", "butter", "cheese", "cream", "buttermilk", "lassi", "ghee")):
        return ["dairy-products", "tea-coffee-drinks"]
    if any(word in name for word in ("noodle", "maggi")):
        return ["indian-street-food", "snacks-food", "rice-grains"]
    if any(word in name for word in ("tea", "coffee", "drink", "milkshake")):
        return ["tea-coffee-drinks", "indian-street-food"]
    if any(word in name for word in ("samosa", "kachori", "gulab", "rasgulla", "ladoo", "katli", "bhujia", "namkeen", "chips", "chikki", "soan papdi", "khaman", "fafda", "sev mamra", "fries", "sandwich", "farsan")):
        return ["indian-street-food", "snacks-food", "bakery-bread-pastry"]
    if any(word in name for word in ("handwash", "detergent", "shampoo", "soap", "sanitizer")):
        return ["personal-care-products", "kitchen-tools-cleaning"]
    if any(word in name for word in ("bottle", "lunch box", "pan", "jars", "towel", "cloth", "bulb", "basket", "strainer", "peeler", "spice box", "dishwash")):
        return ["kitchen-tools-cleaning", "personal-care-products"]
    if shop_slug in {"demo-grocery-kirana", "satyam-kirana-store"}:
        return ["rice-grains", "grocery-food", "tea-coffee-drinks", "snacks-food"]
    if "snacks" in shop_slug or "food-court" in shop_slug or "farsan" in shop_slug:
        return ["snacks-food", "indian-street-food", "bakery-bread-pastry"]
    if "household" in shop_slug or "home-kitchen" in shop_slug:
        return ["kitchen-tools-cleaning", "personal-care-products"]
    return ["grocery-food", "rice-grains", "snacks-food"]


def _tokens(value):
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 2}


ALIASES = {
    "atta": {"wheat", "flour", "grain"}, "maida": {"flour", "wheat"},
    "dal": {"lentil", "legume", "grain", "seed"}, "toor": {"lentil", "legume"},
    "moong": {"lentil", "legume"}, "oil": {"bottle", "liquid"},
    "salt": {"spice", "seasoning", "white"}, "sugar": {"white", "sweet"},
    "noodles": {"noodles", "food", "pasta"}, "maggi": {"noodles", "food"},
    "biscuits": {"cookie", "cracker", "snack"}, "parle": {"cookie", "cracker"},
    "muffin": {"pastry", "cake", "baked"}, "puff": {"pastry", "baked"},
    "farsan": {"snack", "food"}, "sev": {"snack", "food"},
    "bottle": {"bottle", "drinkware"}, "thermometer": {"medicine", "health"},
    "bandage": {"medicine", "health"}, "first": {"medicine", "health"},
    "sanitizer": {"medicine", "health", "bottle"}, "cable": {"phone", "charger", "electronic"},
    "charger": {"phone", "cable", "electronic"}, "earbuds": {"phone", "headphones", "electronic"},
}


def _score(product, photo):
    product_tokens = _tokens(product.name)
    expanded = set(product_tokens)
    for token in product_tokens:
        expanded.update(ALIASES.get(token, ()))
    caption_tokens = _tokens(photo["alt"])
    return len(expanded & caption_tokens)


class Command(BaseCommand):
    help = "Attach distinct, real Unsplash photos to seeded demo products that do not already have images."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report the images that would be assigned without downloading or saving.")
        parser.add_argument("--limit", type=int, default=0, help="Process at most this many products.")

    def handle(self, *args, **options):
        if not CATALOG_PATH.exists():
            raise CommandError(f"Photo catalog is missing: {CATALOG_PATH}")
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        products = list(
            Product.objects.filter(shop__slug__in=SEEDED_SHOP_SLUGS)
            .select_related("shop")
            .prefetch_related("images")
            .order_by("shop__slug", "name", "id")
        )
        existing_products = {product.pk for product in products if product.images.all()}
        pending = [product for product in products if product.pk not in existing_products]
        if options["limit"]:
            pending = pending[:options["limit"]]
        if not pending:
            self.stdout.write("No seeded products need photos.")
            return
        if not options["dry_run"] and not all(settings.CLOUDINARY_STORAGE.get(key) for key in ("CLOUD_NAME", "API_KEY", "API_SECRET")):
            raise CommandError("Cloudinary credentials are required to store seeded product photos.")

        used_sources = set(
            ProductImage.objects.filter(source_url__startswith="https://unsplash.com/")
            .values_list("source_url", flat=True)
        )
        total = 0
        failures = []
        client = requests.Session()
        client.headers.update({"User-Agent": "BAZAR seeded-catalog image importer/1.0"})

        for product in pending:
            categories = _photo_groups(product)
            candidates = []
            seen_urls = set()
            for category in categories:
                for photo in catalog.get(category, []):
                    if photo["url"] in seen_urls or photo["source_url"] in used_sources:
                        continue
                    seen_urls.add(photo["url"])
                    candidates.append(photo)
            if not candidates:
                failures.append(f"{product.shop.slug}/{product.name}: no unique Unsplash image is available")
                continue

            ranked = [photo for _, photo in sorted(
                enumerate(candidates), key=lambda pair: (_score(product, pair[1]), -pair[0]), reverse=True
            )]
            if options["dry_run"]:
                photo = ranked[0]
                self.stdout.write(f"{product.shop.slug}/{product.name} <- {photo['source_url']} ({photo['alt']})")
                used_sources.add(photo["source_url"])
                total += 1
                continue

            saved = False
            last_error = "no usable image candidate"
            for photo in ranked:
                try:
                    response = client.get(photo["url"], timeout=25)
                    response.raise_for_status()
                    if len(response.content) > 5 * 1024 * 1024:
                        raise ValueError("image is larger than 5 MB")
                    content_type = response.headers.get("Content-Type", "")
                    if not content_type.startswith("image/"):
                        raise ValueError(f"unexpected content type {content_type!r}")

                    image = ProductImage(product=product, source_url=photo["source_url"], position=0)
                    filename = f"{slugify(product.shop.slug + '-' + product.name)[:150]}-unsplash.jpg"
                    image.image = SimpleUploadedFile(filename, response.content, content_type="image/jpeg")
                    image.save()
                    used_sources.add(photo["source_url"])
                    total += 1
                    self.stdout.write(self.style.SUCCESS(f"Saved photo for {product.shop.name}: {product.name}"))
                    saved = True
                    break
                except Exception as exc:
                    last_error = str(exc)
            if not saved:
                failures.append(f"{product.shop.slug}/{product.name}: {last_error}")

        self.stdout.write(self.style.SUCCESS(f"Assigned {total} distinct Unsplash photos to {len(existing_products)} products already carrying images were skipped."))
        for failure in failures:
            self.stderr.write(self.style.ERROR(failure))
        if failures and not options["dry_run"]:
            raise CommandError(f"{len(failures)} seeded product photo(s) could not be saved.")
