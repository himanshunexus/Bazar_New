from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("location/", views.set_location, name="set_location"),
    path("healthz", views.healthz, name="healthz"),
    path("seller/", views.seller_dashboard, name="seller_dashboard"),
]
