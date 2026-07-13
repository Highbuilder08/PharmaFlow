from django import forms

from .models import Medicine


class MedicineForm(forms.ModelForm):

    class Meta:
        model = Medicine
        fields = (
            "name",
            "manufacturer",
            "stock",
            "minimum_stock",
        )

        labels = {
            "name": "의약품명",
            "manufacturer": "제조사",
            "stock": "현재 재고",
            "minimum_stock": "최소 재고",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"