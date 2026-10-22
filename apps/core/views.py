import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Count, Sum
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.cart.cart import Cart
from apps.products.models import Product
from apps.shops.models import Shop, ShopCategory

from .ml_client import get_recommendations, hydrate_products

logger = logging.getLogger(__name__)


def home(request):
    profile_pincode = ""
    lat = request.session.get("lat")
    lng = request.session.get("lng")
    location_missing = lat in (None, "") or lng in (None, "")
    if request.user.is_authenticated:
        address = request.user.addresses.filter(is_default=True).first()
        if address:
            profile_pincode = address.pincode
            # A saved profile address wins over a stale browser/session location.
            if address.latitude is not None and address.longitude is not None:
                lat, lng = str(address.latitude), str(address.longitude)
                location_missing = False
            else:
                lat = lng = None
                location_missing = True
    if location_missing:
        if not profile_pincode:
            lat, lng = settings.DEFAULT_LAT, settings.DEFAULT_LNG
    radius = request.GET.get("radius") or request.session.get("radius_km") or settings.DEFAULT_RADIUS_KM
    if lat is not None and lng is not None:
        shops = Shop.objects.active().nearby(lat, lng, 5)
    else:
        shops = []
    recent_ids = request.session.get("recent_product_ids", []) + Cart(request).product_ids()
    rec_ids = get_recommendations(request.user.id if request.user.is_authenticated else None, recent_ids, 10)
    recommendations = hydrate_products(rec_ids, lat, lng, 5)
    return render(
        request,
        "core/home.html",
        {
            "shops": shops,
            "categories": ShopCategory.objects.all()[:12],
            "recommendations": recommendations,
            "radius": radius,
            "profile_pincode": profile_pincode,
        },
    )


def search(request):
    q = (request.GET.get("q") or "").strip()
    shops = Shop.objects.none()
    products = Product.objects.none()
    if q:
        nearby_shop_ids = None
        if request.user.is_authenticated:
            address = request.user.addresses.filter(is_default=True).first()
            if address and address.latitude is not None and address.longitude is not None:
                nearby_shop_ids = [shop.pk for shop in Shop.objects.active().nearby(address.latitude, address.longitude, 5)]
            elif address:
                nearby_shop_ids = []
        shops_qs = Shop.objects.active().filter(name__icontains=q).select_related("category")
        product_qs = Product.objects.filter(is_active=True, stock__gt=0, shop__is_active=True, name__icontains=q)
        if nearby_shop_ids is not None:
            shops_qs = shops_qs.filter(pk__in=nearby_shop_ids)
            product_qs = product_qs.filter(shop_id__in=nearby_shop_ids)
        shops = shops_qs[:10]
        products = product_qs.select_related("shop").prefetch_related("images")[:10]
    return render(request, "core/partials/search_results.html", {"q": q, "shops": shops, "products": products})


@require_POST
def set_location(request):
    try:
        lat, lng = float(request.POST.get("lat")), float(request.POST.get("lng"))
        if not -90 <= lat <= 90 or not -180 <= lng <= 180:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Invalid coordinates."}, status=400)
    request.session["lat"], request.session["lng"] = lat, lng
    request.session["radius_km"] = request.POST.get("radius") or settings.DEFAULT_RADIUS_KM
    if request.user.is_authenticated:
        request.session["location_user_id"] = request.user.pk
    return JsonResponse({"ok": True})


def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("select 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Health check database probe failed")
        return JsonResponse({"ok": False, "error": "Service temporarily unavailable."}, status=503)
    return JsonResponse({"ok": True})


@login_required
def seller_dashboard(request):
    if not getattr(request.user, "is_seller", False) or not hasattr(request.user, "shop"):
        return render(request, "core/not_seller.html", status=403)
    shop = request.user.shop
    orders = shop.orders.all()
    today = timezone.localdate()
    start_month = today.replace(day=1)
    delivered = orders.filter(status="DELIVERED")
    sales_today = delivered.filter(created_at__date=today).aggregate(total=Sum("total"), count=Count("id"))
    sales_month = delivered.filter(created_at__date__gte=start_month, created_at__date__lte=today).aggregate(total=Sum("total"), count=Count("id"))
    low_stock = shop.products.filter(stock__lte=5).order_by("stock")[:10]
    return render(request, "core/seller_dashboard.html", {"shop": shop, "orders": orders, "low_stock": low_stock, "sales_today": sales_today, "sales_month": sales_month})
