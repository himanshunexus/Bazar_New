from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("shops", "0002_postgis_location"),
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("group_number", models.CharField(max_length=32, unique=True)),
                ("delivery_name", models.CharField(max_length=150)),
                ("delivery_phone", models.CharField(max_length=10, validators=[django.core.validators.RegexValidator("^\\d{10}$", "Enter a 10-digit mobile number.")])),
                ("delivery_address_line", models.TextField()),
                ("delivery_city", models.CharField(max_length=120)),
                ("delivery_pincode", models.CharField(max_length=6, validators=[django.core.validators.RegexValidator("^\\d{6}$", "Enter a 6-digit pincode.")])),
                ("delivery_latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("delivery_longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("payment_method", models.CharField(default="COD", max_length=10)),
                ("grand_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_groups", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["customer", "created_at"], name="cart_orderg_custome_55d017_idx")],
            },
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_number", models.CharField(max_length=32, unique=True)),
                ("status", models.CharField(choices=[("PLACED", "Placed"), ("CONFIRMED", "Confirmed"), ("OUT_FOR_DELIVERY", "Out for delivery"), ("DELIVERED", "Delivered"), ("CANCELLED", "Cancelled")], db_index=True, default="PLACED", max_length=20)),
                ("payment_method", models.CharField(default="COD", max_length=10)),
                ("payment_status", models.CharField(choices=[("PENDING", "Pending"), ("PAID", "Paid")], default="PENDING", max_length=10)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("subtotal", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("delivery_fee", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("customer_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to=settings.AUTH_USER_MODEL)),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="orders", to="cart.ordergroup")),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="shops.shop")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["shop", "status"], name="cart_order_shop_id_8144ce_idx"), models.Index(fields=["customer", "created_at"], name="cart_order_custome_2862c7_idx"), models.Index(fields=["order_number"], name="cart_order_order_n_19710d_idx")],
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_name", models.CharField(max_length=180)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("quantity", models.PositiveIntegerField()),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="cart.order")),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="products.product")),
            ],
            options={
                "indexes": [models.Index(fields=["order"], name="cart_orderi_order_i_1ced7e_idx"), models.Index(fields=["product"], name="cart_orderi_product_9b0897_idx")],
            },
        ),
        migrations.AddConstraint(model_name="ordergroup", constraint=models.CheckConstraint(check=models.Q(("payment_method", "COD")), name="order_group_cod_only")),
        migrations.AddConstraint(model_name="ordergroup", constraint=models.CheckConstraint(check=models.Q(("grand_total__gte", 0)), name="order_group_grand_total_non_negative")),
        migrations.AddConstraint(model_name="order", constraint=models.CheckConstraint(check=models.Q(("payment_method", "COD")), name="order_cod_only")),
        migrations.AddConstraint(model_name="order", constraint=models.CheckConstraint(check=models.Q(("subtotal__gte", 0)), name="order_subtotal_non_negative")),
        migrations.AddConstraint(model_name="order", constraint=models.CheckConstraint(check=models.Q(("delivery_fee__gte", 0)), name="order_delivery_fee_non_negative")),
        migrations.AddConstraint(model_name="order", constraint=models.CheckConstraint(check=models.Q(("total__gte", 0)), name="order_total_non_negative")),
        migrations.AddConstraint(model_name="orderitem", constraint=models.CheckConstraint(check=models.Q(("quantity__gt", 0)), name="order_item_quantity_positive")),
        migrations.AddConstraint(model_name="orderitem", constraint=models.CheckConstraint(check=models.Q(("line_total__gte", 0)), name="order_item_line_total_non_negative")),
    ]
