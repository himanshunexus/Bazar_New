from django.contrib import admin

from .models import Shop, ShopCategory


@admin.register(ShopCategory)
class ShopCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "city", "pincode", "is_active", "avg_rating", "review_count")
    list_filter = ("is_active", "category", "city", "pincode")
    search_fields = ("name", "owner__username", "phone", "city", "pincode")
    prepopulated_fields = {"slug": ("name",)}
