from django import forms
from .models import Consultation

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['title', 'content']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # 장고의 원래 폼 세팅을 먼저 불러옵니다.
        
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})