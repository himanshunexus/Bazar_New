import pytest
import cloudinary
import cloudinary.uploader
import json
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import override_settings
from pathlib import Path

from apps.products.models import Product, ProductImage


@pytest.mark.django_db
def test_product_slug_unique_per_shop_bounded(shop):
    first = Product.objects.create(shop=shop, name="Milk", price="40.00", stock=10)
    second = Product.objects.create(shop=shop, name="Milk", price="42.00", stock=10)
    assert first.slug == "milk"
    assert second.slug == "milk-1"


@pytest.mark.django_db
def test_product_image_max_five(product, monkeypatch):
    monkeypatch.setattr(ProductImage, "full_clean", lambda self: None)
    for i in range(5):
        ProductImage.objects.create(product=product, image=f"image-{i}", position=i)
    image = ProductImage(product=product, image="image-6", position=6)
    with pytest.raises(ValidationError):
        image.clean()


@pytest.mark.django_db
def test_seeded_product_photo_dry_run_selects_distinct_unsplash_sources(product, capsys):
    product.shop.slug = "demo-grocery-kirana"
    product.shop.save(update_fields=["slug", "updated_at"])
    product.name = "Aashirvaad Atta"
    product.save(update_fields=["name", "updated_at"])
    Product.objects.create(shop=product.shop, name="India Gate Basmati Rice", price="600.00", stock=8)

    call_command("seed_product_images", dry_run=True, limit=2)

    output = capsys.readouterr().out
    source_urls = [line.split(" <- ", 1)[1].split(" (", 1)[0] for line in output.splitlines() if " <- " in line]
    assert len(source_urls) == 2
    assert all(url.startswith("https://unsplash.com/photos/") for url in source_urls)
    assert len(set(source_urls)) == 2
    assert ProductImage.objects.filter(product__shop=product.shop).count() == 0


def test_seed_photo_manifest_has_unique_unsplash_images():
    manifest_path = Path(__file__).resolve().parents[1] / "apps" / "products" / "seed_product_photo_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = [entry["source_url"] for entry in manifest.values()]
    image_urls = [entry["image_url"].split("?", 1)[0] for entry in manifest.values()]

    assert len(manifest) == 128
    assert len(set(sources)) == len(sources)
    assert len(set(image_urls)) == len(image_urls)
    assert all(source.startswith("https://unsplash.com/photos/") for source in sources)


@pytest.mark.django_db
@override_settings(CLOUDINARY_STORAGE={"CLOUD_NAME": "test-cloud", "API_KEY": "test-key", "API_SECRET": "test-secret"})
def test_seeded_product_photo_uploads_through_cloudinary_field(product, monkeypatch):
    product.shop.slug = "demo-grocery-kirana"
    product.name = "Aashirvaad Atta"
    product.shop.save(update_fields=["slug", "updated_at"])
    product.save(update_fields=["name", "updated_at"])

    old_source = "https://unsplash.com/photos/old-placeholder"
    old_image = cloudinary.CloudinaryResource(
        public_id="seeded/old-rice", format="jpg", version="1", type="upload", resource_type="image"
    )
    ProductImage.objects.create(product=product, image=old_image, source_url=old_source, position=0)

    class PhotoResponse:
        content = b"\xff\xd8\xff\xe0mock-jpeg"
        headers = {"Content-Type": "image/jpeg"}

        def raise_for_status(self):
            pass

    monkeypatch.setattr("requests.Session.get", lambda self, url, timeout: PhotoResponse())
    monkeypatch.setattr(
        cloudinary.uploader,
        "upload_resource",
        lambda uploaded_file, **options: cloudinary.CloudinaryResource(
            public_id="seeded/test-rice", format="jpg", version="1", type="upload", resource_type="image"
        ),
    )
    destroyed = []
    monkeypatch.setattr(cloudinary.uploader, "destroy", lambda public_id, **options: destroyed.append(public_id))

    call_command("seed_product_images", limit=1)

    image = ProductImage.objects.get(product=product)
    assert image.image.public_id == "seeded/test-rice"
    assert image.source_url.startswith("https://unsplash.com/photos/")
    assert image.source_url != old_source
    assert destroyed == ["seeded/old-rice"]
