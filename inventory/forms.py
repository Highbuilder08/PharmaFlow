from django import forms

from .models import Medicine, InventoryTransaction, PurchaseOrder


class MedicineForm(forms.ModelForm):

    class Meta:
        model = Medicine
        fields = (
            "name",
            "manufacturer",
            "box_image",
            "medicine_image",
            "stock",
            "minimum_stock",
        )

        labels = {
            "name": "의약품명",
            "manufacturer": "제조사",
            "box_image": "약 상자 이미지",
            "medicine_image": "약 이미지",
            "stock": "현재 재고",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["medicine"].queryset = (
            Medicine.objects.order_by("name")
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["medicine"].queryset = (
            Medicine.objects.order_by("name")
        )

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"