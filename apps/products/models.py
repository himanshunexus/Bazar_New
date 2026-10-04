import uuid
from decimal import Decimal

from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify


class Product(models.Model):
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE, related_name="products")
    category = models.CharField(max_length=120, blank=True, db_index=True)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    unit_label = models.CharField(max_length=40, default="1 unit")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["shop", "slug"], name="unique_product_slug_per_shop"),
            models.CheckConstraint(check=Q(price__gte=0), name="product_price_non_negative"),
            models.CheckConstraint(check=Q(mrp__isnull=True) | Q(mrp__gte=0), name="product_mrp_non_negative"),
            models.CheckConstraint(check=Q(stock__gte=0), name="product_stock_non_negative"),
        ]
        indexes = [
            models.Index(fields=["shop", "is_active"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_active", "stock"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:150] or "product"
            self.slug = self._build_unique_slug(base)
        super().save(*args, **kwargs)

    def _build_unique_slug(self, base):
        slug = base
        for i in range(1, 21):
            qs = Product.objects.filter(shop=self.shop, slug=slug)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if not qs.exists():
                return slug
            slug = f"{base}-{i}"
        return f"{base}-{uuid.uuid4().hex[:8]}"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"shop_slug": self.shop.slug, "slug": self.slug})

    @property
    def is_in_stock(self):
        return self.stock > 0


def validate_product_image(file_obj):
    if file_obj and getattr(file_obj, "size", 0) > 5 * 1024 * 1024:
        raise ValidationError("Each image must be 5 MB or smaller.")
    content_type = getattr(file_obj, "content_type", "")
    if content_type and content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValidationError("Use JPG, PNG or WebP images.")


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = CloudinaryField("product image", validators=[validate_product_image])
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["product", "position"])]
        constraints = [
            models.CheckConstraint(check=Q(position__gte=0), name="product_image_position_non_negative"),
        ]

    def clean(self):
        super().clean()
        qs = ProductImage.objects.filter(product=self.product)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if self.product_id and qs.count() >= 5:
            raise ValidationError("A product can have at most 5 images.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
