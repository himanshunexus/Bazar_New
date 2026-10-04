from django.conf import settings
from django.db import migrations, models
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
            name="ShopReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField()),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="shops.shop")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shop_reviews", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["shop", "created_at"], name="reviews_sho_shop_id_328610_idx"), models.Index(fields=["user"], name="reviews_sho_user_id_ce72ad_idx")],
            },
        ),
        migrations.CreateModel(
            name="ProductReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField()),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="products.product")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_reviews", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["product", "created_at"], name="reviews_pro_product_b78c02_idx"), models.Index(fields=["user"], name="reviews_pro_user_id_d68447_idx")],
            },
        ),
        migrations.AddConstraint(model_name="shopreview", constraint=models.UniqueConstraint(fields=("user", "shop"), name="unique_shop_review_per_user")),
        migrations.AddConstraint(model_name="shopreview", constraint=models.CheckConstraint(check=models.Q(("rating__gte", 1), ("rating__lte", 5)), name="shop_review_rating_range")),
        migrations.AddConstraint(model_name="productreview", constraint=models.UniqueConstraint(fields=("user", "product"), name="unique_product_review_per_user")),
        migrations.AddConstraint(model_name="productreview", constraint=models.CheckConstraint(check=models.Q(("rating__gte", 1), ("rating__lte", 5)), name="product_review_rating_range")),
    ]
