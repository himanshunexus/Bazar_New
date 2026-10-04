from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.decorators import seller_required
from apps.shops.models import Shop

from .csv_import import CsvImportError, import_products
from .forms import CsvImportForm, ProductForm, ProductImageFormSet
from .models import Product


def detail(request, shop_slug, slug):
    product = get_object_or_404(
        Product.objects.select_related("shop").prefetch_related("images", "reviews"),
        shop__slug=shop_slug,
        slug=slug,
        is_active=True,
    )
    viewed = request.session.setdefault("recent_product_ids", [])
    viewed = [pid for pid in viewed if pid != product.id]
    request.session["recent_product_ids"] = ([product.id] + viewed)[:20]
    message = quote(f"{product.name} x 1 - Rs {product.price} from {product.shop.name}")
    whatsapp_url = f"https://wa.me/{product.shop.whatsapp_phone_e164}?text={message}"
    return render(request, "products/detail.html", {"product": product, "whatsapp_url": whatsapp_url})


@seller_required
def seller_products(request):
    products = request.user.shop.products.all()
    return render(request, "products/seller_list.html", {"products": products})


@seller_required
@require_http_methods(["GET", "POST"])
def product_upsert(request, pk=None):
    product = get_object_or_404(Product, pk=pk, shop=request.user.shop) if pk else Product(shop=request.user.shop)
    form = ProductForm(request.POST or None, instance=product)
    formset = ProductImageFormSet(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            saved = form.save(commit=False)
            saved.shop = request.user.shop
            saved.save()
            formset.instance = saved
            formset.save()
        messages.success(request, "Product saved.")
        return redirect("products:seller_list")
    return render(request, "products/form.html", {"form": form, "formset": formset, "product": product})


@seller_required
@require_http_methods(["POST"])
def product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk, shop=request.user.shop)
    product.is_active = not product.is_active
    product.save(update_fields=["is_active", "updated_at"])
    return redirect("products:seller_list")


@seller_required
@require_http_methods(["GET", "POST"])
def csv_import_view(request):
    form = CsvImportForm(request.POST or None, request.FILES or None)
    errors = []
    if request.method == "POST" and form.is_valid():
        try:
            imported = import_products(request.user.shop, form.cleaned_data["file"])
        except CsvImportError as exc:
            errors = exc.row_errors
        else:
            messages.success(request, f"Imported {len(imported)} products.")
            return redirect("products:seller_list")
    return render(request, "products/csv_import.html", {"form": form, "errors": errors})
