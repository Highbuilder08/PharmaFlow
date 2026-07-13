from django import forms
from django.db import models
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Pharmacy, User


class SignUpForm(UserCreationForm):

    class RequestedRole(models.TextChoices):
        OWNER = User.Role.OWNER, "점주"
        PHARMACIST = User.Role.PHARMACIST, "약사"
        STAFF = User.Role.STAFF, "직원"

    email = forms.EmailField(
        required=True,
        label="이메일",
    )

    requested_role = forms.ChoiceField(
        choices=RequestedRole.choices,
        label="가입 유형",
    )

    business_number = forms.CharField(
        required=False,
        max_length=20,
        label="사업자등록번호",
        help_text="점주 신청을 선택한 경우 입력하세요.",
    )

    pharmacy_place_id = forms.CharField(
        widget=forms.HiddenInput(),
    )

    pharmacy_name = forms.CharField(
        widget=forms.HiddenInput(),
    )

    pharmacy_address = forms.CharField(
        widget=forms.HiddenInput(),
    )

    pharmacy_phone = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    pharmacy_latitude = forms.DecimalField(
        max_digits=10,
        decimal_places=7,
        widget=forms.HiddenInput(),
    )

    pharmacy_longitude = forms.DecimalField(
        max_digits=10,
        decimal_places=7,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = User

        fields = (
            "username",
            "name",
            "email",
            "password1",
            "password2",
        )

        labels = {
            "username": "아이디",
            "name": "이름",
            "email": "이메일",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs["class"] = "form-control"

        self.fields["requested_role"].widget.attrs["class"] = "form-select"

        self.order_fields(
            [
                "username",
                "password1",
                "password2",
                "name",
                "email",
                "requested_role",
                "business_number",
                "pharmacy_place_id",
                "pharmacy_name",
                "pharmacy_address",
                "pharmacy_phone",
                "pharmacy_latitude",
                "pharmacy_longitude",
            ]
        )

    def clean(self):
        cleaned_data = super().clean()

        requested_role = cleaned_data.get("requested_role")
        place_id = cleaned_data.get("pharmacy_place_id")
        pharmacy_name = cleaned_data.get("pharmacy_name")
        business_number = cleaned_data.get("business_number")

        if not place_id or not pharmacy_name:
            raise forms.ValidationError(
                "검색 결과에서 소속 약국을 선택해 주세요."
            )

        if (
            requested_role == User.Role.OWNER
            and not business_number
        ):
            self.add_error(
                "business_number",
                "점주 권한 신청에는 사업자등록번호가 필요합니다.",
            )

        return cleaned_data


class PharmacyForm(forms.ModelForm):

    class Meta:
        model = Pharmacy

        fields = (
            "business_number",
            "business_name",
            "pharmacy_name",
            "owner_name",
            "address",
            "phone",
            "email",
            "status",
        )

        widgets = {
            "business_number": forms.TextInput(
                attrs={"placeholder": "예: 123-45-67890"}
            ),
            "business_name": forms.TextInput(
                attrs={"placeholder": "사업자명을 입력하세요"}
            ),
            "pharmacy_name": forms.TextInput(
                attrs={"placeholder": "약국명을 입력하세요"}
            ),
            "owner_name": forms.TextInput(
                attrs={"placeholder": "대표자명을 입력하세요"}
            ),
            "address": forms.TextInput(
                attrs={"placeholder": "주소를 입력하세요"}
            ),
            "phone": forms.TextInput(
                attrs={"placeholder": "예: 02-1234-5678"}
            ),
            "email": forms.EmailInput(
                attrs={"placeholder": "example@example.com"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        self.fields["status"].widget.attrs["class"] = "form-select"


class ApprovedAuthenticationForm(AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        self.fields["username"].widget.attrs["placeholder"] = "아이디"
        self.fields["password"].widget.attrs["placeholder"] = "비밀번호"

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if user.is_superuser:
            return

        if not user.is_approved:
            if user.role == User.Role.OWNER:
                message = (
                    "점주 권한 승인 대기 중입니다.\n\n"
                    "시스템 관리자가 사업자 정보를 확인한 후 "
                    "로그인할 수 있습니다."
                )
            else:
                message = (
                    "소속 약국 관리자 승인 대기 중입니다.\n\n"
                    "해당 약국 점주의 승인 후 로그인할 수 있습니다."
                )

            raise forms.ValidationError(
                message,
                code="not_approved",
            )
