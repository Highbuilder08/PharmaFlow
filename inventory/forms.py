
# Django에서 폼을 만들기 위한 기능을 가져온다.
# forms.ModelForm을 사용하면 모델을 기반으로 입력 폼을 자동 생성할 수 있다.
from django import forms

# 현재 inventory 앱의 모델들을 가져온다.
# 각 모델을 기반으로 의약품 등록, 입출고 등록, 발주 등록 폼을 만든다.
from .models import Medicine, InventoryTransaction, PurchaseOrder


# =========================================================
# 의약품 등록 및 수정 폼
# =========================================================

# Medicine 모델을 기반으로 의약품 정보를 입력받는 폼이다.
# 이 폼은 의약품 신규 등록과 기존 의약품 수정 화면에서 사용할 수 있다.
class MedicineForm(forms.ModelForm):

    # ModelForm이 어떤 모델과 필드를 사용할지 설정하는 내부 클래스이다.
    class Meta:

        # 이 폼이 연결될 모델을 Medicine으로 지정한다.
        # 폼에서 입력된 값은 Medicine 객체를 생성하거나 수정할 때 사용된다.
        model = Medicine

        # 폼 화면에 표시할 모델 필드를 지정한다.
        # 여기에 포함되지 않은 pharmacy, created_at, updated_at 필드는
        # 폼에서 직접 입력받지 않는다.
        fields = (
            "name",
            "manufacturer",
            "box_image",
            "medicine_image",
            "minimum_stock",
        )


        # 각 필드가 화면에 표시될 때 사용할 한글 이름을 지정한다.
        labels = {
            "name": "의약품명",
            "manufacturer": "제조사",
            "box_image": "약 상자 이미지",
            "medicine_image": "약 이미지",
            "minimum_stock": "최소 재고",
        }

    # 폼 객체가 생성될 때 실행되는 초기화 메서드이다.
    # 기본 ModelForm 생성 과정을 유지하면서 추가 설정을 적용한다.
    def __init__(self, *args, **kwargs):

        # 부모 클래스인 ModelForm의 초기화 메서드를 먼저 실행한다.
        # 이 과정에서 Meta에 정의된 필드들이 실제 폼 필드로 생성된다.
        super().__init__(*args, **kwargs)

        # 현재 폼에 포함된 모든 필드를 하나씩 순회한다.
        for field in self.fields.values():

            # 각 필드의 HTML 위젯에 Bootstrap의 form-control 클래스를 추가한다.
            # 이를 통해 텍스트 입력창, 숫자 입력창, 파일 입력창 등이
            # Bootstrap 스타일로 표시된다.
            field.widget.attrs["class"] = "form-control"


# =========================================================
# 의약품 입출고 등록 폼
# =========================================================

# InventoryTransaction 모델을 기반으로 입고 또는 출고 내역을 입력받는 폼이다.
# 사용자는 의약품, 입출고 구분, 수량, 비고를 입력한다.
class InventoryTransactionForm(forms.ModelForm):

    # 폼과 연결할 모델 및 사용할 필드를 정의한다.
    class Meta:

        # 이 폼이 InventoryTransaction 모델을 기반으로 생성되도록 설정한다.
        model = InventoryTransaction

        # 입출고 등록 화면에서 사용자가 입력할 필드를 지정한다.
        # created_by와 created_at은 폼에서 직접 입력받지 않고
        # 뷰에서 현재 사용자와 현재 시각을 기준으로 처리한다.
        fields = (
            "medicine",
            "transaction_type",
            "quantity",
            "note",
        )

        # 각 폼 필드에 표시될 한글 라벨을 지정한다.
        labels = {
            "medicine": "의약품",
            "transaction_type": "구분",
            "quantity": "수량",
            "note": "비고",
        }

    # 폼이 생성될 때 의약품 목록의 정렬 방식과
    # Bootstrap 스타일을 추가하기 위해 초기화 메서드를 재정의한다.
    def __init__(self, *args, pharmacy=None, **kwargs):

        # ModelForm의 기본 초기화 과정을 먼저 실행한다.
        super().__init__(*args, **kwargs)

        # pharmacy 인자가 전달되지 않으면 의약품 선택 목록을 비운다.
        # 이렇게 하면 다른 약국의 의약품이 실수로 노출되는 것을 막을 수 있다.
        if pharmacy is None:
            self.fields["medicine"].queryset = Medicine.objects.none()

        # 현재 로그인한 사용자의 약국 정보가 전달된 경우에는
        # 해당 약국에 소속된 의약품만 이름과 제조사 순으로 조회한다.
        else:
            self.fields["medicine"].queryset = (
                Medicine.objects
                .filter(pharmacy=pharmacy)
                .order_by("name", "manufacturer")
            )

        # 선택 목록에는 의약품명과 제조사를 함께 표시한다.
        self.fields["medicine"].label_from_instance = (
            lambda medicine: f"{medicine.name} ({medicine.manufacturer})"
        )

        # 폼에 포함된 모든 필드를 순회한다.
        for field in self.fields.values():

            # 각 입력 필드의 HTML 위젯에 Bootstrap의
            # form-control 클래스를 적용한다.
            field.widget.attrs["class"] = "form-control"


# =========================================================
# 의약품 발주 등록 폼
# =========================================================

# PurchaseOrder 모델을 기반으로 의약품 발주 정보를 입력받는 폼이다.
# 사용자는 발주할 의약품, 발주 수량, 비고를 입력한다.
class PurchaseOrderForm(forms.ModelForm):

    # 폼에서 사용할 모델과 필드를 설정한다.
    class Meta:

        # 이 폼이 PurchaseOrder 모델을 기반으로 생성되도록 지정한다.
        model = PurchaseOrder

        # 발주 등록 화면에서 사용자가 입력할 필드를 지정한다.
        # status, ordered_by, created_at, received_at은 폼에서 직접 입력하지 않는다.
        # 상태와 처리자는 일반적으로 뷰의 로직에서 설정한다.
        fields = (
            "medicine",
            "quantity",
            "note",
        )

        # 각 필드가 화면에 표시될 때 사용할 라벨을 지정한다.
        labels = {
            "medicine": "의약품",
            "quantity": "발주 수량",
            "note": "비고",
        }

    # 폼이 생성될 때 의약품 선택 목록과 위젯 스타일을 설정한다.
    def __init__(self, *args, pharmacy=None, **kwargs):

        # 부모 클래스인 ModelForm의 초기화 메서드를 먼저 실행한다.
        super().__init__(*args, **kwargs)

        # pharmacy 인자가 없으면 의약품 선택 목록을 비운다.
        if pharmacy is None:
            self.fields["medicine"].queryset = Medicine.objects.none()

        # 현재 약국에 속한 의약품만 선택할 수 있도록 제한한다.
        else:
            self.fields["medicine"].queryset = (
                Medicine.objects
                .filter(pharmacy=pharmacy)
                .order_by("name", "manufacturer")
            )

        # ForeignKey 선택 항목의 화면 표시 방식을 직접 지정한다.
        # 기본적으로는 Medicine 모델의 __str__() 결과가 표시되지만,
        # 여기서는 각 항목에 의약품 이름만 표시하도록 명확하게 설정한다.
        self.fields["medicine"].label_from_instance = (
            lambda medicine: f"{medicine.name} ({medicine.manufacturer})"
        )

        # 폼에 포함된 모든 필드를 순회한다.
        for field in self.fields.values():

            # 각 필드의 HTML 위젯에 Bootstrap의
            # form-control 클래스를 추가한다.
            field.widget.attrs["class"] = "form-control"
