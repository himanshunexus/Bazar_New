from django import forms
from django.forms import inlineformset_factory

from .models import Product, ProductImage


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name", "description", "price", "mrp", "stock", "unit_label", "is_active"]


ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    fields=["image", "position"],
    extra=1,
    max_num=5,
    validate_max=True,
    can_delete=True,
)


class CsvImportForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        file_obj = self.cleaned_data["file"]
        if file_obj.size > 2 * 1024 * 1024:
            raise forms.ValidationError("CSV must be 2 MB or smaller.")
        return file_obj
