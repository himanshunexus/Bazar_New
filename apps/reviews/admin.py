from django.contrib import admin

from .models import ProductReview, ShopReview


@admin.register(ShopReview)
class ShopReviewAdmin(admin.ModelAdmin):
    list_display = ("shop", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("shop__name", "user__username", "comment")


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "user__username", "comment")
