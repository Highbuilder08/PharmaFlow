from django.db import models

# Create your models here.

#의약품
class Medicine(models.Model):
    name = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return self.name
    
#입출고
class InventoryTransaction(models.Model):

    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)

    TYPE = (
        ("IN", "입고"),
        ("OUT", "출고"),
    )

    transaction_type = models.CharField(
        max_length=3,
        choices=TYPE
    )

    quantity = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

#발주
class PurchaseOrder(models.Model):

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE
    )

    quantity = models.IntegerField()

    STATUS = (
        ("WAIT", "대기"),
        ("DONE", "완료"),
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS,
        default="WAIT"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )