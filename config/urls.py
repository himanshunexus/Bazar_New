from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("shops/", include("apps.shops.urls")),
    path("products/", include("apps.products.urls")),
    path("cart/", include("apps.cart.urls")),
    path("reviews/", include("apps.reviews.urls")),
]
