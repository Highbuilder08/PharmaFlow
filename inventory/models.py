from django.db import models

# Create your models here.

#의약품
class Medicine(models.Model):
    name = models.CharField( #의약품 이름
        max_length=100,
        verbose_name="의약품명",
    )
    manufacturer = models.CharField( #제조사
        max_length=100,
        verbose_name="제조사",
    )
    stock = models.PositiveIntegerField( # 현재 재고량
        default=0,
        verbose_name="현재 재고",
    )
    minimum_stock = models.PositiveIntegerField( # 재고 부족 판단 기준
        default=10,
        verbose_name="최소 재고",
    )
    created_at = models.DateTimeField( # 최초 등록 시간
        auto_now_add=True,
        verbose_name="등록일",
    )
    updated_at = models.DateTimeField( # 마지막 수정 시간
        auto_now=True,
        verbose_name="수정일",
    )

    class Meta:
        ordering = ["name"] # 별도로 정렬하지 않아도 의약품 순서로 나올 수 있도록 해준다.
        verbose_name = "의약품"
        verbose_name_plural = "의약품"

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.stock <= self.minimum_stock
    
from django.core.validators import MinValueValidator    

#입출고
class InventoryTransaction(models.Model):

    class TransactionType(models.TextChoices):
        IN = "IN", "입고"
        OUT = "OUT", "출고"

    medicine = models.ForeignKey( #Medicine 테이블 외래키
        Medicine, 
        on_delete=models.PROTECT, # 입출고 기록이 있는 약품을 실수로 삭제하지 못하게 막는다.
        related_name="transactions", # 의약품에서 입출고 기록을 ( medicine.transactions.all() )처럼 조회할 수 있다.
        verbose_name="의약품",
    )

    transaction_type = models.CharField(
        max_length=3,
        choices=TransactionType.choices,
        verbose_name="입출고 구분",
    )

    quantity = models.PositiveIntegerField( #최소값 검사 -> 0이나 음수는 불가
        validators=[MinValueValidator(1)],
        verbose_name="수량",
    )

    note = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="비고",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="처리일시",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "입출고 내역"
        verbose_name_plural = "입출고 내역"

    def __str__(self):
        return (
            f"{self.medicine.name} "
            f"{self.get_transaction_type_display()} "
            f"{self.quantity}개"
        )

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