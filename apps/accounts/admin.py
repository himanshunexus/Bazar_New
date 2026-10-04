from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Address, User


@admin.register(User)
class BazarUserAdmin(UserAdmin):
    list_display = ("username", "email", "phone", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "phone")
    fieldsets = UserAdmin.fieldsets + (("BAZAR", {"fields": ("role", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("BAZAR", {"fields": ("email", "role", "phone")}),)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "city", "pincode", "is_default")
    list_filter = ("city", "pincode", "is_default")
    search_fields = ("full_name", "phone", "line1", "city", "pincode")
