from django import forms
from .models import Consultation, ConsultationComment

# prescriptions/forms.py에 있던 ConsultationForm을 잘라내서 이곳으로 옮깁니다.
class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['title', 'content']