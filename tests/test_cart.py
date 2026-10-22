import pytest
from django.db import IntegrityError

from apps.cart.models import Order
from apps.cart.services import CheckoutError, cancel_unassigned_orders, place_order, transition_order


class FakeCart:
    def __init__(self, data):
        self.data = data
        self.cleared = False

    def __len__(self):
        return sum(self.data.values())

    def clear(self):
        self.cleared = True


ADDRESS = {
    "full_name": "Customer",
    "phone": "9876543211",
    "line1": "Home",
    "line2": "",
    "city": "Delhi",
    "pincode": "110001",
    "latitude": "28.613900",
    "longitude": "77.209000",
}


@pytest.mark.django_db(transaction=True)
def test_checkout_cod_and_stock(customer, product):
    cart = FakeCart({str(product.id): 2})
    group = place_order(customer, cart, ADDRESS)
    order = group.orders.get()
    product.refresh_from_db()
    assert order.payment_method == "COD"
    assert order.payment_status == "PENDING"
    assert product.stock == 3


@pytest.mark.django_db(transaction=True)
def test_checkout_refuses_insufficient_stock(customer, product):
    cart = FakeCart({str(product.id): 99})
    with pytest.raises(CheckoutError):
        place_order(customer, cart, ADDRESS)
    product.refresh_from_db()
    assert product.stock == 5


@pytest.mark.django_db(transaction=True)
def test_delivered_marks_paid(customer, product):
    group = place_order(customer, FakeCart({str(product.id): 1}), ADDRESS)
    order = group.orders.get()
    order = transition_order(order, Order.Status.CONFIRMED, product.shop.owner)
    order = transition_order(order, Order.Status.OUT_FOR_DELIVERY, product.shop.owner)
    order = transition_order(order, Order.Status.DELIVERED, product.shop.owner)
    assert order.payment_status == Order.PaymentStatus.PAID
    assert order.paid_at is not None


@pytest.mark.django_db(transaction=True)
def test_db_check_rejects_non_cod(customer, product):
    group = place_order(customer, FakeCart({str(product.id): 1}), ADDRESS)
    order = group.orders.get()
    order.payment_method = "CARD"
    with pytest.raises(IntegrityError):
        order.save()


@pytest.mark.django_db(transaction=True)
def test_checkout_rejects_shop_outside_five_kilometres(customer, product, category):
    from apps.accounts.models import User
    from apps.products.models import Product
    from apps.shops.models import Shop

    far_owner = User.objects.create_user("far-seller", "far-seller@example.com", password="pw", role=User.Role.SELLER)
    far_shop = Shop.objects.create(
        owner=far_owner, category=category, name="Far shop", slug="far-checkout-shop",
        phone="9123456781", address="Far away", city="Delhi", pincode="110001",
        latitude="28.800000", longitude="77.209000",
    )
    far_product = Product.objects.create(shop=far_shop, name="Far rice", price="100.00", stock=5, unit_label="1 kg")
    with pytest.raises(CheckoutError, match="outside our 5 km delivery range"):
        place_order(customer, FakeCart({str(far_product.id): 1}), ADDRESS)


@pytest.mark.django_db(transaction=True)
def test_unassigned_order_cancels_after_five_minutes_and_restores_stock(customer, product):
    from datetime import timedelta

    from django.utils import timezone

    group = place_order(customer, FakeCart({str(product.id): 2}), ADDRESS)
    order = group.orders.get()
    product.refresh_from_db()
    assert product.stock == 3

    count = cancel_unassigned_orders(now=order.created_at + timedelta(minutes=5, seconds=1))
    order.refresh_from_db()
    product.refresh_from_db()
    assert count == 1
    assert order.status == Order.Status.CANCELLED
    assert "No rider was available" in order.cancellation_reason
    assert product.stock == 5


@pytest.mark.django_db(transaction=True)
def test_rider_assigned_before_timeout_prevents_auto_cancellation(customer, product, seller):
    from datetime import timedelta

    from apps.cart.models import DeliveryAgent

    group = place_order(customer, FakeCart({str(product.id): 1}), ADDRESS)
    order = group.orders.get()
    agent = DeliveryAgent.objects.create(user=None, shop=product.shop, name="Rider", phone="9123456782")
    order.delivery_agent = agent
    order.save(update_fields=["delivery_agent"])

    assert cancel_unassigned_orders(now=order.created_at + timedelta(minutes=10)) == 0
    order.refresh_from_db()
    assert order.status == Order.Status.PLACED


@pytest.mark.django_db(transaction=True)
def test_order_details_expire_unassigned_order_and_show_customer_message(client, customer, product):
    from datetime import timedelta

    from django.utils import timezone

    group = place_order(customer, FakeCart({str(product.id): 1}), ADDRESS)
    order = group.orders.get()
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(minutes=6))
    client.force_login(customer)

    response = client.get(f"/cart/orders/{order.pk}/")
    assert response.status_code == 200
    assert b"No rider was available within 5 minutes" in response.content
    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
