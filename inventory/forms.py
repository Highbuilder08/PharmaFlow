from django import forms

from .models import InventoryTransaction, Medicine, PurchaseOrder


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = (
            "name",
            "manufacturer",
            "box_image",
            "medicine_image",
            "minimum_stock",
        )
        labels = {
            "name": "의약품명",
            "manufacturer": "제조사",
            "box_image": "약 상자 이미지",
            "medicine_image": "약 이미지",
            "minimum_stock": "최소 재고",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class InventoryTransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction
        fields = (
            "medicine",
            "transaction_type",
            "quantity",
            "note",
        )
        labels = {
            "medicine": "의약품",
            "transaction_type": "구분",
            "quantity": "수량",
            "note": "비고",
        }

    def __init__(self, *args, pharmacy=None, **kwargs):
        super().__init__(*args, **kwargs)

        if pharmacy is None:
            self.fields["medicine"].queryset = Medicine.objects.none()
        else:
            self.fields["medicine"].queryset = (
                Medicine.objects.filter(pharmacy=pharmacy).order_by(
                    "name",
                    "manufacturer",
                )
            )

        self.fields["medicine"].label_from_instance = (
            lambda medicine: f"{medicine.name} ({medicine.manufacturer})"
        )

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = (
            "medicine",
            "quantity",
            "note",
        )
        labels = {
            "medicine": "의약품",
            "quantity": "발주 수량",
            "note": "비고",
        }

    def __init__(self, *args, pharmacy=None, **kwargs):
        super().__init__(*args, **kwargs)

        if pharmacy is None:
            self.fields["medicine"].queryset = Medicine.objects.none()
        else:
            self.fields["medicine"].queryset = (
                Medicine.objects.filter(pharmacy=pharmacy).order_by(
                    "name",
                    "manufacturer",
                )
            )

        self.fields["medicine"].label_from_instance = (
            lambda medicine: f"{medicine.name} ({medicine.manufacturer})"
        )

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
