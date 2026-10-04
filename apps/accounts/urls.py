from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.SafeLoginView.as_view(), name="login"),
    path("logout/", views.SafeLogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("addresses/new/", views.address_upsert, name="address_new"),
    path("addresses/<int:pk>/", views.address_upsert, name="address_edit"),
]
