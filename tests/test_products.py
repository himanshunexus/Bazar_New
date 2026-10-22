import pytest
import cloudinary
import cloudinary.uploader
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import override_settings

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
    Product.objects.create(shop=product.shop, name="Wheat Flour", price="90.00", stock=8)

    call_command("seed_product_images", dry_run=True, limit=2)

    output = capsys.readouterr().out
    source_urls = [line.split(" <- ", 1)[1].split(" (", 1)[0] for line in output.splitlines() if " <- " in line]
    assert len(source_urls) == 2
    assert all(url.startswith("https://unsplash.com/photos/") for url in source_urls)
    assert len(set(source_urls)) == 2
    assert ProductImage.objects.filter(product__shop=product.shop).count() == 0


@pytest.mark.django_db
@override_settings(CLOUDINARY_STORAGE={"CLOUD_NAME": "test-cloud", "API_KEY": "test-key", "API_SECRET": "test-secret"})
def test_seeded_product_photo_uploads_through_cloudinary_field(product, monkeypatch):
    product.shop.slug = "demo-grocery-kirana"
    product.shop.save(update_fields=["slug", "updated_at"])

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

    call_command("seed_product_images", limit=1)

    image = ProductImage.objects.get(product=product)
    assert image.image.public_id == "seeded/test-rice"
    assert image.source_url.startswith("https://unsplash.com/photos/")
