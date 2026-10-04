from django.contrib import admin

from .models import Order, OrderGroup, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "quantity", "line_total")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "shop", "customer", "status", "payment_method", "payment_status", "total")
    list_filter = ("status", "payment_status", "shop", "created_at")
    search_fields = ("order_number", "customer__username", "shop__name")
    readonly_fields = ("order_number", "payment_method", "payment_status", "paid_at", "subtotal", "delivery_fee", "total")
    inlines = [OrderItemInline]


@admin.register(OrderGroup)
class OrderGroupAdmin(admin.ModelAdmin):
    list_display = ("group_number", "customer", "payment_method", "grand_total", "created_at")
    list_filter = ("payment_method", "created_at")
    search_fields = ("group_number", "customer__username", "delivery_phone")
