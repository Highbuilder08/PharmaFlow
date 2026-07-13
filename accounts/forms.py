from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Pharmacy, User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="이메일",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "name",
            "email",
            "pharmacy",
            "password1",
            "password2",
        )

        labels = {
            "username": "아이디",
            "name": "이름",
            "email": "이메일",
            "pharmacy": "소속 약국",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": "form-control",
                }
            )

        self.fields["pharmacy"].required = True
        self.fields["pharmacy"].empty_label = "소속 약국을 선택하세요"
        self.fields["pharmacy"].widget.attrs["class"] = "form-select"

        self.order_fields(
            [
                "username",
                "password1",
                "password2",
                "name",
                "email",
                "pharmacy",
            ]
        )


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
                attrs={
                    "placeholder": "예: 123-45-67890",
                }
            ),
            "business_name": forms.TextInput(
                attrs={
                    "placeholder": "사업자명을 입력하세요",
                }
            ),
            "pharmacy_name": forms.TextInput(
                attrs={
                    "placeholder": "약국명을 입력하세요",
                }
            ),
            "owner_name": forms.TextInput(
                attrs={
                    "placeholder": "대표자명을 입력하세요",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "placeholder": "주소를 입력하세요",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "placeholder": "예: 02-1234-5678",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "example@example.com",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": "form-control",
                }
            )

        self.fields["status"].widget.attrs["class"] = "form-select"


class ApprovedAuthenticationForm(AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": "form-control",
                }
            )
            
        self.fields["username"].widget.attrs["placeholder"] = "아이디"
        self.fields["password"].widget.attrs["placeholder"] = "비밀번호"

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if not user.is_superuser and not user.is_approved:
            raise forms.ValidationError(
                "관리자 승인 대기 중인 계정입니다.",
                code="not_approved",
            )
