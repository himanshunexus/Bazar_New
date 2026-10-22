from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("products", "0002_rename_products_pr_shop_id_7c1a47_idx_products_pr_shop_id_44685a_idx_and_more")]

    operations = [
        migrations.AddField(
            model_name="productimage",
            name="source_url",
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
