from django.contrib import admin

from .models import Medicine
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