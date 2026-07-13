# prescriptions/forms.py
from django import forms
from .models import Prescription, Consultation, ConsultationComment

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['patient_name', 'ssn_front', 'phone', 'symptoms', 'prescription_date']
        
        # 👇 이 부분(widgets)을 추가해 주세요!
        widgets = {
            'prescription_date': forms.DateInput(attrs={'type': 'date'}),
        }

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['title', 'content']