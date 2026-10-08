from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import phone_validator, pincode_validator
from apps.products.models import Product

from .models import Order, OrderGroup, OrderItem, make_group_number, make_order_number


class CheckoutError(ValidationError):
    pass


def _validate_address(data):
    required = ["full_name", "phone", "line1", "city", "pincode"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise CheckoutError(f"Missing delivery details: {', '.join(missing)}")
    phone_validator(data["phone"])
    pincode_validator(data["pincode"])


def _unique_group_number():
    for _ in range(20):
        number = make_group_number()
        if not OrderGroup.objects.filter(group_number=number).exists():
            return number
    raise CheckoutError("Could not allocate an order group number. Please try again.")


def _unique_order_number():
    for _ in range(20):
        number = make_order_number()
        if not Order.objects.filter(order_number=number).exists():
            return number
    raise CheckoutError("Could not allocate an order number. Please try again.")


def place_order(user, cart, address_data, customer_note=""):
    if len(cart) == 0:
        raise CheckoutError("Your cart is empty.")
    _validate_address(address_data)

    product_quantities = {int(product_id): int(qty) for product_id, qty in cart.data.items() if int(qty) > 0}
    if not product_quantities:
        raise CheckoutError("Your cart is empty.")

    with transaction.atomic():
        products = list(
            Product.objects.select_for_update()
            .select_related("shop")
            .filter(id__in=sorted(product_quantities))
            .order_by("id")
        )
        product_map = {product.id: product for product in products}

        grouped = defaultdict(list)
        for product_id, quantity in product_quantities.items():
            product = product_map.get(product_id)
            if not product or not product.is_active or not product.shop.is_active:
                raise CheckoutError("One item in your cart is no longer available.")
            if product.stock < quantity:
                raise CheckoutError(f"{product.name} has only {product.stock} left.")
            grouped[product.shop].append((product, quantity))

        shop_subtotals = {}
        for shop, lines in grouped.items():
            subtotal = sum((product.price * qty for product, qty in lines), Decimal("0.00"))
            if subtotal < shop.min_order_amount:
                raise CheckoutError(f"{shop.name} requires a minimum order of Rs {shop.min_order_amount}.")
            shop_subtotals[shop] = subtotal

        group = OrderGroup.objects.create(
            customer=user,
            group_number=_unique_group_number(),
            delivery_name=address_data["full_name"],
            delivery_phone=address_data["phone"],
            delivery_address_line=", ".join(filter(None, [address_data.get("line1"), address_data.get("line2")])),
            delivery_city=address_data["city"],
            delivery_pincode=address_data["pincode"],
            delivery_latitude=address_data.get("latitude") or None,
            delivery_longitude=address_data.get("longitude") or None,
            payment_method="COD",
        )

        grand_total = Decimal("0.00")
        orders = []
        for shop, lines in grouped.items():
            subtotal = shop_subtotals[shop]
            total = subtotal + shop.delivery_fee
            order = Order.objects.create(
                group=group,
                shop=shop,
                customer=user,
                order_number=_unique_order_number(),
                status=Order.Status.PLACED,
                payment_method="COD",
                payment_status=Order.PaymentStatus.PENDING,
                subtotal=subtotal,
                delivery_fee=shop.delivery_fee,
                total=total,
                customer_note=customer_note,
            )
            orders.append(order)
            grand_total += total
            for product, quantity in lines:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=quantity,
                    line_total=product.price * quantity,
                )
                product.stock -= quantity
                product.save(update_fields=["stock", "updated_at"])

        group.grand_total = grand_total
        group.save(update_fields=["grand_total"])
        transaction.on_commit(cart.clear)
        return group


ALLOWED_TRANSITIONS = {
    Order.Status.PLACED: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.DISPATCHED, Order.Status.OUT_FOR_DELIVERY, Order.Status.CANCELLED},
    Order.Status.DISPATCHED: {Order.Status.OUT_FOR_DELIVERY, Order.Status.DELIVERED},
    Order.Status.OUT_FOR_DELIVERY: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: set(),
    Order.Status.CANCELLED: set(),
}


def transition_order(order, new_status, actor):
    if getattr(actor, "is_seller", False):
        if not hasattr(actor, "shop") or order.shop_id != actor.shop.id:
            raise PermissionDenied("You can update only your own shop orders.")
    elif order.customer_id != actor.id or new_status != Order.Status.CANCELLED or order.status != Order.Status.PLACED:
        raise PermissionDenied("You cannot make this order change.")

    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if new_status not in ALLOWED_TRANSITIONS[locked.status]:
            raise CheckoutError(f"Cannot move order from {locked.status} to {new_status}.")

        if new_status == Order.Status.CANCELLED:
            _restore_stock(locked)
        if new_status == Order.Status.DELIVERED:
            locked.payment_status = Order.PaymentStatus.PAID
            locked.paid_at = timezone.now()
            if locked.delivery_agent_id:
                locked.delivery_agent.is_available = True
                locked.delivery_agent.save(update_fields=["is_available"])
        locked.status = new_status
        locked.save(update_fields=["status", "payment_status", "paid_at", "updated_at"])
        return locked


def _restore_stock(order):
    items = order.items.select_related("product").filter(product__isnull=False).order_by("product_id")
    product_ids = [item.product_id for item in items]
    locked_products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids).order_by("id")}
    for item in items:
        product = locked_products.get(item.product_id)
        if product:
            product.stock += item.quantity
            product.save(update_fields=["stock", "updated_at"])
