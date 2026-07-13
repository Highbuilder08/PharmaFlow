from django.contrib.auth.models import AbstractUser
from django.db import models


class Pharmacy(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "운영 중"
        SUSPENDED = "SUSPENDED", "휴업"
        CLOSED = "CLOSED", "폐업"

    class DataSource(models.TextChoices):
        KAKAO = "KAKAO", "카카오 지도"
        MANUAL = "MANUAL", "직접 등록"

    business_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="사업자등록번호",
    )

    business_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="사업자명",
    )

    pharmacy_name = models.CharField(
        max_length=100,
        verbose_name="약국명",
    )

    owner_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="대표자명",
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="주소",
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="대표 연락처",
    )

    email = models.EmailField(
        blank=True,
        verbose_name="이메일",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="운영 상태",
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="위도",
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="경도",
    )

    external_place_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        verbose_name="외부 장소 ID",
    )

    data_source = models.CharField(
        max_length=20,
        choices=DataSource.choices,
        default=DataSource.MANUAL,
        verbose_name="데이터 출처",
    )

    is_verified = models.BooleanField(
        default=False,
        verbose_name="위치 정보 확인",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="등록일",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일",
    )

    class Meta:
        db_table = "pharmacy"
        verbose_name = "약국"
        verbose_name_plural = "약국"

    def __str__(self):
        return self.pharmacy_name


class User(AbstractUser):

    class Role(models.TextChoices):
        OWNER = "OWNER", "점주"
        PHARMACIST = "PHARMACIST", "약사"
        STAFF = "STAFF", "직원"

    first_name = None
    last_name = None

    pharmacy = models.ForeignKey(
        Pharmacy,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
        verbose_name="소속 약국",
    )

    name = models.CharField(
        max_length=50,
        verbose_name="이름",
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="연락처",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
        verbose_name="역할",
    )

    license_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="약사 면허번호",
    )

    is_approved = models.BooleanField(
        default=False,
        verbose_name="승인 여부",
    )

    REQUIRED_FIELDS = [
        "name",
        "email",
    ]

    class Meta:
        db_table = "accounts_user"
        verbose_name = "사용자"
        verbose_name_plural = "사용자"

    def __str__(self):
        return self.username


class PharmacyOwnershipRequest(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "승인 대기"
        APPROVED = "APPROVED", "승인 완료"
        REJECTED = "REJECTED", "거절"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ownership_requests",
        verbose_name="신청자",
    )

    pharmacy = models.ForeignKey(
        Pharmacy,
        on_delete=models.CASCADE,
        related_name="ownership_requests",
        verbose_name="신청 약국",
    )

    business_number = models.CharField(
        max_length=20,
        verbose_name="사업자등록번호",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="처리 상태",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="신청일",
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="처리일",
    )

    class Meta:
        db_table = "pharmacy_ownership_request"
        verbose_name = "점주 권한 신청"
        verbose_name_plural = "점주 권한 신청"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "pharmacy"),
                name="unique_user_pharmacy_ownership_request",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.pharmacy}"
