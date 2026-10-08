from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.decorators import seller_required
from apps.products.models import Product

from .cart import Cart
from .forms import CheckoutForm
from .models import Order
from .services import CheckoutError, place_order, transition_order


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
    order = get_object_or_404(request.user.orders.select_related("shop").prefetch_related("items"), pk=pk)
    return render(request, "cart/order_detail.html", {"order": order})


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
    orders = request.user.shop.orders.prefetch_related("items").select_related("customer").all()
    return render(request, "cart/seller_orders.html", {"orders": orders})


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
    return redirect("cart:seller_orders" if getattr(request.user, "is_seller", False) else "cart:history")
