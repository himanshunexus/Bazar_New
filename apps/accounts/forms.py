from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.utils.text import slugify

from apps.shops.models import Shop, ShopCategory

from .models import Address, User, phone_validator, pincode_validator


class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField()
    phone = forms.CharField(validators=[phone_validator], max_length=10)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER
        if commit:
            user.save()
        return user


class SellerRegistrationForm(UserCreationForm):
    email = forms.EmailField()
    phone = forms.CharField(validators=[phone_validator], max_length=10)
    shop_name = forms.CharField(max_length=160)
    category = forms.ModelChoiceField(queryset=ShopCategory.objects.all(), required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    city = forms.CharField(max_length=120)
    pincode = forms.CharField(validators=[pincode_validator], max_length=6)
    latitude = forms.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = forms.DecimalField(max_digits=9, decimal_places=6, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.SELLER
        if commit:
            user.save()
            category = self.cleaned_data["category"] or ShopCategory.objects.get_or_create(
                slug="general", defaults={"name": "General", "icon": "🏪"}
            )[0]
            base_slug = slugify(self.cleaned_data["shop_name"])[:80] or "shop"
            slug = base_slug
            for i in range(1, 21):
                if not Shop.objects.filter(slug=slug).exists():
                    break
                slug = f"{base_slug}-{i}"
            Shop.objects.create(
                owner=user,
                category=category,
                name=self.cleaned_data["shop_name"],
                slug=slug,
                phone=self.cleaned_data["phone"],
                whatsapp_number=self.cleaned_data["phone"],
                address=self.cleaned_data["address"],
                city=self.cleaned_data["city"],
                pincode=self.cleaned_data["pincode"],
                latitude=self.cleaned_data.get("latitude"),
                longitude=self.cleaned_data.get("longitude"),
            )
        return user


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "label",
            "full_name",
            "phone",
            "line1",
            "line2",
            "city",
            "pincode",
            "latitude",
            "longitude",
            "is_default",
        ]
