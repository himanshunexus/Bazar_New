from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("cart", "0005_deliveryagent_shop")]

    operations = [
        migrations.AddField(
            model_name="order",
            name="cancellation_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
