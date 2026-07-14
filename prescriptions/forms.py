# prescriptions/forms.py
from django import forms
from .models import Prescription, PrescriptionItem
from inventory.models import Medicine

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['pharmacy', 'patient_name', 'ssn_front', 'phone', 'symptoms', 'prescription_date']
        labels = {'pharmacy': '지정 약국'}
        widgets = {
            'prescription_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
class PrescriptionItemForm(forms.ModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ['medicine', 'dosage', 'duration', 'total_quantity']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        # 🚀 일단 재고가 있는 '모든 약국의 약'을 다 가져옵니다.
        available_medicines = Medicine.objects.filter(stock__gt=0)
            
        self.fields['medicine'].queryset = available_medicines
        self.fields['medicine'].label_from_instance = lambda obj: f"{obj.name} (남은 재고: {obj.stock}개)"
        self.fields['medicine'].empty_label = "약을 선택하세요"