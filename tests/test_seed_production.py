import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.cart.models import Order
from apps.products.models import Product
from apps.shops.models import Shop


@pytest.mark.django_db
def test_seed_production_is_idempotent_and_preserves_product_changes(monkeypatch):
    monkeypatch.setenv("SEED_DEMO_PASSWORD", "test-password")
    call_command("seed_production")
    assert Shop.objects.filter(slug__startswith="demo-").count() == 8
    assert Product.objects.filter(slug__startswith="demo-").count() == 96
    assert Order.objects.filter(order_number__startswith="DEMO-").count() == 400

    product = Product.objects.filter(slug__startswith="demo-").first()
    product.price = "999.99"
    product.stock = 3
    product.save(update_fields=["price", "stock", "updated_at"])
    call_command("seed_production")
    product.refresh_from_db()
    assert str(product.price) == "999.99"
    assert product.stock == 3


@pytest.mark.django_db
def test_seed_dry_run_writes_nothing(monkeypatch):
    monkeypatch.setenv("SEED_DEMO_PASSWORD", "test-password")
    call_command("seed_production", "--dry-run")
    assert Shop.objects.count() == 0


@pytest.mark.django_db
def test_seed_requires_confirmation_for_remote_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@example.invalid:5432/db")
    with pytest.raises(CommandError, match="example.invalid"):
        call_command("seed_production")
