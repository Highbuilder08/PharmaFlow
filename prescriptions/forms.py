# prescriptions/forms.py
from django import forms
from .models import Prescription, Consultation, ConsultationComment, PrescriptionItem
from inventory.models import Medicine

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['patient_name', 'ssn_front', 'phone', 'symptoms', 'prescription_date']
        
        widgets = {
            'prescription_date': forms.DateInput(attrs={'type': 'date'}),
        }

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['title', 'content']
        
class PrescriptionItemForm(forms.ModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ['medicine', 'dosage', 'duration', 'total_quantity']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. 재고(stock)가 1 이상인 약품만 가져옵니다.
        available_medicines = Medicine.objects.filter(stock__gt=0)
        self.fields['medicine'].queryset = available_medicines
        
        # 2. 만약 선택 가능한 약품이 0개라면?
        if not available_medicines.exists():
            self.fields['medicine'].empty_label = "선택 가능한 약품이 없습니다"
            # 입력을 못 하도록 비활성화(disabled) 처리
            self.fields['medicine'].widget.attrs['disabled'] = 'disabled' 
        else:
            self.fields['medicine'].empty_label = "약을 선택하세요"