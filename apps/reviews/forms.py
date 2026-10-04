from django import forms

from .models import ProductReview, ShopReview


class ShopReviewForm(forms.ModelForm):
    class Meta:
        model = ShopReview
        fields = ["rating", "comment"]


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ["rating", "comment"]
