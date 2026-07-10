from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Pharmacy, User


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = (
        "pharmacy_name",
        "business_name",
        "owner_name",
        "phone",
        "status",
    )

    search_fields = (
        "pharmacy_name",
        "business_name",
    )

    list_filter = (
        "status",
    )


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        "username",
        "name",
        "role",
        "pharmacy",
        "is_approved",
        "is_staff",
    )

    search_fields = (
        "username",
        "name",
    )

    list_filter = (
        "role",
        "is_approved",
    )
