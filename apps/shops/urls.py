from django.urls import path

from . import views

app_name = "shops"

urlpatterns = [
    path("categories/", views.categories, name="categories"),
    path("categories/<slug:slug>/", views.category_detail, name="category"),
    path("map/", views.map_view, name="map"),
    path("geojson/", views.geojson, name="geojson"),
    path("<slug:slug>/", views.detail, name="detail"),
]
