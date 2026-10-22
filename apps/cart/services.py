from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import phone_validator, pincode_validator
from apps.products.models import Product
from apps.shops.models import Shop

from .models import Order, OrderGroup, OrderItem, make_group_number, make_order_number


class CheckoutError(ValidationError):
    pass


DELIVERY_RADIUS_KM = 5
NO_RIDER_CANCELLATION_REASON = "No rider was available within 5 minutes. Sorry for the inconvenience. You may contact or visit the shop."


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
    latitude, longitude = address_data.get("latitude"), address_data.get("longitude")
    if latitude in (None, "") or longitude in (None, ""):
        raise CheckoutError("Add your delivery location coordinates so we can confirm the shop is within our 5 km delivery range.")
    try:
        latitude, longitude = float(latitude), float(longitude)
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError
    except (TypeError, ValueError):
        raise CheckoutError("Enter a valid delivery location to check the 5 km delivery range.")

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

        nearby_shop_ids = {
            nearby_shop.pk for nearby_shop in Shop.objects.active().nearby(latitude, longitude, DELIVERY_RADIUS_KM)
        }
        shop_subtotals = {}
        for shop, lines in grouped.items():
            if shop.pk not in nearby_shop_ids:
                raise CheckoutError(f"{shop.name} is outside our 5 km delivery range. Remove its items to continue.")
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
    if getattr(actor, "role", None) == "RIDER":
        if not hasattr(actor, "delivery_agent") or order.delivery_agent_id != actor.delivery_agent.id:
            raise PermissionDenied("You can update only orders assigned to you.")
        if new_status not in {Order.Status.OUT_FOR_DELIVERY, Order.Status.DELIVERED}:
            raise PermissionDenied("Riders can only update delivery progress.")
    elif getattr(actor, "is_seller", False):
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


def cancel_unassigned_orders(now=None, order_id=None):
    """Cancel unpaid orders that have had no rider assigned for five minutes."""
    now = now or timezone.now()
    cutoff = now - timedelta(minutes=5)
    candidates = Order.objects.filter(
        status__in=[Order.Status.PLACED, Order.Status.CONFIRMED],
        delivery_agent__isnull=True,
        created_at__lte=cutoff,
    )
    if order_id is not None:
        candidates = candidates.filter(pk=order_id)

    cancelled = 0
    for candidate_id in candidates.values_list("pk", flat=True).iterator():
        with transaction.atomic():
            order = Order.objects.select_for_update().filter(pk=candidate_id).first()
            if (
                not order
                or order.delivery_agent_id is not None
                or order.status not in {Order.Status.PLACED, Order.Status.CONFIRMED}
                or order.created_at > cutoff
            ):
                continue
            _restore_stock(order)
            order.status = Order.Status.CANCELLED
            order.cancellation_reason = NO_RIDER_CANCELLATION_REASON
            order.save(update_fields=["status", "cancellation_reason", "updated_at"])
            cancelled += 1
    return cancelled


def _restore_stock(order):
    items = order.items.select_related("product").filter(product__isnull=False).order_by("product_id")
    product_ids = [item.product_id for item in items]
    locked_products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids).order_by("id")}
    for item in items:
        product = locked_products.get(item.product_id)
        if product:
            product.stock += item.quantity
            product.save(update_fields=["stock", "updated_at"])
