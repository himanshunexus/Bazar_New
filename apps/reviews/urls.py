from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("shops/<int:shop_id>/", views.shop_review, name="shop"),
    path("products/<int:product_id>/", views.product_review, name="product"),
]
