from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_alter_user_managers_and_more")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(choices=[("CUSTOMER", "Customer"), ("SELLER", "Seller"), ("RIDER", "Rider")], db_index=True, default="CUSTOMER", max_length=20),
        ),
    ]
