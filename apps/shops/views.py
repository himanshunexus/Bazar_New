from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import Shop, ShopCategory


def categories(request):
    return render(request, "shops/categories.html", {"categories": ShopCategory.objects.all()})


def category_detail(request, slug):
    category = get_object_or_404(ShopCategory, slug=slug)
    qs = category.shops.active()
    city = request.GET.get("city")
    pincode = request.GET.get("pincode")
    if city:
        qs = qs.filter(city__iexact=city)
    if pincode:
        qs = qs.filter(pincode=pincode)
    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "shops/category_detail.html", {"category": category, "page": page})


def detail(request, slug):
    shop = get_object_or_404(Shop.objects.select_related("category").prefetch_related("products__images", "reviews"), slug=slug, is_active=True)
    products = shop.products.filter(is_active=True)
    category = request.GET.get("category")
    if category:
        products = products.filter(category__iexact=category)
    return render(request, "shops/detail.html", {"shop": shop, "products": products})


def map_view(request):
    return render(request, "shops/map.html", {"categories": ShopCategory.objects.all()})


def geojson(request):
    lat = request.GET.get("lat") or request.session.get("lat") or settings.DEFAULT_LAT
    lng = request.GET.get("lng") or request.session.get("lng") or settings.DEFAULT_LNG
    radius = request.GET.get("radius") or request.session.get("radius_km") or settings.DEFAULT_RADIUS_KM
    shops = Shop.objects.nearby(lat, lng, radius)
    features = []
    for shop in shops:
        if shop.latitude is None or shop.longitude is None:
            continue
        distance = getattr(shop, "distance_m", None)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(shop.longitude), float(shop.latitude)]},
                "properties": {
                    "id": shop.id,
                    "name": shop.name,
                    "category": shop.category.name,
                    "hours": f"{shop.opening_time:%H:%M} - {shop.closing_time:%H:%M}",
                    "distance_m": distance,
                    "url": shop.get_absolute_url(),
                    "directions": f"https://www.google.com/maps/dir/?api=1&destination={shop.latitude},{shop.longitude}",
                },
            }
        )
    return JsonResponse({"type": "FeatureCollection", "features": features})
