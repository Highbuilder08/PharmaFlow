from django import forms
from .models import Prescription, PrescriptionItem
from inventory.models import Medicine
from django.db.models import Q
from django.forms.models import BaseInlineFormSet 
from django.core.exceptions import ValidationError 

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
        # 🚀 1. fields 목록을 새 필드들로 교체합니다!
        fields = ['medicine', 'dose_amount', 'daily_doses', 'duration_days', 'total_quantity']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 🚀 핵심: 재고가 1 이상이거나, 이미 이 처방전에 등록되어 있던 약품을 모두 가져옵니다!
        if self.instance and self.instance.pk:
            available_medicines = Medicine.objects.filter(
                Q(stock__gt=0) | Q(id=self.instance.medicine_id)
            )
        else:
            available_medicines = Medicine.objects.filter(stock__gt=0)
            
        self.fields['medicine'].queryset = available_medicines
        self.fields['medicine'].label_from_instance = lambda obj: f"{obj.name} (남은 재고: {obj.stock}개)"
        
        if not available_medicines.exists():
            self.fields['medicine'].empty_label = "선택 가능한 약품이 없습니다"
            self.fields['medicine'].widget.attrs['disabled'] = 'disabled' 
        else:
            self.fields['medicine'].empty_label = "약을 선택하세요"
            
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
            
        # 🚀 2. 총 수량(total_quantity) 칸은 사용자가 직접 입력하지 못하게 막습니다!
        self.fields['total_quantity'].widget.attrs['readonly'] = True
        self.fields['total_quantity'].widget.attrs['style'] = 'background-color: #e9ecef; font-weight: bold;'
            
class PrescriptionItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        
        # 개별 폼에 이미 에러가 있다면 먼저 처리하도록 넘김
        if any(self.errors):
            return

        selected_medicines = []
        
        for form in self.forms:
            # 삭제 체크된 폼은 검사에서 제외 (나중을 위해 추가해둠)
            if self.can_delete and self._should_delete_form(form):
                continue
                
            medicine = form.cleaned_data.get('medicine')
            
            if medicine:
                # 🚀 핵심: 이미 선택된 약품 목록에 이 약이 또 있다면? 에러 발생!
                if medicine in selected_medicines:
                    raise ValidationError("🚨 동일한 약품을 중복해서 처방할 수 없습니다.")
                
                selected_medicines.append(medicine)