from django.contrib import admin

from .models import Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    max_num = 5


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "shop", "price", "stock", "is_active")
    list_filter = ("is_active", "category", "shop")
    search_fields = ("name", "description", "shop__name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]
