from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.products.models import Product
from apps.shops.models import Shop

from .forms import ProductReviewForm, ShopReviewForm
from .models import ProductReview, ShopReview


@login_required
@require_http_methods(["POST"])
def shop_review(request, shop_id):
    shop = get_object_or_404(Shop, pk=shop_id)
    review = ShopReview.objects.filter(user=request.user, shop=shop).first()
    review = review or ShopReview(user=request.user, shop=shop)
    form = ShopReviewForm(request.POST, instance=review)
    if form.is_valid():
        try:
            form.save()
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Review saved.")
    else:
        messages.error(request, "Please check your review.")
    return redirect(shop.get_absolute_url())


@login_required
@require_http_methods(["POST"])
def product_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    review = ProductReview.objects.filter(user=request.user, product=product).first()
    review = review or ProductReview(user=request.user, product=product)
    form = ProductReviewForm(request.POST, instance=review)
    if form.is_valid():
        try:
            form.save()
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Review saved.")
    else:
        messages.error(request, "Please check your review.")
    return redirect(product.get_absolute_url())
