from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q


phone_validator = RegexValidator(r"^\d{10}$", "Enter a 10-digit mobile number.")
pincode_validator = RegexValidator(r"^\d{6}$", "Enter a 6-digit pincode.")


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        SELLER = "SELLER", "Seller"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER, db_index=True)
    phone = models.CharField(max_length=10, validators=[phone_validator], blank=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(phone="") | Q(phone__regex=r"^\d{10}$"),
                name="accounts_user_phone_10_digits_or_blank",
            )
        ]
        indexes = [models.Index(fields=["email"]), models.Index(fields=["role"])]

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=60, default="Home")
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=10, validators=[phone_validator])
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, db_index=True)
    pincode = models.CharField(max_length=6, validators=[pincode_validator], db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]
        indexes = [
            models.Index(fields=["user", "is_default"]),
            models.Index(fields=["city"]),
            models.Index(fields=["pincode"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(phone__regex=r"^\d{10}$"), name="address_phone_10_digits"),
            models.CheckConstraint(check=Q(pincode__regex=r"^\d{6}$"), name="address_pincode_6_digits"),
            models.CheckConstraint(
                check=Q(latitude__isnull=True) | (Q(latitude__gte=-90) & Q(latitude__lte=90)),
                name="address_latitude_range",
            ),
            models.CheckConstraint(
                check=Q(longitude__isnull=True) | (Q(longitude__gte=-180) & Q(longitude__lte=180)),
                name="address_longitude_range",
            ),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)

    def __str__(self):
        return f"{self.label} - {self.full_name}"

    @property
    def single_line(self):
        parts = [self.line1, self.line2, self.city, self.pincode]
        return ", ".join(part for part in parts if part)
