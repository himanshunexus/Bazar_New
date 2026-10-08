from django.urls import path

from . import views

app_name = "shops"

urlpatterns = [
    path("", views.shop_map_api, name="shop_map_api"),
    path("categories/", views.categories, name="categories"),
    path("categories/<slug:slug>/", views.category_detail, name="category"),
    path("map/", views.map_view, name="map"),
    path("geojson/", views.geojson, name="geojson"),
    path("<slug:slug>/", views.detail, name="detail"),
]
