from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction

# Create your views here.
from .forms import (
    MedicineForm,
    InventoryTransactionForm,
)
from .models import Medicine, InventoryTransaction


# ============ 의약품 (Medicine) ==============

def medicine_list(request):
    medicines = Medicine.objects.all()

    return render(
        request,
        "inventory/medicine_list.html",
        { "medicines": medicines }
    )
    
def medicine_create(request):
    if request.method == "POST":
        form = MedicineForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("inventory:medicine_list")
    else:
        form = MedicineForm()

    context = {
        "form": form,
        "page_title": "의약품 등록",
        "submit_text": "등록",
    }

    return render(
        request,
        "inventory/medicine_form.html",
        context,
    )
    
def medicine_update(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)

    if request.method == "POST":
        form = MedicineForm(
            request.POST,
            instance=medicine,
        )

        if form.is_valid():
            form.save()
            return redirect("inventory:medicine_list")
    else:
        form = MedicineForm(instance=medicine)

    context = {
        "form": form,
        "page_title": "의약품 수정",
        "submit_text": "수정",
    }

    return render(
        request,
        "inventory/medicine_form.html",
        context,
    )
    
def medicine_delete(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)

    if request.method == "POST":
        medicine.delete()
        return redirect("inventory:medicine_list")

    return render(
        request,
        "inventory/medicine_confirm_delete.html",
        {
            "medicine": medicine,
        },
    )
    
    
# ============ 입출고 (Transaction) ==============
def transaction_list(request):
    transactions = InventoryTransaction.objects.select_related(
        "medicine",
    ).all()

    context = {
        "transactions": transactions,
    }

    return render(
        request,
        "inventory/transaction_list.html",
        context,
    )
    
def transaction_create(request):
    if request.method == "POST":
        form = InventoryTransactionForm(request.POST)

        if form.is_valid():
            # form.cleaned_data는 form.is_valid()를 통과한 안전한 입력값
            medicine_id = form.cleaned_data["medicine"].pk
            transaction_type = form.cleaned_data["transaction_type"]
            quantity = form.cleaned_data["quantity"]
            note = form.cleaned_data["note"]

            with transaction.atomic(): 
                # Medicine 재고 변경
                # InventoryTransaction 기록 생성
                # 이 두가지 작업을 하나로 묶음
                medicine = (
                    Medicine.objects
                    .select_for_update() # 처리하는 동안 해당 의약품 DB 행을 잠금.
                    .get(pk=medicine_id)
                )

                if (
                    transaction_type
                    == InventoryTransaction.TransactionType.OUT
                    and medicine.stock < quantity
                ):
                    form.add_error(
                        "quantity",
                        (
                            f"현재 재고는 {medicine.stock}개입니다. "
                            "현재 재고보다 많이 출고할 수 없습니다."
                        ),
                    )
                else:
                    if (
                        transaction_type
                        == InventoryTransaction.TransactionType.IN
                    ):
                        medicine.stock += quantity
                    else:
                        medicine.stock -= quantity

                    medicine.save(
                        update_fields=[
                            "stock",
                            "updated_at",
                        ],
                    )

                    InventoryTransaction.objects.create(
                        medicine=medicine,
                        transaction_type=transaction_type,
                        quantity=quantity,
                        note=note,
                    )

                    return redirect(
                        "inventory:transaction_list",
                    )
    else:
        form = InventoryTransactionForm()

    medicine_stocks = { # transaction_form.html의 javascript가 선택된 의약품 id를 이용해 재고 표시
        str(medicine.pk): medicine.stock
        for medicine in Medicine.objects.all()
    }

    context = {
        "form": form,
        "page_title": "입출고 등록",
        "submit_text": "등록",
        "medicine_stocks": medicine_stocks,
    }

    return render(
        request,
        "inventory/transaction_form.html",
        context,
    )



# ============ 발주 (PurchaseOrder) ==============