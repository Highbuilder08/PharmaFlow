from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Pharmacy, User


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = (
        "pharmacy_name",
        "business_number",
        "business_name",
        "owner_name",
        "phone",
        "status",
    )

    search_fields = (
        "pharmacy_name",
        "business_name",
        "business_number",
        "owner_name",
    )

    list_filter = (
        "status",
    )

    ordering = (
        "pharmacy_name",
    )

    list_per_page = 20


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "name",
        "role",
        "pharmacy",
        "is_approved",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "name",
        "email",
        "phone",
    )

    list_filter = (
        "role",
        "is_approved",
        "is_active",
        "is_staff",
    )

    ordering = (
        "username",
    )

    readonly_fields = (
        "last_login",
        "date_joined",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "password",
                )
            },
        ),
        (
            "개인 정보",
            {
                "fields": (
                    "name",
                    "email",
                    "phone",
                )
            },
        ),
        (
            "약국 정보",
            {
                "fields": (
                    "pharmacy",
                    "role",
                    "license_number",
                    "is_approved",
                )
            },
        ),
        (
            "권한",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "접속 기록",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "name",
                    "email",
                    "phone",
                    "pharmacy",
                    "role",
                    "license_number",
                    "is_approved",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )
    
    actions = (
    "approve_users",
    "cancel_approval",
    )
    
    @admin.action(description="선택한 사용자를 승인")
    def approve_users(self, request, queryset):
        updated = queryset.update(is_approved=True)
        
        self.message_user(
            request,
            f"{updated}명의 사용자를 승인했습니다.",
            )
    
    
    @admin.action(description="선택한 사용자의 승인을 취소")
    def cancel_approval(self, request, queryset):
        updated = queryset.update(is_approved=False)
        
        self.message_user(
            request,
            f"{updated}명의 사용자 승인을 취소했습니다.",
            )

