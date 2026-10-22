import json
import logging
from pathlib import Path

import cloudinary.uploader
import requests
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.products.models import Product, ProductImage


logger = logging.getLogger(__name__)
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "seed_product_photo_manifest.json"
SEEDED_SHOP_SLUGS = {
    "demo-grocery-kirana", "demo-fruits-vegetables", "demo-bakery", "demo-dairy",
    "demo-snacks-sweets", "demo-stationery", "demo-mobile-accessories", "demo-home-kitchen",
    "satyam-kirana-store", "the-u-mart-limda", "tea-post-parul-university",
    "chhaswala-parul-university", "wfc-food-court-parul", "parul-sevashram-pharmacy",
    "limda-farsan-corner", "hostel-household-mart",
}


def _manifest_key(product):
    return f"{product.shop.slug}|{product.name}"


class Command(BaseCommand):
    help = "Seed or correct distinct, product-matched Unsplash photos for demo catalog items."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show the photo assignments without saving them.")
        parser.add_argument("--limit", type=int, default=0, help="Process at most this many products.")

    def handle(self, *args, **options):
        if not MANIFEST_PATH.exists():
            raise CommandError(f"Product photo manifest is missing: {MANIFEST_PATH}")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        manifest_sources = [entry["source_url"] for entry in manifest.values()]
        if len(manifest_sources) != len(set(manifest_sources)):
            raise CommandError("The Unsplash photo manifest contains duplicate photo sources.")

        products = list(
            Product.objects.filter(shop__slug__in=SEEDED_SHOP_SLUGS)
            .select_related("shop")
            .prefetch_related("images")
            .order_by("shop__slug", "name", "id")
        )
        work = []
        unchanged = 0
        manual_images = 0
        for product in products:
            photo = manifest.get(_manifest_key(product))
            if not photo:
                continue  # Product was added manually to a demo shop, not by the seed data.
            images = list(product.images.all())
            seed_image = next((image for image in images if image.source_url.startswith("https://unsplash.com/")), None)
            if seed_image and seed_image.source_url == photo["source_url"]:
                unchanged += 1
                continue
            if not seed_image and images:
                manual_images += 1  # Keep a seller-uploaded photo intact.
                continue
            work.append((product, photo, seed_image))

        if options["limit"]:
            work = work[:options["limit"]]
        if not work:
            self.stdout.write(f"Product photos are current ({unchanged} unchanged, {manual_images} seller photos preserved).")
            return
        if not options["dry_run"] and not all(settings.CLOUDINARY_STORAGE.get(key) for key in ("CLOUD_NAME", "API_KEY", "API_SECRET")):
            raise CommandError("Cloudinary credentials are required to store seeded product photos.")

        if options["dry_run"]:
            for product, photo, previous in work:
                action = "replace" if previous else "add"
                self.stdout.write(f"{action}: {product.shop.slug}/{product.name} <- {photo['source_url']} ({photo['alt']})")
            self.stdout.write(f"{len(work)} photo(s) ready; {unchanged} already current; {manual_images} seller photo(s) preserved.")
            return

        client = requests.Session()
        client.headers.update({"User-Agent": "BAZAR seeded-catalog image importer/1.0"})
        saved = 0
        failures = []
        for product, photo, previous in work:
            try:
                response = client.get(photo["image_url"], timeout=25)
                response.raise_for_status()
                if len(response.content) > 5 * 1024 * 1024:
                    raise ValueError("image is larger than 5 MB")
                if not response.headers.get("Content-Type", "").startswith("image/"):
                    raise ValueError("photo URL did not return an image")

                old_public_id = getattr(previous.image, "public_id", None) if previous else None
                image = previous or ProductImage(product=product, position=0)
                image.source_url = photo["source_url"]
                image.position = 0
                filename = f"{slugify(product.shop.slug + '-' + product.name)[:150]}-unsplash.jpg"
                image.image = SimpleUploadedFile(filename, response.content, content_type="image/jpeg")
                image.save()
                saved += 1

                if old_public_id:
                    try:
                        cloudinary.uploader.destroy(old_public_id, resource_type="image", type="upload", invalidate=True)
                    except Exception as exc:
                        logger.warning("Old Cloudinary photo cleanup failed for %s: %s", product.name, exc)
                self.stdout.write(self.style.SUCCESS(f"Saved photo for {product.shop.name}: {product.name}"))
            except Exception as exc:
                failures.append(f"{product.shop.slug}/{product.name}: {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"Saved {saved} product-matched Unsplash photos; {unchanged} already current; {manual_images} seller photo(s) preserved."
        ))
        for failure in failures:
            self.stderr.write(self.style.ERROR(failure))
        if failures:
            raise CommandError(f"{len(failures)} seeded product photo(s) could not be saved.")
