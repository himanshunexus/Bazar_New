from decimal import Decimal

import cloudinary.models
from django.db import migrations, models
import django.db.models.deletion
import apps.products.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("shops", "0002_postgis_location"),
    ]

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(blank=True, db_index=True, max_length=120)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("mrp", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("stock", models.PositiveIntegerField(default=0)),
                ("unit_label", models.CharField(default="1 unit", max_length=40)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="products", to="shops.shop")),
            ],
            options={
                "ordering": ["name"],
                "indexes": [models.Index(fields=["shop", "is_active"], name="products_pr_shop_id_7c1a47_idx"), models.Index(fields=["category"], name="products_pr_categor_78da86_idx"), models.Index(fields=["is_active", "stock"], name="products_pr_is_acti_0ae3a3_idx"), models.Index(fields=["created_at"], name="products_pr_created_21087c_idx")],
            },
        ),
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", cloudinary.models.CloudinaryField(max_length=255, validators=[apps.products.models.validate_product_image], verbose_name="product image")),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="products.product")),
            ],
            options={
                "ordering": ["position", "id"],
                "indexes": [models.Index(fields=["product", "position"], name="products_pr_product_384543_idx")],
            },
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(fields=("shop", "slug"), name="unique_product_slug_per_shop"),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(check=models.Q(("price__gte", 0)), name="product_price_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(check=models.Q(("mrp__isnull", True), ("mrp__gte", 0), _connector="OR"), name="product_mrp_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(check=models.Q(("stock__gte", 0)), name="product_stock_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="productimage",
            constraint=models.CheckConstraint(check=models.Q(("position__gte", 0)), name="product_image_position_non_negative"),
        ),
    ]
