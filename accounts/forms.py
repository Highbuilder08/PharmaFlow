# ==================================================
# 파일 역할: 회원가입과 사용자·약국 정보 입력값을 검증하는 폼 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError

from .models import Pharmacy, User
from .validators import normalize_business_number, validate_business_number


# 회원가입 입력값과 HIRA에서 선택한 약국 정보를 검증한다.
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
        max_length=12,
        label="사업자등록번호",
        validators=[validate_business_number],
        help_text=(
            "점주로 가입하는 경우 000-00-00000 형식으로 "
            "입력하세요."
        ),
        widget=forms.TextInput(
            attrs={
                "class": "form-control business-number-input",
                "placeholder": "000-00-00000",
                "inputmode": "numeric",
                "maxlength": "12",
                "autocomplete": "off",
            }
        ),
    )

    business_name = forms.CharField(
        required=False,
        max_length=100,
        label="사업자명",
        help_text="점주로 가입하는 경우에만 입력하세요.",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "사업자명",
                "autocomplete": "organization",
            }
        ),
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

    # Meta 클래스의 데이터 구조와 동작을 정의한다.
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
            "business_name",
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

    # __init__ 기능을 처리한다.
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
        self.fields["business_number"].widget.attrs.update(
            {
                "class": "form-control business-number-input",
                "placeholder": "000-00-00000",
                "inputmode": "numeric",
                "maxlength": "12",
                "autocomplete": "off",
            }
        )
        self.fields["business_name"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "사업자명",
                "autocomplete": "organization",
            }
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
                "business_name",
                "pharmacy_external_id",
                "pharmacy_name",
                "pharmacy_address",
                "pharmacy_phone",
                "pharmacy_latitude",
                "pharmacy_longitude",
            ]
        )

    # 회원가입 이메일을 정규화하고 기존 계정과 중복되는지 검사한다.
    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("이미 가입된 이메일입니다.")

        return email

    # business_number 필드의 입력값을 추가로 검증한다.
    def clean_business_number(self):
        business_number = self.cleaned_data.get(
            "business_number",
            "",
        )

        if not business_number:
            return ""

        return normalize_business_number(business_number)

    # business_name 필드의 앞뒤 공백을 제거한다.
    def clean_business_name(self):
        business_name = self.cleaned_data.get(
            "business_name",
            "",
        )

        return business_name.strip()

    # 여러 필드 사이의 관계를 종합적으로 검증한다.
    def clean(self):
        cleaned_data = super().clean()

        requested_role = cleaned_data.get("requested_role")
        external_id = cleaned_data.get("pharmacy_external_id")
        pharmacy_name = cleaned_data.get("pharmacy_name")
        business_number = cleaned_data.get("business_number")
        business_name = cleaned_data.get("business_name")

        if not external_id or not pharmacy_name:
            raise forms.ValidationError(
                "약국 검색 결과에서 소속 약국을 선택해 주세요."
            )

        if requested_role == User.Role.OWNER:
            if not business_number:
                self.add_error(
                    "business_number",
                    "점주 권한 신청에는 사업자등록번호가 필요합니다.",
                )

            if not business_name:
                self.add_error(
                    "business_name",
                    "점주 권한 신청에는 사업자명이 필요합니다.",
                )

        return cleaned_data


# 비밀번호 재설정 요청 시 아이디와 이메일이 모두 일치하는 계정만 조회한다.
class CustomPasswordResetForm(PasswordResetForm):
    username = forms.CharField(
        label="아이디",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "아이디를 입력하세요.",
                "autocomplete": "username",
            }
        ),
    )

    email = forms.EmailField(
        label="이메일",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "회원가입 시 인증한 이메일을 입력하세요.",
                "autocomplete": "email",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username", "").strip()
        email = cleaned_data.get("email", "").strip().lower()

        if username and email:
            account_exists = User.objects.filter(
                username=username,
                email__iexact=email,
                is_active=True,
            ).exists()

            if not account_exists:
                raise ValidationError(
                    "아이디와 이메일이 일치하는 계정을 찾을 수 없습니다."
                )

        cleaned_data["username"] = username
        cleaned_data["email"] = email
        return cleaned_data

    def get_users(self, email):
        """입력한 아이디와 이메일이 모두 일치하는 활성 사용자만 반환한다."""
        username = self.cleaned_data.get("username", "").strip()

        return (
            user
            for user in User.objects.filter(
                username=username,
                email__iexact=email,
                is_active=True,
            )
            if user.has_usable_password()
        )


# 약국의 사업자 및 연락처 정보를 등록하거나 수정한다.
class PharmacyUpdateForm(forms.ModelForm):

    # Meta 클래스의 데이터 구조와 동작을 정의한다.
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
            "business_number": forms.TextInput(
                attrs={
                    "class": "form-control business-number-input",
                    "placeholder": "000-00-00000",
                    "inputmode": "numeric",
                    "maxlength": "12",
                    "autocomplete": "off",
                }
            ),
            "business_name": forms.TextInput(),
            "pharmacy_name": forms.TextInput(),
            "owner_name": forms.TextInput(),
            "address": forms.TextInput(),
            "phone": forms.TextInput(),
            "email": forms.EmailInput(),
            "status": forms.Select(),
            # 좌표는 지도 표시와 기존 위치 보존에 사용하므로 화면에는 숨긴다.
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    # __init__ 기능을 처리한다.
    def __init__(self, *args, current_user=None, **kwargs):
        # 현재 로그인 사용자를 별도로 받아 약국 이메일과 계정 이메일을 연결한다.
        self.current_user = current_user
        super().__init__(*args, **kwargs)

        # 기존 약국 이메일이 비어 있으면 로그인 계정 이메일을 초기값으로 표시한다.
        # POST 요청(self.is_bound=True)에서는 사용자가 제출한 값을 덮어쓰지 않는다.
        if (
            self.current_user is not None
            and not self.is_bound
            and not (self.instance and self.instance.email)
        ):
            # ModelForm은 instance에서 만든 self.initial 값을 우선 사용하므로
            # field.initial만 설정하면 빈 Pharmacy.email 값에 가려질 수 있다.
            # 화면에 계정 이메일이 확실히 표시되도록 폼 초기값을 직접 갱신한다.
            account_email = (self.current_user.email or "").strip().lower()
            self.initial["email"] = account_email
            self.fields["email"].initial = account_email

        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

        self.fields["business_number"].widget.attrs.update(
            {
                "class": "form-control business-number-input",
                "placeholder": "000-00-00000",
                "inputmode": "numeric",
                "maxlength": "12",
                "autocomplete": "off",
            }
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

    # 약국 이메일을 정규화하고 다른 사용자 계정과의 중복 여부를 검사한다.
    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()

        if not email:
            return ""

        duplicate_users = User.objects.filter(email__iexact=email)

        # 현재 로그인 사용자가 자신의 기존 이메일을 그대로 저장하는 것은 허용한다.
        if self.current_user is not None:
            duplicate_users = duplicate_users.exclude(pk=self.current_user.pk)

        if duplicate_users.exists():
            raise ValidationError("다른 계정에서 이미 사용 중인 이메일입니다.")

        return email

    def save(self, commit=True):
        """약국 이메일과 현재 로그인 사용자의 이메일을 함께 저장한다."""
        pharmacy = super().save(commit=commit)

        if self.current_user is not None:
            new_email = self.cleaned_data.get("email", "").strip().lower()

            if self.current_user.email != new_email:
                self.current_user.email = new_email

                if commit:
                    self.current_user.save(update_fields=["email"])

        return pharmacy

    # business_number 필드의 입력값을 추가로 검증한다.
    def clean_business_number(self):
        business_number = self.cleaned_data.get(
            "business_number",
        )

        if not business_number:
            return None

        return normalize_business_number(business_number)

    # pharmacy_name 필드의 입력값을 추가로 검증한다.
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

    # 여러 필드 사이의 관계를 종합적으로 검증한다.
    def clean(self):
        cleaned_data = super().clean()

        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if (latitude is None) != (longitude is None):
            raise forms.ValidationError(
                "위도와 경도는 함께 입력해야 합니다."
            )

        return cleaned_data


# ApprovedAuthenticationForm 클래스의 데이터 구조와 동작을 정의한다.
class ApprovedAuthenticationForm(AuthenticationForm):

    # __init__ 기능을 처리한다.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        self.fields["username"].widget.attrs["placeholder"] = "아이디"
        self.fields["password"].widget.attrs["placeholder"] = "비밀번호"

    # confirm_login_allowed 기능을 처리한다.
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


# 점주 또는 관리자가 직원을 직접 추가할 때 사용하는 폼이다.
class StaffCreateForm(UserCreationForm):

    # Meta 클래스의 데이터 구조와 동작을 정의한다.
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

    # __init__ 기능을 처리한다.
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


    def clean_email(self):
        """직원 계정 이메일을 정규화하고 중복 가입을 막는다."""
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise ValidationError("이메일을 입력해 주세요.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("이미 사용 중인 이메일입니다.")
        return email


# 소속 직원의 계정 정보를 수정할 때 사용하는 폼이다.
class StaffUpdateForm(forms.ModelForm):

    # Meta 클래스의 데이터 구조와 동작을 정의한다.
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


    def clean_email(self):
        """다른 사용자와 이메일이 중복되지 않도록 검사한다."""
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise ValidationError("이메일을 입력해 주세요.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("이미 사용 중인 이메일입니다.")
        return email


# 마이페이지의 민감한 기능에 앞서 현재 비밀번호를 확인한다.
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

    # __init__ 기능을 처리한다.
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    # password 필드의 입력값을 추가로 검증한다.
    def clean_password(self):
        password = self.cleaned_data["password"]

        if self.user is None or not self.user.check_password(password):
            raise forms.ValidationError(
                "비밀번호가 올바르지 않습니다."
            )

        return password


# 사용자가 본인의 연락처, 프로필 이미지와 비밀번호를 수정한다.
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

    # Meta 클래스의 데이터 구조와 동작을 정의한다.
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

    def clean_email(self):
        """내 계정 이외의 사용자와 이메일 중복을 막는다."""
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise ValidationError("이메일을 입력해 주세요.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("이미 사용 중인 이메일입니다.")
        return email

    # 여러 필드 사이의 관계를 종합적으로 검증한다.
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

    # 검증된 입력값을 모델 객체에 반영하여 저장한다.
    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password1")

        if new_password:
            user.set_password(new_password)

        if commit:
            user.save()

        return user

