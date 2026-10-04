from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Avg, Q

from apps.cart.models import Order


class ShopReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shop_reviews")
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "shop"], name="unique_shop_review_per_user"),
            models.CheckConstraint(check=Q(rating__gte=1) & Q(rating__lte=5), name="shop_review_rating_range"),
        ]
        indexes = [models.Index(fields=["shop", "created_at"]), models.Index(fields=["user"])]

    def clean(self):
        super().clean()
        if self.user_id and self.shop_id and not Order.objects.filter(
            customer=self.user,
            shop=self.shop,
            status=Order.Status.DELIVERED,
        ).exists():
            raise ValidationError("You can review a shop after a delivered order.")

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.recompute_shop_rating(self.shop)

    @staticmethod
    def recompute_shop_rating(shop):
        summary = shop.reviews.aggregate(avg=Avg("rating"), count=models.Count("id"))
        shop.avg_rating = Decimal(str(round(summary["avg"] or 0, 2)))
        shop.review_count = summary["count"] or 0
        shop.save(update_fields=["avg_rating", "review_count", "updated_at"])


class ProductReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_reviews")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_product_review_per_user"),
            models.CheckConstraint(check=Q(rating__gte=1) & Q(rating__lte=5), name="product_review_rating_range"),
        ]
        indexes = [models.Index(fields=["product", "created_at"]), models.Index(fields=["user"])]

    def clean(self):
        super().clean()
        if self.user_id and self.product_id and not Order.objects.filter(
            customer=self.user,
            status=Order.Status.DELIVERED,
            items__product=self.product,
        ).exists():
            raise ValidationError("You can review a product after a delivered order.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
