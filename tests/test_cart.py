import pytest
from django.db import IntegrityError

from apps.cart.models import Order
from apps.cart.services import CheckoutError, place_order, transition_order


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
