import logging
from collections import OrderedDict

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, Count, IntegerField, Value, When

logger = logging.getLogger(__name__)
session = requests.Session()
CIRCUIT_KEY = "ml:circuit_open"
TRENDING_KEY = "ml:trending:{top_n}"


def get_trending_product_ids(top_n=10):
    cache_key = TRENDING_KEY.format(top_n=top_n)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    from apps.cart.models import OrderItem
    from apps.products.models import Product

    sold_ids = list(
        OrderItem.objects.filter(product__is_active=True, product__stock__gt=0, product__shop__is_active=True)
        .values("product_id")
        .annotate(total=Count("id"))
        .order_by("-total")
        .values_list("product_id", flat=True)[:top_n]
    )
    if len(sold_ids) < top_n:
        extras = Product.objects.filter(is_active=True, stock__gt=0, shop__is_active=True).exclude(id__in=sold_ids).order_by("-created_at").values_list("id", flat=True)[: top_n - len(sold_ids)]
        sold_ids.extend(list(extras))
    cache.set(cache_key, sold_ids, 300)
    return sold_ids


def get_recommendations(user_id, recent_product_ids, top_n=10):
    if cache.get(CIRCUIT_KEY):
        return get_trending_product_ids(top_n)
    payload = {"user_id": user_id, "recent_product_ids": list(OrderedDict.fromkeys(recent_product_ids or []))[:20], "top_n": top_n}
    try:
        response = session.post(settings.ML_SERVICE_URL, json=payload, timeout=1.5)
        response.raise_for_status()
        data = response.json()
        product_ids = data.get("recommended_product_ids")
        if not isinstance(product_ids, list) or not all(isinstance(pid, int) for pid in product_ids):
            raise ValueError("Bad recommendation shape")
        return product_ids[:top_n]
    except Exception as exc:
        logger.info("ML recommendation fallback: %s", exc)
        cache.set(CIRCUIT_KEY, True, 30)
        return get_trending_product_ids(top_n)


def hydrate_products(product_ids, lat=None, lng=None, radius_km=None):
    from apps.products.models import Product
    from apps.shops.models import Shop

    product_ids = list(OrderedDict.fromkeys(product_ids))
    if not product_ids:
        return []
    order = Case(*[When(pk=pk, then=Value(pos)) for pos, pk in enumerate(product_ids)], output_field=IntegerField())
    qs = Product.objects.select_related("shop").filter(id__in=product_ids, is_active=True, stock__gt=0, shop__is_active=True)
    if lat and lng:
        shops = Shop.objects.nearby(lat, lng, radius_km or settings.DEFAULT_RADIUS_KM)
        qs = qs.filter(shop_id__in=[shop.id for shop in shops])
    return list(qs.order_by(order))
