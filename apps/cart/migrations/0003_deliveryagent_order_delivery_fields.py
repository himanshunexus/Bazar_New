from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("cart", "0002_rename_cart_order_shop_id_8144ce_idx_cart_order_shop_id_73c467_idx_and_more")]

    operations = [
        migrations.CreateModel(
            name="DeliveryAgent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=10, unique=True, validators=[django.core.validators.RegexValidator("^\\d{10}$", "Enter a 10-digit mobile number.")])),
                ("vehicle_number", models.CharField(blank=True, max_length=30)),
                ("is_available", models.BooleanField(db_index=True, default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_agent",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to="cart.deliveryagent"),
        ),
        migrations.AddField(model_name="order", name="dispatched_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="order", name="estimated_delivery_time", field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(choices=[("PLACED", "Placed"), ("CONFIRMED", "Confirmed"), ("DISPATCHED", "Dispatched"), ("OUT_FOR_DELIVERY", "Out for delivery"), ("DELIVERED", "Delivered"), ("CANCELLED", "Cancelled")], db_index=True, default="PLACED", max_length=20),
        ),
    ]
