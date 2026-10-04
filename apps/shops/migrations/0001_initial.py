from decimal import Decimal

import cloudinary.models
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ShopCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("icon", models.CharField(blank=True, default="🏪", max_length=24)),
                ("sort_order", models.PositiveIntegerField(db_index=True, default=0)),
            ],
            options={
                "ordering": ["sort_order", "name"],
                "indexes": [models.Index(fields=["slug"], name="shops_shopc_slug_c48daa_idx"), models.Index(fields=["sort_order"], name="shops_shopc_sort_or_034e6b_idx")],
            },
        ),
        migrations.CreateModel(
            name="Shop",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                ("logo", cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name="shop logo")),
                ("phone", models.CharField(max_length=10, validators=[django.core.validators.RegexValidator("^\\d{10}$", "Enter a 10-digit mobile number.")])),
                ("whatsapp_number", models.CharField(blank=True, max_length=10, validators=[django.core.validators.RegexValidator("^\\d{10}$", "Enter a 10-digit mobile number.")])),
                ("address", models.TextField()),
                ("city", models.CharField(db_index=True, max_length=120)),
                ("pincode", models.CharField(db_index=True, max_length=6, validators=[django.core.validators.RegexValidator("^\\d{6}$", "Enter a 6-digit pincode.")])),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("opening_time", models.TimeField(default="09:00")),
                ("closing_time", models.TimeField(default="21:00")),
                ("delivery_fee", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("min_order_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("avg_rating", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=3)),
                ("review_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="shops", to="shops.shopcategory")),
                ("owner", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="shop", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["name"],
                "indexes": [models.Index(fields=["city"], name="shops_shop_city_42c03f_idx"), models.Index(fields=["pincode"], name="shops_shop_pincode_aa694f_idx"), models.Index(fields=["is_active", "category"], name="shops_shop_is_acti_144de7_idx"), models.Index(fields=["owner"], name="shops_shop_owner_i_40e136_idx")],
            },
        ),
        migrations.AddConstraint(
            model_name="shop",
            constraint=models.CheckConstraint(check=models.Q(("latitude__isnull", True), models.Q(("latitude__gte", -90), ("latitude__lte", 90)), _connector="OR"), name="shop_latitude_range"),
        ),
        migrations.AddConstraint(
            model_name="shop",
            constraint=models.CheckConstraint(check=models.Q(("longitude__isnull", True), models.Q(("longitude__gte", -180), ("longitude__lte", 180)), _connector="OR"), name="shop_longitude_range"),
        ),
        migrations.AddConstraint(
            model_name="shop",
            constraint=models.CheckConstraint(check=models.Q(("delivery_fee__gte", 0)), name="shop_delivery_fee_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="shop",
            constraint=models.CheckConstraint(check=models.Q(("min_order_amount__gte", 0)), name="shop_min_order_non_negative"),
        ),
    ]
