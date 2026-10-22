from decimal import Decimal

import pytest
from django.test import override_settings

from apps.accounts.models import User
from apps.cart.models import DeliveryAgent
from apps.shops.models import Shop


@pytest.mark.django_db
@override_settings(DEFAULT_LAT=28.6139, DEFAULT_LNG=77.2090, DEFAULT_RADIUS_KM=5)
def test_home_defaults_to_configured_location(client, shop, category, monkeypatch):
    from apps.core import views

    monkeypatch.setattr(views, "get_recommendations", lambda *_args: [])
    Shop.objects.create(
        owner=User.objects.create_user("far-home-seller", "far-home@example.com", password="pw", role=User.Role.SELLER),
        category=category,
        name="Far away",
        slug="far-away-home-shop",
        phone="9123456788",
        address="Far away",
        city=shop.city,
        pincode=shop.pincode,
        latitude=Decimal("28.800000"),
        longitude=Decimal("77.209000"),
    )
    response = client.get("/")
    assert response.status_code == 200
    assert [item.name for item in response.context["shops"]] == [shop.name]


@pytest.mark.django_db
def test_shop_map_limits_same_pincode_results_to_radius(client, shop, category):
    Shop.objects.create(
        owner=User.objects.create_user("far-seller", "far@example.com", password="pw", role=User.Role.SELLER),
        category=category,
        name="Far shop",
        slug="far-shop",
        phone="9123456789",
        address="Far away",
        city=shop.city,
        pincode=shop.pincode,
        latitude=Decimal("28.800000"),
        longitude=Decimal("77.209000"),
    )
    response = client.get("/api/shops/", {"pincode": shop.pincode, "lat": shop.latitude, "lng": shop.longitude})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == [shop.name]


@pytest.mark.django_db
def test_rider_location_is_saved_only_for_authenticated_rider(client):
    rider = User.objects.create_user("rider-one", "rider@example.com", password="pw", role=User.Role.RIDER)
    agent = DeliveryAgent.objects.create(user=rider, name="Rider One", phone="9876543212")
    denied = client.post("/cart/rider/location/", {"latitude": "22.3", "longitude": "73.4"})
    assert denied.status_code == 302

    client.force_login(rider)
    response = client.post("/cart/rider/location/", {"latitude": "22.3", "longitude": "73.4"})
    assert response.status_code == 200
    agent.refresh_from_db()
    assert float(agent.latitude) == pytest.approx(22.3)
    assert float(agent.longitude) == pytest.approx(73.4)
    assert agent.location_updated_at is not None


@pytest.mark.django_db
def test_rider_cannot_update_an_unassigned_order(customer, product):
    from apps.cart.models import Order
    from apps.cart.services import place_order, transition_order
    from django.core.exceptions import PermissionDenied

    group = place_order(customer, type("Cart", (), {"data": {str(product.id): 1}, "__len__": lambda self: 1, "clear": lambda self: None})(), {
        "full_name": "Customer", "phone": "9876543211", "line1": "Home", "line2": "", "city": "Delhi", "pincode": "110001",
    })
    rider = User.objects.create_user("rider-two", "rider2@example.com", password="pw", role=User.Role.RIDER)
    DeliveryAgent.objects.create(user=rider, name="Rider Two", phone="9876543213")
    with pytest.raises(PermissionDenied):
        transition_order(group.orders.get(), Order.Status.OUT_FOR_DELIVERY, rider)
