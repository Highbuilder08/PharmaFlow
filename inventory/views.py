from django.shortcuts import get_object_or_404, redirect, render

# Create your views here.
from .forms import MedicineForm
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
    
    

# ============ 발주 (PurchaseOrder) ==============