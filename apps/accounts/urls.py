from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.SafeLoginView.as_view(), name="login"),
    path("password/change/", auth_views.PasswordChangeView.as_view(template_name="accounts/password_change.html", success_url=reverse_lazy("accounts:password_change_done")), name="password_change"),
    path("password/change/done/", auth_views.PasswordChangeDoneView.as_view(template_name="accounts/password_change_done.html"), name="password_change_done"),
    path("logout/", views.SafeLogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("addresses/new/", views.address_upsert, name="address_new"),
    path("addresses/<int:pk>/", views.address_upsert, name="address_edit"),
    path("addresses/<int:pk>/default/", views.address_set_default, name="address_default"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
]
