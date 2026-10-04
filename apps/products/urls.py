from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("seller/", views.seller_products, name="seller_list"),
    path("seller/new/", views.product_upsert, name="new"),
    path("seller/<int:pk>/", views.product_upsert, name="edit"),
    path("seller/<int:pk>/toggle/", views.product_toggle, name="toggle"),
    path("seller/import/", views.csv_import_view, name="csv_import"),
    path("<slug:shop_slug>/<slug:slug>/", views.detail, name="detail"),
]
