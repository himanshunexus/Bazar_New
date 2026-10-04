import pytest
from django.core.exceptions import ValidationError

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
