import logging
import math
import uuid
from decimal import Decimal

from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import connection, models
from django.db.models import Case, IntegerField, Q, Value, When
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import phone_validator, pincode_validator

logger = logging.getLogger(__name__)


class ShopCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    icon = models.CharField(max_length=24, default="🏪", blank=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["sort_order"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:120] or f"category-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ShopQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def nearby(self, lat, lng, radius_km=5):
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            radius_f = float(radius_km or 5)
        except (TypeError, ValueError):
            return self.none()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "select shop_id, distance_meters from get_shops_within_radius(%s, %s, %s)",
                    [lat_f, lng_f, radius_f],
                )
                rows = cursor.fetchall()
        except Exception as exc:  # pragma: no cover - used by non-PostGIS test DBs.
            logger.warning("PostGIS nearby function unavailable; using haversine fallback: %s", exc)
            return self._nearby_haversine(lat_f, lng_f, radius_f)

        ids = [row[0] for row in rows]
        distances = {row[0]: row[1] for row in rows}
        order = Case(*[When(pk=pk, then=Value(pos)) for pos, pk in enumerate(ids)], output_field=IntegerField())
        shops = list(self.filter(pk__in=ids).order_by(order))
        for shop in shops:
            shop.distance_m = distances.get(shop.pk)
        return shops

    def _nearby_haversine(self, lat, lng, radius_km):
        radius_m = radius_km * 1000
        candidates = self.active().filter(latitude__isnull=False, longitude__isnull=False)
        matched = []
        for shop in candidates:
            distance = _haversine_m(lat, lng, float(shop.latitude), float(shop.longitude))
            if distance <= radius_m:
                shop.distance_m = distance
                matched.append(shop)
        return sorted(matched, key=lambda shop: shop.distance_m)


class Shop(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shop")
    category = models.ForeignKey(ShopCategory, on_delete=models.PROTECT, related_name="shops")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    logo = CloudinaryField("shop logo", blank=True, null=True)
    phone = models.CharField(max_length=10, validators=[phone_validator])
    whatsapp_number = models.CharField(max_length=10, validators=[phone_validator], blank=True)
    address = models.TextField()
    city = models.CharField(max_length=120, db_index=True)
    pincode = models.CharField(max_length=6, validators=[pincode_validator], db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    opening_time = models.TimeField(default="09:00")
    closing_time = models.TimeField(default="21:00")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True, db_index=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))
    review_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ShopQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["pincode"]),
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["owner"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(latitude__isnull=True) | (Q(latitude__gte=-90) & Q(latitude__lte=90)),
                name="shop_latitude_range",
            ),
            models.CheckConstraint(
                check=Q(longitude__isnull=True) | (Q(longitude__gte=-180) & Q(longitude__lte=180)),
                name="shop_longitude_range",
            ),
            models.CheckConstraint(check=Q(delivery_fee__gte=0), name="shop_delivery_fee_non_negative"),
            models.CheckConstraint(check=Q(min_order_amount__gte=0), name="shop_min_order_non_negative"),
        ]

    def save(self, *args, **kwargs):
        if not self.whatsapp_number:
            self.whatsapp_number = self.phone
        if not self.slug:
            base = slugify(self.name)[:140] or "shop"
            self.slug = _unique_slug(Shop, base, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("shops:detail", kwargs={"slug": self.slug})

    @property
    def is_open_now(self):
        now = timezone.localtime().time()
        if self.opening_time <= self.closing_time:
            return self.opening_time <= now <= self.closing_time
        return now >= self.opening_time or now <= self.closing_time

    @property
    def whatsapp_phone_e164(self):
        return f"91{self.whatsapp_number}"


def _unique_slug(model, base, instance_pk=None):
    slug = base
    for i in range(1, 21):
        qs = model.objects.filter(slug=slug)
        if instance_pk:
            qs = qs.exclude(pk=instance_pk)
        if not qs.exists():
            return slug
        slug = f"{base}-{i}"
    return f"{base}-{uuid.uuid4().hex[:8]}"


def _haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))
