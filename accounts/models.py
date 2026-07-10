from django.contrib.auth.models import AbstractUser
from django.db import models


class Pharmacy(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "운영 중"
        SUSPENDED = "SUSPENDED", "휴업"
        CLOSED = "CLOSED", "폐업"

    business_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="사업자등록번호"
    )

    business_name = models.CharField(
        max_length=100,
        verbose_name="사업자명"
    )

    pharmacy_name = models.CharField(
        max_length=100,
        verbose_name="약국명"
    )

    owner_name = models.CharField(
        max_length=50,
        verbose_name="대표자명"
    )

    address = models.CharField(
        max_length=255,
        verbose_name="주소"
    )

    phone = models.CharField(
        max_length=20,
        verbose_name="대표 연락처"
    )

    email = models.EmailField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pharmacy"

    def __str__(self):
        return self.pharmacy_name


class User(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "관리자"
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
    )

    name = models.CharField(max_length=50)

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
    )

    license_number = models.CharField(
        max_length=50,
        blank=True
    )

    is_approved = models.BooleanField(
        default=True
    )

    REQUIRED_FIELDS = ["name", "email"]

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return self.username
