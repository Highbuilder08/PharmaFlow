from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError

from .models import Pharmacy, User


class SignUpForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        label="이메일",
    )

    profile_image = forms.ImageField(
        required=False,
        label="프로필 사진",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
            }
        ),
    )

    requested_role = forms.ChoiceField(
        choices=(
            (User.Role.OWNER, "점주"),
            (User.Role.PHARMACIST, "약사"),
            (User.Role.STAFF, "직원"),
        ),
        label="가입 유형",
    )

    business_number = forms.CharField(
        required=False,
        max_length=20,
        label="사업자등록번호",
        help_text="점주로 가입하는 경우에만 입력하세요.",
    )

    pharmacy_external_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    pharmacy_name = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    pharmacy_address = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    pharmacy_phone = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    pharmacy_latitude = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        widget=forms.HiddenInput(),
    )

    pharmacy_longitude = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=7,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = User

        fields = (
            "username",
            "password1",
            "password2",
            "name",
            "email",
            "profile_image",
            "requested_role",
            "business_number",
            "pharmacy_external_id",
            "pharmacy_name",
            "pharmacy_address",
            "pharmacy_phone",
            "pharmacy_latitude",
            "pharmacy_longitude",
        )

        labels = {
            "username": "아이디",
            "name": "이름",
            "email": "이메일",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field.widget, forms.HiddenInput):
                continue

            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

        self.fields["username"].widget.attrs["placeholder"] = "아이디"
        self.fields["password1"].widget.attrs["placeholder"] = "비밀번호"
        self.fields["password2"].widget.attrs["placeholder"] = (
            "비밀번호 확인"
        )
        self.fields["name"].widget.attrs["placeholder"] = "이름"
        self.fields["email"].widget.attrs["placeholder"] = "이메일"
        self.fields["business_number"].widget.attrs["placeholder"] = (
            "사업자등록번호"
        )

        self.order_fields(
            [
                "username",
                "password1",
                "password2",
                "name",
                "email",
                "profile_image",
                "requested_role",
                "business_number",
                "pharmacy_external_id",
                "pharmacy_name",
                "pharmacy_address",
                "pharmacy_phone",
                "pharmacy_latitude",
                "pharmacy_longitude",
            ]
        )

    def clean_business_number(self):
        business_number = self.cleaned_data.get(
            "business_number",
            "",
        )

        return business_number.strip()

    def clean(self):
        cleaned_data = super().clean()

        requested_role = cleaned_data.get("requested_role")
        external_id = cleaned_data.get("pharmacy_external_id")
        pharmacy_name = cleaned_data.get("pharmacy_name")
        business_number = cleaned_data.get("business_number")

        if not external_id or not pharmacy_name:
            raise forms.ValidationError(
                "약국 검색 결과에서 소속 약국을 선택해 주세요."
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


class PharmacyUpdateForm(forms.ModelForm):

    class Meta:
        model = Pharmacy

        fields = [
            "business_number",
            "business_name",
            "pharmacy_name",
            "owner_name",
            "address",
            "phone",
            "email",
            "status",
            "latitude",
            "longitude",
        ]

        labels = {
            "business_number": "사업자등록번호",
            "business_name": "사업자명",
            "pharmacy_name": "약국명",
            "owner_name": "대표자명",
            "address": "주소",
            "phone": "대표 연락처",
            "email": "이메일",
            "status": "운영 상태",
            "latitude": "위도",
            "longitude": "경도",
        }

        widgets = {
            "business_number": forms.TextInput(),
            "business_name": forms.TextInput(),
            "pharmacy_name": forms.TextInput(),
            "owner_name": forms.TextInput(),
            "address": forms.TextInput(),
            "phone": forms.TextInput(),
            "email": forms.EmailInput(),
            "status": forms.Select(),
            "latitude": forms.NumberInput(
                attrs={
                    "step": "0.0000001",
                }
            ),
            "longitude": forms.NumberInput(
                attrs={
                    "step": "0.0000001",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

        self.fields["business_number"].widget.attrs["placeholder"] = (
            "사업자등록번호"
        )
        self.fields["business_name"].widget.attrs["placeholder"] = (
            "사업자명"
        )
        self.fields["pharmacy_name"].widget.attrs["placeholder"] = (
            "약국명"
        )
        self.fields["owner_name"].widget.attrs["placeholder"] = (
            "대표자명"
        )
        self.fields["address"].widget.attrs["placeholder"] = "주소"
        self.fields["phone"].widget.attrs["placeholder"] = "대표 연락처"
        self.fields["email"].widget.attrs["placeholder"] = "이메일"

    def clean_business_number(self):
        business_number = self.cleaned_data.get(
            "business_number",
        )

        if not business_number:
            return None

        return business_number.strip()

    def clean_pharmacy_name(self):
        pharmacy_name = self.cleaned_data.get(
            "pharmacy_name",
            "",
        ).strip()

        if not pharmacy_name:
            raise forms.ValidationError(
                "약국명을 입력해 주세요."
            )

        return pharmacy_name

    def clean(self):
        cleaned_data = super().clean()

        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if (latitude is None) != (longitude is None):
            raise forms.ValidationError(
                "위도와 경도는 함께 입력해야 합니다."
            )

        return cleaned_data


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
                    "소속 약국 점주의 승인 대기 중입니다.\n\n"
                    "해당 약국 점주의 승인 후 로그인할 수 있습니다."
                )

            raise forms.ValidationError(
                message,
                code="not_approved",
            )


class StaffCreateForm(UserCreationForm):

    class Meta:
        model = User

        fields = (
            "username",
            "password1",
            "password2",
            "name",
            "email",
            "phone",
            "profile_image",
        )

        labels = {
            "username": "아이디",
            "name": "이름",
            "email": "이메일",
            "phone": "연락처",
            "profile_image": "프로필 사진",
        }

        widgets = {
            "profile_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        self.order_fields(
            [
                "username",
                "password1",
                "password2",
                "name",
                "email",
                "phone",
                "profile_image",
            ]
        )


class StaffUpdateForm(forms.ModelForm):

    class Meta:
        model = User

        fields = (
            "name",
            "email",
            "phone",
            "profile_image",
            "is_approved",
        )

        labels = {
            "name": "이름",
            "email": "이메일",
            "phone": "연락처",
            "profile_image": "프로필 사진",
            "is_approved": "근무 승인",
        }

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "profile_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
            "is_approved": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


class PasswordConfirmForm(forms.Form):

    password = forms.CharField(
        label="현재 비밀번호",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "현재 비밀번호",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]

        if self.user is None or not self.user.check_password(password):
            raise forms.ValidationError(
                "비밀번호가 올바르지 않습니다."
            )

        return password


class MyPageUpdateForm(forms.ModelForm):

    new_password1 = forms.CharField(
        required=False,
        label="새 비밀번호",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "변경할 때만 입력하세요.",
                "autocomplete": "new-password",
            }
        ),
        help_text="비밀번호를 변경하지 않으려면 비워 두세요.",
    )

    new_password2 = forms.CharField(
        required=False,
        label="새 비밀번호 확인",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "새 비밀번호를 다시 입력하세요.",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User

        fields = (
            "name",
            "email",
            "phone",
            "profile_image",
        )

        labels = {
            "name": "이름",
            "email": "이메일",
            "phone": "연락처",
            "profile_image": "프로필 사진",
        }

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "profile_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 or password2:
            if not password1:
                self.add_error(
                    "new_password1",
                    "새 비밀번호를 입력해 주세요.",
                )

            if not password2:
                self.add_error(
                    "new_password2",
                    "새 비밀번호 확인을 입력해 주세요.",
                )

            if password1 and password2 and password1 != password2:
                self.add_error(
                    "new_password2",
                    "새 비밀번호가 서로 일치하지 않습니다.",
                )

            if password1 and password1 == password2:
                try:
                    password_validation.validate_password(
                        password1,
                        self.instance,
                    )
                except ValidationError as errors:
                    self.add_error(
                        "new_password1",
                        errors,
                    )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password1")

        if new_password:
            user.set_password(new_password)

        if commit:
            user.save()

        return user

