
# Django 프로젝트의 settings.py에 정의된 설정값을 가져온다.
# 여기서는 settings.AUTH_USER_MODEL을 사용하여 현재 프로젝트의 사용자 모델을 참조한다.
from django.conf import settings

# Django에서 데이터베이스 모델을 정의할 때 사용하는 기능을 가져온다.
from django.db import models


# Django가 기본으로 생성해 주는 안내 주석이다.
# 이 파일에서 데이터베이스 테이블로 사용될 모델 클래스를 작성한다.
# Create your models here.

# accounts 앱에 정의된 Pharmacy 모델을 가져온다.
# 각 의약품이 어느 약국에 속해 있는지 연결하기 위해 사용한다.
from accounts.models import Pharmacy


# =========================================================
# 의약품 모델
# =========================================================

# 약국에서 관리하는 의약품의 기본 정보와 현재 재고를 저장하는 모델이다.
# Medicine 클래스 하나가 데이터베이스의 의약품 테이블 하나에 해당하며,
# Medicine 객체 하나는 특정 약국에서 관리하는 의약품 한 종류를 의미한다.
class Medicine(models.Model):

    # 해당 의약품을 관리하는 약국을 연결하는 외래키이다.
    pharmacy = models.ForeignKey(
        # 연결 대상은 accounts 앱의 Pharmacy 모델이다.
        Pharmacy,

        # 연결된 약국이 삭제되면 해당 약국에 등록된 의약품도 함께 삭제된다.
        # 약국 없이 의약품만 독립적으로 존재할 수 없기 때문에 CASCADE를 사용한다.
        on_delete=models.CASCADE,

        # Pharmacy 객체에서 해당 약국의 의약품 목록을 역참조할 때 사용할 이름이다.
        # 예: pharmacy.medicines.all()
        related_name="medicines",

        # 관리자 페이지나 Django 폼에서 표시되는 필드 이름이다.
        verbose_name="약국",
    )

    # 의약품의 이름을 저장하는 문자열 필드이다.
    name = models.CharField(
        # 최대 100글자까지 저장할 수 있다.
        max_length=100,

        # 관리자 페이지와 Django 폼에서 "의약품명"으로 표시된다.
        verbose_name="의약품명",
    )

    # 의약품을 생산한 제조사 이름을 저장한다.
    manufacturer = models.CharField(
        # 제조사 이름은 최대 100글자까지 입력할 수 있다.
        max_length=100,

        # 관리자 페이지와 Django 폼에서 표시되는 이름이다.
        verbose_name="제조사",
    )

    # 의약품 포장 상자의 이미지를 저장하는 필드이다.
    box_image = models.ImageField(
        # 업로드된 이미지는 MEDIA_ROOT 아래의
        # medicines/boxes/ 경로에 저장된다.
        upload_to="medicines/boxes/",

        # 폼에서 값을 입력하지 않아도 허용한다.
        blank=True,

        # 데이터베이스에 NULL 값이 저장되는 것을 허용한다.
        null=True,

        # 관리자 페이지와 폼에서 표시할 이름이다.
        verbose_name="약 상자 이미지",
    )

    # 의약품 자체의 사진을 저장하는 필드이다.
    medicine_image = models.ImageField(
        # 업로드된 이미지는 MEDIA_ROOT 아래의
        # medicines/items/ 경로에 저장된다.
        upload_to="medicines/items/",

        # 이미지 등록은 필수가 아니므로 빈 입력을 허용한다.
        blank=True,

        # 데이터베이스의 NULL 값 저장을 허용한다.
        null=True,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="약 이미지",
    )

    # 해당 의약품의 현재 재고 수량을 저장한다.
    stock = models.PositiveIntegerField(
        # 새 의약품을 등록할 때 별도의 값을 입력하지 않으면
        # 재고 수량을 0으로 시작한다.
        default=0,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="현재 재고",
    )

    # 재고 부족 여부를 판단할 때 기준으로 사용할 수량이다.
    minimum_stock = models.PositiveIntegerField(
        # 별도의 값을 입력하지 않으면 최소 재고 기준을 10개로 설정한다.
        default=10,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="최소 재고",
    )

    # 의약품 정보가 최초로 등록된 날짜와 시간을 저장한다.
    created_at = models.DateTimeField(
        # 객체가 처음 생성될 때 현재 날짜와 시간이 자동으로 저장된다.
        # 이후 객체를 수정해도 이 값은 변경되지 않는다.
        auto_now_add=True,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="등록일",
    )

    # 의약품 정보가 마지막으로 수정된 날짜와 시간을 저장한다.
    updated_at = models.DateTimeField(
        # 객체가 저장될 때마다 현재 날짜와 시간으로 자동 갱신된다.
        auto_now=True,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="수정일",
    )

    # Medicine 모델의 정렬 방식, 표시 이름, 제약조건 등
    # 추가 설정을 정의하는 내부 클래스이다.
    class Meta:

        # 의약품 목록을 별도로 정렬하지 않았을 때
        # 의약품 이름을 기준으로 오름차순 정렬한다.
        ordering = ["name"]

        # 관리자 페이지 등에서 단수 형태로 표시할 모델 이름이다.
        verbose_name = "의약품"

        # 관리자 페이지 등에서 복수 형태로 표시할 모델 이름이다.
        verbose_name_plural = "의약품"

        # 데이터베이스에 적용할 추가 제약조건을 정의한다.
        constraints = [
            # 지정된 필드 조합이 중복되지 않도록 제한하는 제약조건이다.
            models.UniqueConstraint(
                fields=[
                    # 약국, 의약품명, 제조사가 모두 같은 데이터는
                    # 중복 등록할 수 없도록 한다.
                    "pharmacy",
                    "name",
                    "manufacturer",
                ],

                # 데이터베이스에서 사용할 제약조건의 이름이다.
                name="unique_medicine_per_pharmacy",
            ),
        ]

    # Medicine 객체를 문자열로 표현할 때 반환할 값을 정의한다.
    # 관리자 페이지, Django shell, 선택 항목 등에서
    # 객체 주소 대신 의약품 이름이 표시되게 한다.
    def __str__(self):
        return self.name

    # 메서드를 일반 속성처럼 사용할 수 있도록 하는 데코레이터이다.
    # 호출할 때 medicine.is_low_stock처럼 괄호 없이 사용할 수 있다.
    @property
    def is_low_stock(self):

        # 현재 재고가 최소 재고 기준보다 작거나 같으면 True를 반환한다.
        # 재고가 충분하면 False를 반환한다.
        # 예: 템플릿에서 재고 부족 배지를 표시할 때 사용할 수 있다.
        return self.stock <= self.minimum_stock


# 숫자 필드에 입력 가능한 최소값을 제한하는 검증기를 가져온다.
# 입출고 수량과 발주 수량이 최소 1 이상이 되도록 검사할 때 사용한다.
from django.core.validators import MinValueValidator


# =========================================================
# 입출고 내역 모델
# =========================================================

# 의약품의 입고와 출고 기록을 저장하는 모델이다.
# 한 건의 InventoryTransaction 객체는 특정 의약품에 대해 발생한
# 한 번의 입고 또는 출고 작업을 의미한다.
class InventoryTransaction(models.Model):

    # 입출고 종류에 사용할 선택지를 정의하는 내부 클래스이다.
    # TextChoices를 사용하면 데이터베이스에 저장되는 값과
    # 사용자 화면에 표시되는 값을 구분할 수 있다.
    class TransactionType(models.TextChoices):

        # 데이터베이스에는 "IN"이 저장되고
        # 관리자 페이지와 폼에는 "입고"라고 표시된다.
        IN = "IN", "입고"

        # 데이터베이스에는 "OUT"이 저장되고
        # 관리자 페이지와 폼에는 "출고"라고 표시된다.
        OUT = "OUT", "출고"

    # 입출고 대상 의약품을 연결하는 외래키이다.
    medicine = models.ForeignKey(
        # 연결 대상은 위에서 정의한 Medicine 모델이다.
        Medicine,

        # 입출고 기록이 존재하는 의약품은 삭제하지 못하게 한다.
        # 과거의 재고 변경 기록이 사라지는 것을 방지하기 위해 PROTECT를 사용한다.
        on_delete=models.PROTECT,

        # Medicine 객체에서 해당 의약품의 입출고 기록을 역참조할 때 사용한다.
        # 예: medicine.transactions.all()
        related_name="transactions",

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="의약품",
    )

    # 해당 기록이 입고인지 출고인지 저장하는 필드이다.
    transaction_type = models.CharField(
        # "IN" 또는 "OUT"을 저장하기에 충분하도록 최대 길이를 3으로 지정한다.
        max_length=3,

        # TransactionType 내부 클래스에 정의된 값만 선택할 수 있게 한다.
        choices=TransactionType.choices,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="입출고 구분",
    )

    # 입고 또는 출고된 의약품 수량을 저장한다.
    quantity = models.PositiveIntegerField(
        # 입력 수량이 최소 1 이상인지 검사한다.
        # 따라서 0이나 음수 수량은 저장할 수 없다.
        validators=[MinValueValidator(1)],

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="수량",
    )

    # 입출고 작업에 대한 추가 설명을 저장한다.
    note = models.CharField(
        # 최대 255글자까지 입력할 수 있다.
        max_length=255,

        # 비고는 필수 항목이 아니므로 빈 입력을 허용한다.
        blank=True,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="비고",
    )

    # 해당 입출고 작업을 처리한 사용자를 저장하는 외래키이다.
    created_by = models.ForeignKey(
        # 프로젝트의 사용자 모델을 직접 지정하지 않고
        # settings.AUTH_USER_MODEL을 참조한다.
        # Custom User 모델을 사용하는 프로젝트에서도 안전하게 연결할 수 있다.
        settings.AUTH_USER_MODEL,

        # 처리자 계정이 삭제되더라도 입출고 기록은 유지한다.
        # 삭제된 사용자가 연결되어 있던 값만 NULL로 변경된다.
        on_delete=models.SET_NULL,

        # 데이터베이스에 NULL 값을 저장할 수 있도록 허용한다.
        null=True,

        # 폼에서 처리자 값이 비어 있는 것도 허용한다.
        blank=True,

        # 사용자 객체에서 해당 사용자가 처리한 입출고 기록을 조회할 때 사용한다.
        # 예: user.inventory_transactions.all()
        related_name="inventory_transactions",

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="처리자",
    )

    # 입출고 작업이 등록된 날짜와 시간을 저장한다.
    created_at = models.DateTimeField(
        # 입출고 내역이 처음 생성될 때 현재 날짜와 시간이 자동으로 저장된다.
        auto_now_add=True,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="처리일시",
    )

    # InventoryTransaction 모델의 기본 동작과 표시 방식을 설정한다.
    class Meta:

        # 입출고 내역을 처리일시 기준 내림차순으로 정렬한다.
        # 가장 최근에 처리된 기록이 목록의 위쪽에 표시된다.
        ordering = ["-created_at"]

        # 관리자 페이지 등에서 단수 형태로 표시할 이름이다.
        verbose_name = "입출고 내역"

        # 관리자 페이지 등에서 복수 형태로 표시할 이름이다.
        verbose_name_plural = "입출고 내역"

    # 입출고 내역 객체를 문자열로 표현하는 방식을 정의한다.
    def __str__(self):
        return (
            # 연결된 의약품의 이름을 표시한다.
            f"{self.medicine.name} "

            # choices에 정의된 화면 표시값을 반환한다.
            # IN이면 "입고", OUT이면 "출고"가 반환된다.
            f"{self.get_transaction_type_display()} "

            # 처리된 수량을 표시한다.
            f"{self.quantity}개"
        )


# =========================================================
# 발주 모델
# =========================================================

# 부족한 의약품을 공급업체에 주문한 발주 내역을 저장하는 모델이다.
# 한 개의 PurchaseOrder 객체는 특정 의약품에 대한
# 한 번의 발주 요청과 그 진행 상태를 의미한다.
class PurchaseOrder(models.Model):

    # 발주의 진행 상태에 사용할 선택지를 정의한다.
    class Status(models.TextChoices):

        # 발주 정보가 시스템에 등록되었지만
        # 아직 공급업체에 실제 주문하지 않은 상태이다.
        WAIT = "WAIT", "발주 대기"

        # 공급업체에 발주 요청을 완료한 상태이다.
        ORDERED = "ORDERED", "발주 완료"

        # 주문한 의약품을 실제로 전달받아
        # 재고 반영까지 완료된 상태이다.
        RECEIVED = "RECEIVED", "입고 완료"

        # 등록된 발주가 취소된 상태이다.
        CANCELLED = "CANCELLED", "취소"

    # 발주 대상 의약품을 연결하는 외래키이다.
    medicine = models.ForeignKey(
        # 연결 대상은 Medicine 모델이다.
        Medicine,

        # 발주 기록이 존재하는 의약품은 삭제하지 못하게 한다.
        # 과거 발주 내역을 보존하기 위해 PROTECT를 사용한다.
        on_delete=models.PROTECT,

        # Medicine 객체에서 해당 의약품의 발주 내역을 역참조할 때 사용한다.
        # 예: medicine.purchase_orders.all()
        related_name="purchase_orders",

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="의약품",
    )

    # 발주할 의약품의 수량을 저장한다.
    quantity = models.PositiveIntegerField(
        # 발주 수량은 최소 1개 이상이어야 한다.
        # 0 또는 음수 수량이 입력되는 것을 방지한다.
        validators=[MinValueValidator(1)],

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="발주 수량",
    )

    # 발주의 현재 진행 상태를 저장한다.
    status = models.CharField(
        # 상태값 중 가장 긴 문자열을 저장할 수 있도록 최대 길이를 10으로 지정한다.
        max_length=10,

        # Status 내부 클래스에 정의된 상태만 선택할 수 있도록 제한한다.
        choices=Status.choices,

        # 새 발주를 생성할 때 별도의 상태를 지정하지 않으면
        # 기본적으로 발주 대기 상태로 저장한다.
        default=Status.WAIT,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="상태",
    )

    # 발주와 관련된 추가 설명을 저장한다.
    note = models.CharField(
        # 최대 255글자까지 입력할 수 있다.
        max_length=255,

        # 비고 입력은 필수가 아니므로 빈 값을 허용한다.
        blank=True,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="비고",
    )

    # 발주를 등록하거나 처리한 사용자를 연결하는 외래키이다.
    ordered_by = models.ForeignKey(
        # 프로젝트에서 설정한 사용자 모델을 참조한다.
        # Custom User 모델을 사용하더라도 올바르게 연결된다.
        settings.AUTH_USER_MODEL,

        # 발주자 계정이 삭제되더라도 발주 내역은 유지한다.
        # 삭제된 사용자와의 연결값만 NULL로 변경된다.
        on_delete=models.SET_NULL,

        # 데이터베이스에서 NULL 값을 허용한다.
        null=True,

        # 폼에서 발주자 값을 입력하지 않아도 허용한다.
        blank=True,

        # 사용자 객체에서 해당 사용자가 등록한 발주 내역을 조회할 때 사용한다.
        # 예: user.purchase_orders.all()
        related_name="purchase_orders",

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="발주자",
    )

    # 발주 내역이 최초로 등록된 날짜와 시간을 저장한다.
    created_at = models.DateTimeField(
        # 객체가 처음 생성될 때 현재 날짜와 시간이 자동 저장된다.
        auto_now_add=True,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="발주일",
    )

    # 발주 상태가 입고 완료로 변경된 날짜와 시간을 저장한다.
    received_at = models.DateTimeField(
        # 아직 입고가 완료되지 않은 경우 값이 없을 수 있으므로
        # 데이터베이스의 NULL 값을 허용한다.
        null=True,

        # 폼에서도 빈 값 입력을 허용한다.
        blank=True,

        # 관리자 페이지와 폼에서 표시되는 이름이다.
        verbose_name="입고 완료일",
    )

    # PurchaseOrder 모델의 기본 정렬 방식과 표시 이름을 설정한다.
    class Meta:

        # 발주일 기준 내림차순으로 정렬한다.
        # 가장 최근에 등록된 발주가 목록의 위쪽에 표시된다.
        ordering = ["-created_at"]

        # 관리자 페이지 등에서 단수 형태로 표시할 모델 이름이다.
        verbose_name = "발주"

        # 관리자 페이지 등에서 복수 형태로 표시할 모델 이름이다.
        verbose_name_plural = "발주"

    # 발주 객체를 문자열로 표현할 때 사용할 값을 정의한다.
    def __str__(self):
        return (
            # 발주 대상 의약품 이름을 표시한다.
            f"{self.medicine.name} - "

            # 발주 수량을 표시한다.
            f"{self.quantity}개 - "

            # 현재 상태의 화면 표시값을 반환한다.
            # 예: WAIT 값은 "발주 대기"로 표시된다.
            f"{self.get_status_display()}"
        )
