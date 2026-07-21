# ==================================================
# 파일 역할: Django 관리자 페이지에서 계정 관련 모델을 관리하기 위한 설정 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Pharmacy, PharmacyOwnershipRequest, User
from django.db import transaction
from django.utils import timezone


# PharmacyAdmin 클래스의 데이터 구조와 동작을 정의한다.
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


# CustomUserAdmin 클래스의 데이터 구조와 동작을 정의한다.
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
    
    # approve_users 기능을 처리한다.
    @admin.action(description="선택한 사용자를 승인")
    def approve_users(self, request, queryset):
        # 점주는 사업자 정보 검증이 필요하므로 점주 권한 신청 메뉴에서만 승인한다.
        target = queryset.exclude(role=User.Role.OWNER)
        updated = target.update(is_approved=True)
        skipped = queryset.filter(role=User.Role.OWNER).count()

        self.message_user(
            request,
            f"{updated}명의 사용자를 승인했습니다. 점주 {skipped}명은 별도 승인 대상입니다.",
        )
    
    # cancel_approval 기능을 처리한다.
    @admin.action(description="선택한 사용자의 승인을 취소")
    def cancel_approval(self, request, queryset):
        updated = queryset.update(is_approved=False)
        
        self.message_user(
            request,
            f"{updated}명의 사용자 승인을 취소했습니다.",
            )


# PharmacyOwnershipRequestAdmin 클래스의 데이터 구조와 동작을 정의한다.
@admin.register(PharmacyOwnershipRequest)
class PharmacyOwnershipRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "pharmacy",
        "business_number",
        "status",
        "created_at",
        "processed_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__name",
        "pharmacy__pharmacy_name",
        "business_number",
    )

    actions = (
        "approve_requests",
        "reject_requests",
    )

    # approve_requests 기능을 처리한다.
    @admin.action(description="선택한 점주 신청 승인")
    def approve_requests(self, request, queryset):
        approved_count = 0
        skipped_count = 0

        with transaction.atomic():
            pending_requests = (
                queryset.select_for_update()
                .select_related("user", "pharmacy")
                .filter(status=PharmacyOwnershipRequest.Status.PENDING)
            )
            for ownership_request in pending_requests:
                pharmacy = ownership_request.pharmacy
                business_number = ownership_request.business_number.strip()
                duplicate = Pharmacy.objects.filter(
                    business_number=business_number,
                ).exclude(pk=pharmacy.pk).exists()
                if duplicate:
                    skipped_count += 1
                    continue

                ownership_request.status = PharmacyOwnershipRequest.Status.APPROVED
                ownership_request.processed_at = timezone.now()
                ownership_request.save(update_fields=["status", "processed_at"])

                user = ownership_request.user
                user.role = User.Role.OWNER
                user.pharmacy = pharmacy
                user.is_approved = True
                user.save(update_fields=["role", "pharmacy", "is_approved"])

                pharmacy.business_number = business_number
                pharmacy.business_name = ownership_request.business_name.strip()
                if not pharmacy.owner_name:
                    pharmacy.owner_name = user.name
                pharmacy.save(
                    update_fields=[
                        "business_number",
                        "business_name",
                        "owner_name",
                        "updated_at",
                    ]
                )
                approved_count += 1

        self.message_user(
            request,
            f"{approved_count}건 승인, {skipped_count}건 중복으로 건너뛰었습니다.",
        )

    # reject_requests 기능을 처리한다.
    @admin.action(description="선택한 점주 신청 거절")
    def reject_requests(self, request, queryset):
        pending = queryset.filter(
            status=PharmacyOwnershipRequest.Status.PENDING,
        )
        user_ids = list(pending.values_list("user_id", flat=True))
        updated = pending.update(
            status=PharmacyOwnershipRequest.Status.REJECTED,
            processed_at=timezone.now(),
        )
        User.objects.filter(pk__in=user_ids).update(is_approved=False)

        self.message_user(
            request,
            f"{updated}건의 점주 신청을 거절했습니다.",
        )