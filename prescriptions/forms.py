# prescriptions/forms.py
from django import forms
from .models import Prescription, PrescriptionItem
from inventory.models import Medicine

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['patient_name', 'ssn_front', 'phone', 'symptoms', 'prescription_date']
        
        widgets = {
            'prescription_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
class PrescriptionItemForm(forms.ModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ['medicine', 'dosage', 'duration', 'total_quantity']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. 재고(stock)가 1 이상인 약품만 가져옵니다.
        available_medicines = Medicine.objects.filter(stock__gt=0)
        self.fields['medicine'].queryset = available_medicines
        
        # 🚀 2. [핵심 추가] 드롭다운(Select)에 표시될 글자를 내 마음대로 바꿉니다!
        self.fields['medicine'].label_from_instance = lambda obj: f"{obj.name} (남은 재고: {obj.stock}개)"
        
        # 3. 만약 선택 가능한 약품이 0개라면?
        if not available_medicines.exists():
            self.fields['medicine'].empty_label = "선택 가능한 약품이 없습니다"
            self.fields['medicine'].widget.attrs['disabled'] = 'disabled' 
        else:
            self.fields['medicine'].empty_label = "약을 선택하세요"