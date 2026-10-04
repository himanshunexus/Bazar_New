from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def seller_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not getattr(request.user, "is_seller", False) or not hasattr(request.user, "shop"):
            messages.error(request, "Seller access is required.")
            return redirect("core:home")
        return view_func(request, *args, **kwargs)

    return wrapper
