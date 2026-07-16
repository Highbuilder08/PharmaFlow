from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import approved_pharmacy_required
from .forms import InventoryTransactionForm, MedicineForm, PurchaseOrderForm
from .models import InventoryTransaction, Medicine, PurchaseOrder


# ============ 의약품 (Medicine) ==============


@approved_pharmacy_required
def medicine_list(request):
    medicines = Medicine.objects.filter(
        pharmacy=request.user.pharmacy,
    ).order_by("name", "manufacturer")

    query = request.GET.get("q", "").strip()
    stock_filter = request.GET.get("stock_filter", "all")

    if query:
        medicines = medicines.filter(
            Q(name__icontains=query)
            | Q(manufacturer__icontains=query)
        )

    if stock_filter == "low":
        medicines = medicines.filter(stock__lte=F("minimum_stock"))
    elif stock_filter == "normal":
        medicines = medicines.filter(stock__gt=F("minimum_stock"))

    paginator = Paginator(medicines, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/medicine_list.html",
        {
            "medicines": page_obj,
            "page_obj": page_obj,
            "query": query,
            "stock_filter": stock_filter,
        },
    )


@approved_pharmacy_required
def medicine_create(request):
    if request.method == "POST":
        form = MedicineForm(request.POST, request.FILES)

        if form.is_valid():
            medicine = form.save(commit=False)
            medicine.pharmacy = request.user.pharmacy
            medicine.save()

            messages.success(request, "의약품이 등록되었습니다.")
            return redirect("inventory:medicine_list")
    else:
        form = MedicineForm()

    return render(
        request,
        "inventory/medicine_form.html",
        {
            "form": form,
            "page_title": "의약품 등록",
            "submit_text": "등록",
        },
    )


@approved_pharmacy_required
def medicine_update(request, pk):
    medicine = get_object_or_404(
        Medicine,
        pk=pk,
        pharmacy=request.user.pharmacy,
    )

    if request.method == "POST":
        form = MedicineForm(
            request.POST,
            request.FILES,
            instance=medicine,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "의약품 정보가 수정되었습니다.")
            return redirect("inventory:medicine_detail", pk=medicine.pk)
    else:
        form = MedicineForm(instance=medicine)

    return render(
        request,
        "inventory/medicine_form.html",
        {
            "form": form,
            "page_title": "의약품 수정",
            "submit_text": "수정",
        },
    )


@approved_pharmacy_required
def medicine_detail(request, pk):
    medicine = get_object_or_404(
        Medicine.objects.select_related("pharmacy"),
        pk=pk,
        pharmacy=request.user.pharmacy,
    )

    recent_transactions = medicine.transactions.select_related(
        "created_by",
    ).all()[:5]

    return render(
        request,
        "inventory/medicine_detail.html",
        {
            "medicine": medicine,
            "recent_transactions": recent_transactions,
        },
    )


@approved_pharmacy_required
def medicine_delete(request, pk):
    medicine = get_object_or_404(
        Medicine,
        pk=pk,
        pharmacy=request.user.pharmacy,
    )

    if request.method == "POST":
        medicine_name = medicine.name

        try:
            medicine.delete()
        except ProtectedError:
            messages.error(
                request,
                "입출고 또는 발주 기록이 있는 의약품은 삭제할 수 없습니다.",
            )
            return redirect("inventory:medicine_detail", pk=medicine.pk)

        messages.success(
            request,
            f"{medicine_name} 의약품이 삭제되었습니다.",
        )
        return redirect("inventory:medicine_list")

    return render(
        request,
        "inventory/medicine_confirm_delete.html",
        {"medicine": medicine},
    )


# ============ 입출고 (InventoryTransaction) ==============


@approved_pharmacy_required
def transaction_list(request):
    transactions = (
        InventoryTransaction.objects.filter(
            medicine__pharmacy=request.user.pharmacy,
        )
        .select_related("medicine", "created_by")
        .order_by("-created_at")
    )

    query = request.GET.get("q", "").strip()
    transaction_filter = request.GET.get(
        "transaction_filter",
        "all",
    )

    if query:
        transactions = transactions.filter(
            Q(medicine__name__icontains=query)
            | Q(medicine__manufacturer__icontains=query)
            | Q(note__icontains=query)
        )

    if transaction_filter == "in":
        transactions = transactions.filter(
            transaction_type=InventoryTransaction.TransactionType.IN,
        )
    elif transaction_filter == "out":
        transactions = transactions.filter(
            transaction_type=InventoryTransaction.TransactionType.OUT,
        )

    paginator = Paginator(transactions, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/transaction_list.html",
        {
            "transactions": page_obj,
            "page_obj": page_obj,
            "query": query,
            "transaction_filter": transaction_filter,
        },
    )


@approved_pharmacy_required
def transaction_create(request):
    pharmacy = request.user.pharmacy

    if request.method == "POST":
        form = InventoryTransactionForm(
            request.POST,
            pharmacy=pharmacy,
        )

        if form.is_valid():
            medicine_id = form.cleaned_data["medicine"].pk
            transaction_type = form.cleaned_data["transaction_type"]
            quantity = form.cleaned_data["quantity"]
            note = form.cleaned_data["note"]

            with transaction.atomic():
                medicine = get_object_or_404(
                    Medicine.objects.select_for_update(),
                    pk=medicine_id,
                    pharmacy=pharmacy,
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

                    medicine.save(update_fields=["stock", "updated_at"])

                    InventoryTransaction.objects.create(
                        medicine=medicine,
                        transaction_type=transaction_type,
                        quantity=quantity,
                        note=note,
                        created_by=request.user,
                    )

                    action_name = (
                        "입고"
                        if transaction_type
                        == InventoryTransaction.TransactionType.IN
                        else "출고"
                    )
                    messages.success(
                        request,
                        f"{medicine.name} {quantity}개 {action_name} 처리가 완료되었습니다.",
                    )
                    return redirect("inventory:transaction_list")
    else:
        form = InventoryTransactionForm(pharmacy=pharmacy)

    medicine_stocks = {
        str(medicine.pk): medicine.stock
        for medicine in Medicine.objects.filter(pharmacy=pharmacy)
    }

    return render(
        request,
        "inventory/transaction_form.html",
        {
            "form": form,
            "page_title": "입출고 등록",
            "submit_text": "등록",
            "medicine_stocks": medicine_stocks,
        },
    )


# ============ 발주 (PurchaseOrder) ==============


@approved_pharmacy_required
def purchase_order_list(request):
    purchase_orders = (
        PurchaseOrder.objects.filter(
            medicine__pharmacy=request.user.pharmacy,
        )
        .select_related("medicine", "ordered_by")
        .order_by("-created_at")
    )

    paginator = Paginator(purchase_orders, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/purchase_order_list.html",
        {
            "purchase_orders": page_obj,
            "page_obj": page_obj,
        },
    )


@approved_pharmacy_required
def purchase_order_create(request):
    pharmacy = request.user.pharmacy

    if request.method == "POST":
        form = PurchaseOrderForm(
            request.POST,
            pharmacy=pharmacy,
        )
    else:
        form = PurchaseOrderForm(pharmacy=pharmacy)

    medicines = Medicine.objects.filter(
        pharmacy=pharmacy,
    ).order_by("name", "manufacturer")

    if request.method == "POST" and form.is_valid():
        purchase_order = form.save(commit=False)
        purchase_order.ordered_by = request.user
        purchase_order.save()

        messages.success(
            request,
            (
                f"{purchase_order.medicine.name} "
                f"{purchase_order.quantity}개 발주가 등록되었습니다."
            ),
        )
        return redirect("inventory:purchase_order_list")

    medicine_data = list(
        medicines.values(
            "id",
            "manufacturer",
            "stock",
            "minimum_stock",
        )
    )

    return render(
        request,
        "inventory/purchase_order_form.html",
        {
            "form": form,
            "medicine_data": medicine_data,
        },
    )


@approved_pharmacy_required
def purchase_order_mark_ordered(request, pk):
    if request.method != "POST":
        return redirect("inventory:purchase_order_list")

    with transaction.atomic():
        purchase_order = get_object_or_404(
            PurchaseOrder.objects.select_for_update(),
            pk=pk,
            medicine__pharmacy=request.user.pharmacy,
        )

        if purchase_order.status != PurchaseOrder.Status.WAIT:
            messages.warning(
                request,
                "발주 대기 상태인 내역만 발주 완료 처리할 수 있습니다.",
            )
            return redirect("inventory:purchase_order_list")

        purchase_order.status = PurchaseOrder.Status.ORDERED
        purchase_order.save(update_fields=["status"])

    messages.success(request, "발주 완료 상태로 변경했습니다.")
    return redirect("inventory:purchase_order_list")


@approved_pharmacy_required
def purchase_order_receive(request, pk):
    if request.method != "POST":
        return redirect("inventory:purchase_order_list")

    with transaction.atomic():
        purchase_order = get_object_or_404(
            PurchaseOrder.objects.select_for_update().select_related(
                "medicine",
            ),
            pk=pk,
            medicine__pharmacy=request.user.pharmacy,
        )

        if purchase_order.status != PurchaseOrder.Status.ORDERED:
            messages.warning(
                request,
                "발주 완료 상태인 내역만 입고 완료 처리할 수 있습니다.",
            )
            return redirect("inventory:purchase_order_list")

        medicine = get_object_or_404(
            Medicine.objects.select_for_update(),
            pk=purchase_order.medicine_id,
            pharmacy=request.user.pharmacy,
        )

        medicine.stock += purchase_order.quantity
        medicine.save(update_fields=["stock", "updated_at"])

        InventoryTransaction.objects.create(
            medicine=medicine,
            transaction_type=InventoryTransaction.TransactionType.IN,
            quantity=purchase_order.quantity,
            note=f"발주 #{purchase_order.pk} 입고 완료",
            created_by=request.user,
        )

        purchase_order.status = PurchaseOrder.Status.RECEIVED
        purchase_order.received_at = timezone.now()
        purchase_order.save(update_fields=["status", "received_at"])

    messages.success(
        request,
        (
            f"{purchase_order.medicine.name} "
            f"{purchase_order.quantity}개를 입고 처리했습니다."
        ),
    )
    return redirect("inventory:purchase_order_list")


@approved_pharmacy_required
def purchase_order_cancel(request, pk):
    if request.method != "POST":
        return redirect("inventory:purchase_order_list")

    with transaction.atomic():
        purchase_order = get_object_or_404(
            PurchaseOrder.objects.select_for_update(),
            pk=pk,
            medicine__pharmacy=request.user.pharmacy,
        )

        if purchase_order.status == PurchaseOrder.Status.RECEIVED:
            messages.warning(
                request,
                "이미 입고 완료된 발주는 취소할 수 없습니다.",
            )
            return redirect("inventory:purchase_order_list")

        if purchase_order.status == PurchaseOrder.Status.CANCELLED:
            messages.warning(request, "이미 취소된 발주입니다.")
            return redirect("inventory:purchase_order_list")

        purchase_order.status = PurchaseOrder.Status.CANCELLED
        purchase_order.save(update_fields=["status"])

    messages.success(request, "발주를 취소했습니다.")
    return redirect("inventory:purchase_order_list")
