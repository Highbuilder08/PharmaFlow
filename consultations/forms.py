from django import forms
from .models import Consultation

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['tag', 'title', 'content']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) 
        super().__init__(*args, **kwargs)
        
        # 부트스트랩 클래스 적용
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        # 관리자(superuser)가 아니면 '공지(NOTICE)' 선택지를 선택 목록에서 삭제
        if user and not user.is_superuser:
            self.fields['tag'].choices = [
                choice for choice in Consultation.TAG_CHOICES if choice[0] != 'NOTICE'
            ]