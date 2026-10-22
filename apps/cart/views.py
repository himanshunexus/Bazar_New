from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.core.validators import RegexValidator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_http_methods

from apps.core.decorators import seller_required
from apps.products.models import Product

from .cart import Cart
from .forms import CheckoutForm
from .models import DeliveryAgent, Order
from .services import CheckoutError, place_order, transition_order

phone_validator = RegexValidator(r"^\d{10}$", "Enter a 10-digit mobile number.")


def detail(request):
    cart = Cart(request)
    return render(request, "cart/detail.html", {"cart": cart, "groups": cart.grouped_by_shop()})


@require_http_methods(["POST"])
def add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True, shop__is_active=True)
    Cart(request).add(product.id, request.POST.get("quantity", 1))
    if request.htmx:
        cart = Cart(request)
        return render(request, "cart/_summary.html", {"cart": cart})
    return redirect("cart:detail")


@require_http_methods(["POST"])
def update(request, product_id):
    Cart(request).update(product_id, request.POST.get("quantity", 1))
    return redirect("cart:detail")


@require_http_methods(["POST"])
def remove(request, product_id):
    Cart(request).remove(product_id)
    return redirect("cart:detail")


@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    cart = Cart(request)
    initial = {}
    default_address = request.user.addresses.filter(is_default=True).first()
    if default_address:
        initial = {
            "full_name": default_address.full_name,
            "phone": default_address.phone,
            "line1": default_address.line1,
            "line2": default_address.line2,
            "city": default_address.city,
            "pincode": default_address.pincode,
            "latitude": default_address.latitude,
            "longitude": default_address.longitude,
        }
    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            group = place_order(request.user, cart, form.cleaned_data, form.cleaned_data.get("customer_note", ""))
        except CheckoutError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Pay in cash when your order arrives.")
            return redirect("cart:confirmation", group_id=group.id)
    return render(request, "cart/checkout.html", {"form": form, "cart": cart, "groups": cart.grouped_by_shop()})


@login_required
def confirmation(request, group_id):
    group = get_object_or_404(request.user.order_groups.prefetch_related("orders__shop"), pk=group_id)
    return render(request, "cart/confirmation.html", {"group": group})


@login_required
def order_history(request):
    orders = request.user.orders.select_related("shop").prefetch_related("items").all()
    return render(request, "cart/history.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        request.user.orders.select_related("shop", "delivery_agent").prefetch_related("items"), pk=pk
    )
    return render(request, "cart/order_detail.html", {"order": order})


@login_required
def track_order(request, pk):
    order = get_object_or_404(
        request.user.orders.select_related("shop", "delivery_agent", "group").prefetch_related("items"), pk=pk
    )
    steps = [
        (Order.Status.PLACED, "Order placed", "We received your order."),
        (Order.Status.CONFIRMED, "Preparing your order", "The shop is confirming and packing your items."),
        (Order.Status.DISPATCHED, "Ready to ship", "A delivery partner has been assigned and picked up your order."),
        (Order.Status.OUT_FOR_DELIVERY, "On the way", "Your delivery partner is heading to your address."),
        (Order.Status.DELIVERED, "Delivered", "Your order has reached you."),
    ]
    progress = {status: index for index, (status, _label, _description) in enumerate(steps)}
    current_index = progress.get(order.status, -1)
    timeline = [
        {"label": label, "description": description, "complete": index <= current_index, "current": index == current_index}
        for index, (_status, label, description) in enumerate(steps)
    ]
    return render(request, "cart/order_tracking.html", {
        "order": order,
        "timeline": timeline,
        "cancelled": order.status == Order.Status.CANCELLED,
    })


@login_required
@require_http_methods(["POST"])
def reorder(request, pk):
    order = get_object_or_404(request.user.orders.prefetch_related("items__product"), pk=pk)
    cart = Cart(request)
    for item in order.items.all():
        if item.product and item.product.is_active and item.product.stock > 0:
            cart.add(item.product_id, min(item.quantity, item.product.stock))
    messages.success(request, "Available items from this order were added to your cart.")
    return redirect("cart:detail")


@seller_required
def seller_orders(request):
    orders = request.user.shop.orders.prefetch_related("items").select_related("customer", "delivery_agent").all()
    delivery_agents = DeliveryAgent.objects.filter(is_available=True).filter(Q(shop=request.user.shop) | Q(shop__isnull=True))
    return render(request, "cart/seller_orders.html", {"orders": orders, "delivery_agents": delivery_agents})


@seller_required
@require_http_methods(["GET", "POST"])
def seller_staff(request):
    issued_password = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            name = (request.POST.get("name") or "").strip()
            phone = (request.POST.get("phone") or "").strip()
            vehicle = (request.POST.get("vehicle_number") or "").strip()
            try:
                phone_validator(phone)
                if not name:
                    raise ValueError("Enter the rider's name.")
                with transaction.atomic():
                    agent = DeliveryAgent.objects.filter(phone=phone).first()
                    if agent and agent.shop_id not in {None, request.user.shop.pk}:
                        raise ValueError("This delivery partner already belongs to another shop.")
                    user = agent.user if agent else None
                    username = f"rider_{phone}"
                    if user is None:
                        user = request.user.__class__.objects.filter(username=username).first()
                        if user and user.role != "RIDER":
                            raise ValueError("This rider login name is already in use.")
                        if user is None:
                            import secrets
                            from django.contrib.auth import get_user_model

                            password = secrets.token_urlsafe(12)
                            user = get_user_model().objects.create_user(
                                username=username, email=f"{username}@bazar.local", phone=phone,
                                role="RIDER", password=password,
                            )
                            issued_password = password
                    agent, _ = DeliveryAgent.objects.update_or_create(
                        phone=phone,
                        defaults={"name": name, "vehicle_number": vehicle, "user": user, "shop": request.user.shop, "is_available": True},
                    )
                messages.success(request, f"{agent.name} added to your delivery team. Login username: {username}.")
            except Exception as exc:
                messages.error(request, str(exc))
        elif action == "availability":
            agent = get_object_or_404(DeliveryAgent, pk=request.POST.get("agent_id"), shop=request.user.shop)
            agent.is_available = not agent.is_available
            agent.save(update_fields=["is_available"])
            messages.success(request, f"{agent.name} marked {'available' if agent.is_available else 'unavailable'}.")
        return render(request, "cart/seller_staff.html", {"agents": request.user.shop.delivery_agents.select_related("user").all(), "issued_password": issued_password})
    return render(request, "cart/seller_staff.html", {"agents": request.user.shop.delivery_agents.select_related("user").all()})


@seller_required
@require_http_methods(["POST"])
def dispatch_order(request, pk):
    with transaction.atomic():
        order = get_object_or_404(request.user.shop.orders.select_for_update(), pk=pk)
        agent = get_object_or_404(
            DeliveryAgent.objects.select_for_update(),
            pk=request.POST.get("delivery_agent"),
            is_available=True,
        )
        if order.status not in {Order.Status.PLACED, Order.Status.CONFIRMED}:
            messages.error(request, "Only placed or confirmed orders can be dispatched.")
            return redirect("cart:seller_orders")
        dispatched_at = timezone.now()
        order.delivery_agent = agent
        order.dispatched_at = dispatched_at
        order.estimated_delivery_time = dispatched_at + timedelta(minutes=60)
        order.status = Order.Status.DISPATCHED
        order.save(update_fields=["delivery_agent", "dispatched_at", "estimated_delivery_time", "status", "updated_at"])
        agent.is_available = False
        agent.save(update_fields=["is_available"])
    messages.success(request, f"{order.order_number} dispatched with {agent.name}.")
    return redirect("cart:seller_orders")


@login_required
def rider_dashboard(request):
    if getattr(request.user, "role", None) != "RIDER" or not hasattr(request.user, "delivery_agent"):
        return render(request, "core/not_seller.html", {"message": "Rider access is required."}, status=403)
    agent = request.user.delivery_agent
    orders = agent.orders.select_related("shop", "customer", "group").prefetch_related("items").all()
    return render(request, "cart/rider_dashboard.html", {"agent": agent, "orders": orders})


@login_required
@require_http_methods(["POST"])
def update_rider_location(request):
    if getattr(request.user, "role", None) != "RIDER" or not hasattr(request.user, "delivery_agent"):
        return JsonResponse({"ok": False, "error": "Rider access is required."}, status=403)
    try:
        latitude = float(request.POST.get("latitude"))
        longitude = float(request.POST.get("longitude"))
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Invalid location coordinates."}, status=400)
    agent = request.user.delivery_agent
    agent.latitude, agent.longitude = latitude, longitude
    agent.location_updated_at = timezone.now()
    agent.save(update_fields=["latitude", "longitude", "location_updated_at"])
    return JsonResponse({"ok": True, "updated_at": agent.location_updated_at.isoformat()})


@login_required
def rider_location_for_order(request, pk):
    order = get_object_or_404(Order.objects.select_related("shop", "delivery_agent"), pk=pk)
    allowed = (
        order.customer_id == request.user.pk
        or (getattr(request.user, "is_seller", False) and hasattr(request.user, "shop") and order.shop_id == request.user.shop.pk)
        or (getattr(request.user, "role", None) == "RIDER" and hasattr(request.user, "delivery_agent") and order.delivery_agent_id == request.user.delivery_agent.pk)
        or request.user.is_superuser
    )
    if not allowed:
        return JsonResponse({"ok": False, "error": "You cannot view this delivery location."}, status=403)
    if order.status not in {Order.Status.DISPATCHED, Order.Status.OUT_FOR_DELIVERY}:
        return JsonResponse({"ok": True, "location": None})
    agent = order.delivery_agent
    if (
        not agent or agent.latitude is None or agent.longitude is None or not agent.location_updated_at
        or agent.location_updated_at < timezone.now() - timedelta(minutes=5)
    ):
        return JsonResponse({"ok": True, "location": None})
    return JsonResponse({
        "ok": True,
        "location": {"latitude": float(agent.latitude), "longitude": float(agent.longitude), "updated_at": agent.location_updated_at.isoformat()},
    })


@login_required
@require_http_methods(["POST"])
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        transition_order(order, request.POST.get("status"), request.user)
    except (CheckoutError, PermissionDenied) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Order updated.")
    if getattr(request.user, "role", None) == "RIDER":
        return redirect("cart:rider_dashboard")
    return redirect("cart:seller_orders" if getattr(request.user, "is_seller", False) else "cart:history")
