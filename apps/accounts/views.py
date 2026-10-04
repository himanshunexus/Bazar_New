from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from .forms import AddressForm, CustomerRegistrationForm, SellerRegistrationForm
from .models import Address


def _safe_next(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return next_url
    return reverse_lazy("core:home")


class SafeLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return _safe_next(self.request)


class SafeLogoutView(LogoutView):
    next_page = reverse_lazy("core:home")


@require_http_methods(["GET", "POST"])
def register(request):
    role = request.POST.get("role") or request.GET.get("role") or "customer"
    form_class = SellerRegistrationForm if role == "seller" else CustomerRegistrationForm
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to BAZAR.")
        return redirect(_safe_next(request))
    return render(request, "accounts/register.html", {"form": form, "role": role})


@login_required
def profile(request):
    addresses = request.user.addresses.all()
    return render(request, "accounts/profile.html", {"addresses": addresses})


@login_required
@require_http_methods(["GET", "POST"])
def address_upsert(request, pk=None):
    address = get_object_or_404(Address, pk=pk, user=request.user) if pk else None
    form = AddressForm(request.POST or None, instance=address)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        saved.user = request.user
        saved.save()
        messages.success(request, "Address saved.")
        return redirect("accounts:profile")
    return render(request, "accounts/address_form.html", {"form": form, "address": address})
