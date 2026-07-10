from django import forms
from .models import Prescription, Consultation, ConsultationComment

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['patient_name', 'ssn_front', 'phone', 'symptoms', 'prescription_date']

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['title', 'content']