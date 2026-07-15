from django.contrib import admin

from .models import Medicine, InventoryTransaction, PurchaseOrder


# Register your models here.

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "manufacturer",
        "stock",
        "minimum_stock",
        "stock_status",
        "updated_at",
    )
    search_fields = (
        "name",
        "manufacturer",
    )
    list_filter = (
        "manufacturer",
        "created_at",
    )

    @admin.display(description="재고 상태")
    def stock_status(self, obj):
        if obj.is_low_stock:
            return "부족"
        return "정상"
    
    
@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "medicine",
        "transaction_type",
        "quantity",
        "note",
        "created_at",
    )

    list_filter = (
        "transaction_type",
        "created_at",
    )

    search_fields = (
        "medicine__name",
        "medicine__manufacturer",
        "note",
    )

    autocomplete_fields = (
        "medicine",
    )
    
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "medicine",
        "quantity",
        "status",
        "ordered_by",
        "created_at",
        "received_at",
    )

    list_filter = (
        "status",
        "created_at",
        "received_at",
    )

    search_fields = (
        "medicine__name",
        "medicine__manufacturer",
        "ordered_by__username",
        "ordered_by__name",
        "note",
    )

    readonly_fields = (
        "created_at",
        "received_at",
    )