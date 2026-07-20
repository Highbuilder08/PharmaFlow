# forms: 사용자가 입력하는 글쓰기 화면(폼)을 자동으로 만들어주는 기능
from django import forms
from .models import Consultation

# ConsultationForm: 글 작성/수정 화면에서 쓰는 입력 폼
class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation  # Consultation 모델을 기반으로 폼을 자동 생성
        fields = ['tag', 'title', 'content']  # 화면에 보여줄 입력 항목

    def __init__(self, *args, **kwargs):
        # views.py에서 넘겨준 user 값을 꺼내옴 (없으면 None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 부트스트랩 클래스 적용
        # 모든 입력창에 부트스트랩 디자인(form-control)을 적용해서 예쁘게 보이게 함
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

        # 관리자(superuser)가 아니면 '공지(NOTICE)' 선택지를 선택 목록에서 삭제
        if user and not user.is_superuser:
            self.fields['tag'].choices = [
                choice for choice in Consultation.TAG_CHOICES if choice[0] != 'NOTICE'
            ]