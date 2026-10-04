import pytest

from apps.accounts.models import User
from apps.products.models import Product
from apps.shops.models import Shop, ShopCategory


@pytest.fixture
def category(db):
    return ShopCategory.objects.create(name="Grocery", slug="grocery")


@pytest.fixture
def seller(db):
    return User.objects.create_user(username="seller", email="seller@example.com", password="pw", role=User.Role.SELLER, phone="9876543210")


@pytest.fixture
def customer(db):
    return User.objects.create_user(username="customer", email="customer@example.com", password="pw", role=User.Role.CUSTOMER, phone="9876543211")


@pytest.fixture
def shop(db, seller, category):
    return Shop.objects.create(
        owner=seller,
        category=category,
        name="Fresh Mart",
        slug="fresh-mart",
        phone="9876543210",
        whatsapp_number="9876543210",
        address="Main road",
        city="Delhi",
        pincode="110001",
        latitude=28.6139,
        longitude=77.2090,
    )


@pytest.fixture
def product(db, shop):
    return Product.objects.create(shop=shop, name="Rice", price="100.00", stock=5, unit_label="1 kg")
