from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.detail, name="detail"),
    path("add/<int:product_id>/", views.add, name="add"),
    path("update/<int:product_id>/", views.update, name="update"),
    path("remove/<int:product_id>/", views.remove, name="remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("confirmation/<int:group_id>/", views.confirmation, name="confirmation"),
    path("orders/", views.order_history, name="history"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/reorder/", views.reorder, name="reorder"),
    path("seller/orders/", views.seller_orders, name="seller_orders"),
    path("orders/<int:pk>/status/", views.update_order_status, name="status"),
]
