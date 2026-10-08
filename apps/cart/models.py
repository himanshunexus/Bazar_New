import random
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import phone_validator, pincode_validator


class OrderGroup(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="order_groups")
    group_number = models.CharField(max_length=32, unique=True)
    delivery_name = models.CharField(max_length=150)
    delivery_phone = models.CharField(max_length=10, validators=[phone_validator])
    delivery_address_line = models.TextField()
    delivery_city = models.CharField(max_length=120)
    delivery_pincode = models.CharField(max_length=6, validators=[pincode_validator])
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    payment_method = models.CharField(max_length=10, default="COD")
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "created_at"])]
        constraints = [
            models.CheckConstraint(check=Q(payment_method="COD"), name="order_group_cod_only"),
            models.CheckConstraint(check=Q(grand_total__gte=0), name="order_group_grand_total_non_negative"),
        ]

    def __str__(self):
        return self.group_number


class DeliveryAgent(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=10, validators=[phone_validator], unique=True)
    vehicle_number = models.CharField(max_length=30, blank=True)
    is_available = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "PLACED", "Placed"
        CONFIRMED = "CONFIRMED", "Confirmed"
        DISPATCHED = "DISPATCHED", "Dispatched"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for delivery"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE, related_name="orders")
    shop = models.ForeignKey("shops.Shop", on_delete=models.PROTECT, related_name="orders")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    order_number = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED, db_index=True)
    payment_method = models.CharField(max_length=10, default="COD")
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    customer_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivery_agent = models.ForeignKey(
        DeliveryAgent, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    dispatched_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shop", "status"]),
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["order_number"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(payment_method="COD"), name="order_cod_only"),
            models.CheckConstraint(check=Q(subtotal__gte=0), name="order_subtotal_non_negative"),
            models.CheckConstraint(check=Q(delivery_fee__gte=0), name="order_delivery_fee_non_negative"),
            models.CheckConstraint(check=Q(total__gte=0), name="order_total_non_negative"),
        ]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=180)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [models.Index(fields=["order"]), models.Index(fields=["product"])]
        constraints = [
            models.CheckConstraint(check=Q(quantity__gt=0), name="order_item_quantity_positive"),
            models.CheckConstraint(check=Q(line_total__gte=0), name="order_item_line_total_non_negative"),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"


def make_group_number():
    stamp = timezone.localdate().strftime("%Y%m%d")
    return f"BZG-{stamp}-{random.randint(100000, 999999)}"


def make_order_number():
    stamp = timezone.localdate().strftime("%Y%m%d")
    return f"BZR-{stamp}-{random.randint(100000, 999999)}"
