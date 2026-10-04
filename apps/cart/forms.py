from django import forms

from apps.accounts.models import phone_validator, pincode_validator


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=10, validators=[phone_validator])
    line1 = forms.CharField(max_length=255)
    line2 = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=120)
    pincode = forms.CharField(max_length=6, validators=[pincode_validator])
    latitude = forms.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = forms.DecimalField(max_digits=9, decimal_places=6, required=False)
    customer_note = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
