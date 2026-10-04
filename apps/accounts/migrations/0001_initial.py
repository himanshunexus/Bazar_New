from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False)),
                ("username", models.CharField(error_messages={"unique": "A user with that username already exists."}, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.", max_length=150, unique=True, validators=[django.core.validators.RegexValidator("^[\\w.@+-]+\\Z", "Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters.", "invalid")], verbose_name="username")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                ("date_joined", models.DateTimeField(auto_now_add=True, verbose_name="date joined")),
                ("role", models.CharField(choices=[("CUSTOMER", "Customer"), ("SELLER", "Seller")], db_index=True, default="CUSTOMER", max_length=20)),
                ("phone", models.CharField(blank=True, max_length=10, validators=[django.core.validators.RegexValidator("^\\d{10}$", "Enter a 10-digit mobile number.")])),
                ("groups", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.group")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.permission")),
            ],
            options={
                "indexes": [models.Index(fields=["email"], name="accounts_us_email_50909a_idx"), models.Index(fields=["role"], name="accounts_us_role_615d30_idx")],
            },
        ),
        migrations.CreateModel(
            name="Address",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(default="Home", max_length=60)),
                ("full_name", models.CharField(max_length=150)),
                ("phone", models.CharField(max_length=10, validators=[django.core.validators.RegexValidator("^\\d{10}$", "Enter a 10-digit mobile number.")])),
                ("line1", models.CharField(max_length=255)),
                ("line2", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(db_index=True, max_length=120)),
                ("pincode", models.CharField(db_index=True, max_length=6, validators=[django.core.validators.RegexValidator("^\\d{6}$", "Enter a 6-digit pincode.")])),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="addresses", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-is_default", "-updated_at"],
                "indexes": [models.Index(fields=["user", "is_default"], name="accounts_ad_user_id_f2f8b2_idx"), models.Index(fields=["city"], name="accounts_ad_city_816df5_idx"), models.Index(fields=["pincode"], name="accounts_ad_pincode_d80755_idx")],
            },
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(check=models.Q(("phone", ""), ("phone__regex", "^\\d{10}$"), _connector="OR"), name="accounts_user_phone_10_digits_or_blank"),
        ),
        migrations.AddConstraint(
            model_name="address",
            constraint=models.CheckConstraint(check=models.Q(("phone__regex", "^\\d{10}$")), name="address_phone_10_digits"),
        ),
        migrations.AddConstraint(
            model_name="address",
            constraint=models.CheckConstraint(check=models.Q(("pincode__regex", "^\\d{6}$")), name="address_pincode_6_digits"),
        ),
        migrations.AddConstraint(
            model_name="address",
            constraint=models.CheckConstraint(check=models.Q(("latitude__isnull", True), models.Q(("latitude__gte", -90), ("latitude__lte", 90)), _connector="OR"), name="address_latitude_range"),
        ),
        migrations.AddConstraint(
            model_name="address",
            constraint=models.CheckConstraint(check=models.Q(("longitude__isnull", True), models.Q(("longitude__gte", -180), ("longitude__lte", 180)), _connector="OR"), name="address_longitude_range"),
        ),
    ]
