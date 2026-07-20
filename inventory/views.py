
# 데이터베이스에서 객체를 조회하거나,
# 다른 URL로 이동하거나,
# HTML 템플릿을 화면에 렌더링할 때 사용하는 함수들을 가져온다.
from django.shortcuts import get_object_or_404, redirect, render

# 여러 데이터베이스 작업을 하나의 작업 단위로 묶을 때 사용하는 기능이다.
# 현재 의약품 관련 뷰에서는 직접 사용하지 않지만,
# 같은 views.py의 입출고 또는 발주 처리에서 사용할 수 있다.
from django.db import transaction

# 사용자에게 성공, 경고, 오류 등의 일회성 메시지를 전달할 때 사용한다.
# 예: 의약품 등록 완료, 수정 완료, 삭제 완료 메시지
from django.contrib import messages

# Django에서 현재 날짜와 시간을 시간대 설정에 맞게 가져올 때 사용한다.
# 현재 의약품 관련 뷰에서는 직접 사용하지 않지만,
# 발주 입고 완료 시각 등을 기록할 때 사용할 수 있다.
from django.utils import timezone

# F는 데이터베이스 필드끼리 값을 비교하거나 계산할 때 사용하고,
# Q는 여러 검색 조건을 OR 또는 복합 조건으로 묶을 때 사용한다.
from django.db.models import F, Q

# 조회 결과를 여러 페이지로 나누기 위한 페이지네이션 기능이다.
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

# 승인된 약국 사용자만 inventory 기능에 접근할 수 있도록 검사하는 데코레이터이다.
from .decorators import approved_pharmacy_required

# 누가 어떤 작업을 수행했는지 기록하기 위한 감사 로그 모델이다.
from consultations.models import AuditLog


# Django가 기본으로 생성하는 안내 주석이다.
# 이 파일에 요청을 처리하는 뷰 함수를 작성한다.
# Create your views here.

# 현재 inventory 앱에서 사용하는 폼 클래스들을 가져온다.
from .forms import (
    MedicineForm,
    InventoryTransactionForm,
    PurchaseOrderForm,
)

# 현재 inventory 앱의 모델 클래스들을 가져온다.
from .models import Medicine, InventoryTransaction, PurchaseOrder


# =========================================================
# 의약품 관련 뷰
# =========================================================


# 의약품 목록을 조회하고 검색, 재고 상태 필터,
# 페이지네이션을 적용하여 화면에 표시하는 뷰이다.
@approved_pharmacy_required
def medicine_list(request):

    # 현재 로그인한 사용자가 소속된 약국의 의약품만 조회한다.
    # 다른 약국의 의약품 데이터가 목록에 노출되지 않도록
    # pharmacy 조건을 반드시 적용한다.
    medicines = (
        Medicine.objects
        .filter(pharmacy=request.user.pharmacy)
        .order_by("name")
    )

    # URL의 GET 파라미터 중 q 값을 가져온다.
    # 검색어가 전달되지 않으면 빈 문자열을 사용한다.
    # strip()은 검색어 앞뒤의 불필요한 공백을 제거한다.
    query = request.GET.get("q", "").strip()

    # URL의 GET 파라미터 중 stock_filter 값을 가져온다.
    # 값이 전달되지 않으면 기본값으로 "all"을 사용한다.
    stock_filter = request.GET.get("stock_filter", "all")

    # 검색어가 입력된 경우에만 검색 조건을 추가한다.
    if query:

        # 의약품명 또는 제조사명에 검색어가 포함된 의약품을 조회한다.
        medicines = medicines.filter(
            # name__icontains는 대소문자를 구분하지 않고
            # 의약품명에 검색어가 포함되어 있는지 검사한다.
            Q(name__icontains=query)

            # | 연산자는 두 Q 조건을 OR 조건으로 연결한다.
            # 따라서 의약품명이나 제조사명 중 하나만 일치해도 조회된다.
            | Q(manufacturer__icontains=query)
        )

    # 사용자가 재고 부족 필터를 선택한 경우 실행한다.
    if stock_filter == "low":

        # 현재 재고가 최소 재고 이하인 의약품만 조회한다.
        # F("minimum_stock")을 사용하면 Python으로 값을 가져오지 않고
        # 데이터베이스 내부에서 stock 필드와 minimum_stock 필드를 비교한다.
        medicines = medicines.filter(
            stock__lte=F("minimum_stock")
        )

    # 사용자가 정상 재고 필터를 선택한 경우 실행한다.
    elif stock_filter == "normal":

        # 현재 재고가 최소 재고보다 많은 의약품만 조회한다.
        medicines = medicines.filter(
            stock__gt=F("minimum_stock")
        )

    # 조회된 의약품 목록을 한 페이지당 10개씩 나누는
    # Paginator 객체를 생성한다.
    paginator = Paginator(medicines, 10)

    # URL의 GET 파라미터에서 현재 페이지 번호를 가져온다.
    # 예: ?page=2이면 "2"가 저장된다.
    page_number = request.GET.get("page")

    # 요청된 페이지에 해당하는 Page 객체를 가져온다.
    # 페이지 번호가 없거나 잘못된 경우에도 get_page()가
    # 적절한 첫 페이지 또는 마지막 페이지를 반환한다.
    page_obj = paginator.get_page(page_number)

    # 템플릿으로 전달할 데이터를 딕셔너리 형태로 구성한다.
    context = {
        # 기존 템플릿에서 medicines라는 이름으로 반복 출력할 수 있도록
        # 현재 페이지의 Page 객체를 전달한다.
        "medicines": page_obj,

        # 페이지 번호, 이전·다음 페이지, 전체 페이지 수 등을
        # 템플릿에서 사용하기 위해 같은 Page 객체를 전달한다.
        "page_obj": page_obj,

        # 검색창에 기존 검색어를 유지하거나
        # 현재 검색 조건을 표시하기 위해 전달한다.
        "query": query,

        # 현재 선택된 재고 필터를 화면에서 유지하기 위해 전달한다.
        "stock_filter": stock_filter,
    }

    # 의약품 목록 템플릿을 렌더링하여 사용자에게 반환한다.
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


# =========================================================
# 의약품 등록
# =========================================================

# 새로운 의약품을 등록하는 뷰이다.
# GET 요청에서는 빈 폼을 보여주고,
# POST 요청에서는 사용자가 입력한 내용을 검증하고 저장한다.
@approved_pharmacy_required
def medicine_create(request):

    # 폼 제출 요청인지 확인한다.
    if request.method == "POST":

        # POST로 전달된 일반 입력값과
        # FILES로 전달된 이미지 파일을 사용해 폼 객체를 생성한다.
        form = MedicineForm(
            request.POST,
            request.FILES,
        )

        # 필수값, 데이터 형식, 모델 제약조건 등을 검사한다.
        if form.is_valid():

            # commit=False를 사용하여 데이터베이스에 즉시 저장하지 않고
            # 아직 저장되지 않은 Medicine 객체만 생성한다.
            # 폼에 포함되지 않은 pharmacy 값을 추가하기 위해 사용한다.
            medicine = form.save(commit=False)

            # 등록되는 의약품의 소속 약국을
            # 현재 로그인한 사용자의 약국으로 지정한다.
            medicine.pharmacy = request.user.pharmacy

            # 약국 정보까지 설정된 Medicine 객체를 데이터베이스에 저장한다.
            medicine.save()

            # 다음 화면에서 사용자에게 한 번 표시할
            # 등록 완료 성공 메시지를 저장한다.
            messages.success(
                request,
                "의약품이 등록되었습니다.",
            )

            # 등록이 완료되면 의약품 목록 페이지로 이동한다.
            # POST 처리 후 redirect하여 새로고침으로 인한
            # 중복 등록 문제를 방지한다.
            return redirect("inventory:medicine_list")

    # GET 요청인 경우 실행한다.
    else:

        # 아무 데이터도 입력되지 않은 빈 의약품 폼을 생성한다.
        form = MedicineForm()

    # 등록 폼 템플릿으로 전달할 데이터를 구성한다.
    context = {
        # 화면에 출력할 폼 객체이다.
        "form": form,

        # 등록과 수정이 같은 템플릿을 공유하므로
        # 현재 화면의 제목을 별도로 전달한다.
        "page_title": "의약품 등록",

        # 제출 버튼에 표시할 문구를 전달한다.
        "submit_text": "등록",
    }

    # 의약품 등록 폼 템플릿을 렌더링한다.
    return render(
        request,
        "inventory/medicine_form.html",
        {
            "form": form,
            "page_title": "의약품 등록",
            "submit_text": "등록",
        },
    )


# =========================================================
# 의약품 수정
# =========================================================

# 기존에 등록된 의약품 정보를 수정하는 뷰이다.
# URL에서 전달받은 pk 값으로 수정 대상 의약품을 찾는다.
@approved_pharmacy_required
def medicine_update(request, pk):

    # 기본키가 pk와 일치하면서,
    # 현재 사용자의 약국에 속한 의약품만 조회한다.
    # 조건에 맞는 객체가 없으면 자동으로 404 응답을 반환한다.
    # pharmacy 조건으로 다른 약국의 의약품 수정 접근을 막는다.
    medicine = get_object_or_404(
        Medicine,
        pk=pk,
        pharmacy=request.user.pharmacy,
    )

    # 수정 폼이 제출된 경우 실행한다.
    if request.method == "POST":

        # 사용자가 제출한 값과 이미지 파일로 폼을 생성한다.
        # instance=medicine을 지정했기 때문에
        # 새로운 의약품을 만드는 것이 아니라 기존 객체를 수정한다.
        form = MedicineForm(
            request.POST,
            request.FILES,
            instance=medicine,
        )

        # 입력값이 유효한지 검사한다.
        if form.is_valid():

            # 검증된 값으로 기존 Medicine 객체를 수정하여 저장한다.
            form.save()

            # 누가 어떤 의약품 정보를 수정했는지 감사 로그에 기록한다.
            AuditLog.objects.create(
                user=request.user,
                action="의약품 정보 수정",
                target=f"Medicine #{medicine.pk}",
                detail=medicine.name,
            )

            # 수정 완료 메시지를 저장한다.
            messages.success(
                request,
                "의약품 정보가 수정되었습니다.",
            )

            # 수정된 의약품의 상세 페이지로 이동한다.
            return redirect(
                "inventory:medicine_detail",
                pk=medicine.pk,
            )

    # 처음 수정 페이지에 접근한 GET 요청인 경우 실행한다.
    else:

        # 기존 의약품 정보를 초기값으로 채운 수정 폼을 생성한다.
        form = MedicineForm(instance=medicine)

    # 수정 폼 템플릿으로 전달할 데이터를 구성한다.
    context = {
        "form": form,
        "page_title": "의약품 수정",
        "submit_text": "수정",
    }

    # 등록 화면과 같은 템플릿을 사용하되,
    # 제목과 버튼 문구를 수정용으로 전달한다.
    return render(
        request,
        "inventory/medicine_form.html",
        {
            "form": form,
            "page_title": "의약품 수정",
            "submit_text": "수정",
        },
    )


# =========================================================
# 의약품 상세
# =========================================================

# 특정 의약품의 상세 정보와 최근 입출고 내역을 보여주는 뷰이다.
@approved_pharmacy_required
def medicine_detail(request, pk):

    # 기본키와 현재 사용자의 약국 조건에 맞는 의약품을 조회한다.
    medicine = get_object_or_404(

        # select_related("pharmacy")는 의약품과 연결된 약국 정보를
        # SQL JOIN으로 함께 조회한다.
        # 템플릿에서 medicine.pharmacy를 사용할 때
        # 추가 데이터베이스 조회가 발생하는 것을 줄일 수 있다.
        Medicine.objects.select_related("pharmacy"),

        pk=pk,
        pharmacy=request.user.pharmacy,
    )

    # 해당 의약품과 연결된 최근 입출고 기록을 조회한다.
    # models.py의 related_name="transactions" 설정으로
    # medicine.transactions 형태의 역참조가 가능하다.
    recent_transactions = (
        medicine.transactions

        # 각 입출고 기록과 연결된 의약품을 함께 조회한다.
        # 현재는 이미 특정 medicine에서 역참조하고 있어
        # 필수적이지는 않지만, 템플릿 접근 시 추가 조회를 줄일 수 있다.
        .select_related("created_by")

        # 연결된 모든 입출고 기록을 조회 대상으로 만든다.
        # InventoryTransaction의 Meta.ordering이 적용되어
        # 최근 기록부터 정렬된다.
        .all()[:5]
        # 슬라이싱을 사용하여 가장 최근 입출고 기록 5건만 가져온다.
    )

    # 상세 페이지 템플릿으로 전달할 데이터를 구성한다.
    context = {
        # 상세 화면에 표시할 의약품 객체이다.
        "medicine": medicine,

        # 해당 의약품의 최근 입출고 기록 최대 5건이다.
        "recent_transactions": recent_transactions,
    }

    # 의약품 상세 페이지를 렌더링한다.
    return render(
        request,
        "inventory/medicine_detail.html",
        {
            "medicine": medicine,
            "recent_transactions": recent_transactions,
        },
    )


# =========================================================
# 의약품 삭제
# =========================================================

# 특정 의약품의 삭제 확인 화면을 보여주고,
# 사용자가 확인하면 실제 삭제를 수행하는 뷰이다.
@approved_pharmacy_required
def medicine_delete(request, pk):

    # 삭제 대상 의약품을 기본키와 현재 약국 조건으로 조회한다.
    # 다른 약국의 의약품을 삭제하지 못하도록 pharmacy 조건을 적용한다.
    medicine = get_object_or_404(
        Medicine,
        pk=pk,
        pharmacy=request.user.pharmacy,
    )

    # 삭제 확인 폼이 POST 방식으로 제출된 경우에만
    # 실제 삭제를 수행한다.
    if request.method == "POST":

        # 객체를 삭제하기 전에 의약품명을 별도 변수에 저장한다.
        # delete() 실행 후에도 성공 메시지에서 이름을 사용하기 위함이다.
        medicine_name = medicine.name
        medicine_pk = medicine.pk

        # 해당 의약품 객체를 데이터베이스에서 삭제한다.
        # 입출고 또는 발주 기록이 연결되어 있고
        # 외래키가 PROTECT로 설정되어 있다면 삭제가 제한될 수 있다.
        try:
            medicine.delete()
        except ProtectedError:
            messages.error(
                request,
                "입출고 또는 발주 기록이 있는 의약품은 삭제할 수 없습니다.",
            )
            return redirect(
                "inventory:medicine_detail",
                pk=medicine.pk,
            )

        # 누가 어떤 의약품을 삭제했는지 감사 로그에 기록한다.
        AuditLog.objects.create(
            user=request.user,
            action="의약품 삭제",
            target=f"Medicine #{medicine_pk}",
            detail=medicine_name,
        )

        # 삭제 완료 메시지를 저장한다.
        messages.success(
            request,
            f"{medicine_name} 의약품이 삭제되었습니다.",
        )

        # 삭제 후 의약품 목록 페이지로 이동한다.
        return redirect("inventory:medicine_list")

    # GET 요청에서는 바로 삭제하지 않고
    # 사용자에게 삭제 여부를 확인하는 페이지를 보여준다.
    return render(
        request,
        "inventory/medicine_confirm_delete.html",
        {"medicine": medicine},
    )


    
    
    
    
    
    
# ============ 입출고 (Transaction) ==============





# =========================================================
# 입출고 내역 목록
# =========================================================

# 현재 로그인한 사용자의 약국에서 발생한 입출고 내역을 조회하고,
# 검색, 입고·출고 필터, 페이지네이션을 적용하여 화면에 표시하는 뷰이다.
@approved_pharmacy_required
def transaction_list(request):

    # 현재 로그인한 사용자가 소속된 약국의 입출고 내역만 조회한다.
    transactions = (
        InventoryTransaction.objects

        # InventoryTransaction 모델에는 pharmacy 필드가 직접 존재하지 않으므로,
        # 연결된 Medicine 모델의 pharmacy 필드를 통해 현재 약국을 확인한다.
        #
        # medicine__pharmacy처럼 이중 밑줄(__)을 사용하면
        # ForeignKey로 연결된 모델의 필드를 기준으로 조회할 수 있다.
        .filter(
            medicine__pharmacy=request.user.pharmacy,
        )

        # 입출고 내역과 연결된 의약품 및 처리자 정보를
        # SQL JOIN을 사용해 한 번에 함께 조회한다.
        #
        # 템플릿에서 transaction.medicine 또는
        # transaction.created_by에 접근할 때
        # 추가 데이터베이스 조회가 발생하는 것을 줄일 수 있다.
        .select_related(
            "medicine",
            "created_by",
        )

        # 처리일시를 기준으로 내림차순 정렬한다.
        # 가장 최근에 등록된 입출고 내역이 목록 위에 표시된다.
        .order_by("-created_at")
    )

    # URL의 GET 파라미터에서 q 값을 가져온다.
    # 검색어가 전달되지 않으면 빈 문자열을 기본값으로 사용한다.
    # strip()은 검색어 앞뒤의 공백을 제거한다.
    query = request.GET.get("q", "").strip()

    # URL의 GET 파라미터에서 transaction_filter 값을 가져온다.
    # 필터값이 전달되지 않으면 전체 내역을 표시하기 위해
    # 기본값으로 "all"을 사용한다.
    transaction_filter = request.GET.get(
        "transaction_filter",
        "all",
    )

    # 검색어가 입력된 경우에만 검색 조건을 적용한다.
    if query:

        # 의약품명, 제조사명, 비고 중 하나에 검색어가 포함된
        # 입출고 내역을 조회한다.
        transactions = transactions.filter(

            # 연결된 Medicine 모델의 name 필드에서 검색한다.
            # icontains는 대소문자를 구분하지 않고
            # 해당 문자열이 포함되어 있는지 검사한다.
            Q(medicine__name__icontains=query)

            # | 연산자는 Q 객체들을 OR 조건으로 연결한다.
            # 따라서 의약품명, 제조사명, 비고 중 하나만 일치해도 조회된다.
            | Q(medicine__manufacturer__icontains=query)

            # 입출고 등록 시 작성한 비고에서도 검색한다.
            | Q(note__icontains=query)
        )

    # 사용자가 입고 내역 필터를 선택한 경우 실행한다.
    if transaction_filter == "in":

        # transaction_type 값이 IN인 입출고 내역만 조회한다.
        # 문자열 "IN"을 직접 작성하는 대신
        # 모델에 정의된 TextChoices 값을 사용한다.
        transactions = transactions.filter(
            transaction_type=InventoryTransaction.TransactionType.IN,
        )

    # 사용자가 출고 내역 필터를 선택한 경우 실행한다.
    elif transaction_filter == "out":

        # transaction_type 값이 OUT인 입출고 내역만 조회한다.
        transactions = transactions.filter(
            transaction_type=InventoryTransaction.TransactionType.OUT,
        )

    # 검색 및 필터가 적용된 입출고 내역을
    # 한 페이지당 10개씩 나누는 Paginator 객체를 생성한다.
    paginator = Paginator(transactions, 10)

    # URL의 GET 파라미터에서 현재 페이지 번호를 가져온다.
    # 예: ?page=2이면 두 번째 페이지를 요청한 것이다.
    page_number = request.GET.get("page")

    # 요청한 페이지 번호에 해당하는 Page 객체를 가져온다.
    # 페이지 번호가 없거나 올바르지 않아도 get_page()가
    # 적절한 첫 페이지 또는 마지막 페이지를 반환한다.
    page_obj = paginator.get_page(page_number)

    # 템플릿으로 전달할 데이터를 딕셔너리 형태로 구성한다.
    context = {

        # 현재 페이지에 포함된 입출고 내역을 전달한다.
        # 템플릿에서는 transactions를 반복하여 목록을 출력할 수 있다.
        "transactions": page_obj,

        # 이전·다음 페이지 여부, 현재 페이지 번호,
        # 전체 페이지 수 등을 사용하기 위해 Page 객체를 전달한다.
        "page_obj": page_obj,

        # 검색 후에도 검색창에 기존 검색어를 유지하기 위해 전달한다.
        "query": query,

        # 현재 선택된 입고·출고 필터 상태를
        # 화면에서 유지하기 위해 전달한다.
        "transaction_filter": transaction_filter,
    }

    # 입출고 내역 목록 템플릿을 렌더링하여 사용자에게 반환한다.
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


# =========================================================
# 입출고 등록
# =========================================================

# 새로운 입고 또는 출고 내역을 등록하고,
# 등록된 수량만큼 Medicine 모델의 현재 재고를 변경하는 뷰이다.
#
# GET 요청에서는 빈 입력 폼을 보여주고,
# POST 요청에서는 입력값 검증, 재고 변경, 입출고 기록 생성을 처리한다.
@approved_pharmacy_required
def transaction_create(request):

    # 사용자가 입출고 등록 폼을 제출한 경우 실행한다.
    if request.method == "POST":

        # POST 요청으로 전달된 입력값을 사용해
        # 입출고 등록 폼 객체를 생성한다.
        form = InventoryTransactionForm(
            request.POST,
            pharmacy=request.user.pharmacy,
        )

        # 모델 필드 형식, 필수값, 최소 수량 등의
        # 유효성 검사를 통과했는지 확인한다.
        if form.is_valid():

            # form.cleaned_data에는 form.is_valid() 검사를 통과하여
            # 정리되고 검증된 안전한 입력값이 저장된다.

            # 사용자가 선택한 Medicine 객체의 기본키를 가져온다.
            # 이후 select_for_update()를 사용해 같은 의약품을 다시 조회한다.
            medicine_id = form.cleaned_data["medicine"].pk

            # 사용자가 선택한 입출고 구분값을 가져온다.
            # 값은 InventoryTransaction.TransactionType에 정의된
            # "IN" 또는 "OUT" 중 하나이다.
            transaction_type = form.cleaned_data["transaction_type"]

            # 사용자가 입력한 입고 또는 출고 수량을 가져온다.
            quantity = form.cleaned_data["quantity"]

            # 사용자가 입력한 비고 내용을 가져온다.
            # 비고를 입력하지 않은 경우 빈 문자열이 들어올 수 있다.
            note = form.cleaned_data["note"]

            # 아래 데이터베이스 작업들을 하나의 트랜잭션으로 묶는다.
            #
            # 1. Medicine 모델의 현재 재고 변경
            # 2. InventoryTransaction 입출고 기록 생성
            #
            # 처리 중 오류가 발생하면 두 작업을 모두 취소하여
            # 재고만 변경되거나 기록만 생성되는 불일치를 방지한다.
            with transaction.atomic():

                # 사용자가 선택한 의약품을 기본키로 다시 조회한다.
                medicine = (
                    Medicine.objects

                    # 조회된 의약품 데이터베이스 행에 잠금을 건다.
                    #
                    # 한 사용자가 재고를 변경하는 동안
                    # 다른 사용자가 같은 의약품의 재고를 동시에 변경하는 것을 막아
                    # 동시 처리 과정에서 재고 수량이 잘못 계산되는 것을 방지한다.
                    .select_for_update()

                    # 사용자가 선택한 의약품의 기본키로 객체를 가져온다.
                    .get(
                        pk=medicine_id,
                        pharmacy=request.user.pharmacy,
                    )
                )

                # 출고 요청인 동시에 현재 재고보다 출고 수량이 큰지 검사한다.
                if (
                    transaction_type
                    == InventoryTransaction.TransactionType.OUT
                    and medicine.stock < quantity
                ):

                    # 현재 재고보다 많은 수량은 출고할 수 없으므로
                    # quantity 필드에 직접 오류 메시지를 추가한다.
                    #
                    # 오류가 추가된 폼은 아래 렌더링 과정에서 다시 표시되며,
                    # 사용자는 수량 입력란 근처에서 오류 내용을 확인할 수 있다.
                    form.add_error(
                        "quantity",
                        (
                            f"현재 재고는 {medicine.stock}개입니다. "
                            "현재 재고보다 많이 출고할 수 없습니다."
                        ),
                    )

                # 출고 수량에 문제가 없는 경우 재고 변경을 처리한다.
                else:

                    # 입출고 구분이 입고인 경우 실행한다.
                    if (
                        transaction_type
                        == InventoryTransaction.TransactionType.IN
                    ):

                        # 기존 재고에 입력한 입고 수량을 더한다.
                        medicine.stock += quantity

                    # 입고가 아닌 경우 출고로 처리한다.
                    else:

                        # 기존 재고에서 입력한 출고 수량을 뺀다.
                        medicine.stock -= quantity

                    # 변경된 의약품 재고를 데이터베이스에 저장한다.
                    medicine.save(

                        # 전체 필드를 갱신하지 않고
                        # 변경된 stock과 자동 수정 시각 updated_at만 갱신한다.
                        #
                        # 불필요한 데이터베이스 필드 업데이트를 줄일 수 있다.
                        update_fields=[
                            "stock",
                            "updated_at",
                        ],
                    )

                    # 재고 변경 내용을 입출고 내역으로 새롭게 생성한다.
                    InventoryTransaction.objects.create(

                        # 재고를 변경한 대상 의약품이다.
                        medicine=medicine,

                        # 입고인지 출고인지 저장한다.
                        transaction_type=transaction_type,

                        # 실제 처리한 입고 또는 출고 수량을 저장한다.
                        quantity=quantity,

                        # 사용자가 입력한 추가 비고를 저장한다.
                        note=note,

                        # 현재 로그인한 사용자를 입출고 처리자로 저장한다.
                        created_by=request.user,
                    )

                    # 입출고 처리가 완료되었다는 성공 메시지를 저장한다.
                    messages.success(
                        request,
                        (
                            # 처리한 의약품 이름을 표시한다.
                            f"{medicine.name} "

                            # 처리한 수량을 표시한다.
                            f"{quantity}개 "

                            # 입출고 구분에 따라 화면에 표시할 문구를 결정한다.
                            # IN이면 "입고", 그 외에는 "출고"를 사용한다.
                            f"{'입고' if transaction_type == InventoryTransaction.TransactionType.IN else '출고'}"

                            # 최종 완료 문구를 연결한다.
                            f" 처리가 완료되었습니다."
                        ),
                    )

                    # 입출고 처리가 정상 완료되면
                    # 입출고 내역 목록 페이지로 이동한다.
                    #
                    # POST 처리 후 redirect를 사용하므로
                    # 사용자가 새로고침했을 때 같은 입출고가
                    # 중복 등록되는 문제를 방지할 수 있다.
                    return redirect(
                        "inventory:transaction_list",
                    )

    # 처음 입출고 등록 페이지에 접근한 GET 요청인 경우 실행한다.
    else:

        # 아무 입력값도 없는 빈 입출고 등록 폼을 생성한다.
        form = InventoryTransactionForm(
            pharmacy=request.user.pharmacy,
        )

    # 의약품 기본키와 현재 재고를 키-값 형태로 구성한다.
    #
    # 예:
    # {
    #     "1": 30,
    #     "2": 15,
    # }
    #
    # transaction_form.html의 JavaScript가 사용자가 선택한 의약품 ID를 이용해
    # 해당 의약품의 현재 재고를 화면에 표시할 때 사용한다.
    medicine_stocks = {

        # JavaScript 객체의 키로 사용하기 쉽도록
        # 의약품 기본키를 문자열로 변환한다.
        str(medicine.pk): medicine.stock

        # 등록된 모든 의약품을 순회하면서
        # 각 의약품의 기본키와 현재 재고를 딕셔너리에 저장한다.
        for medicine in Medicine.objects.filter(
            pharmacy=request.user.pharmacy,
        )
    }

    # 입출고 등록 템플릿으로 전달할 데이터를 구성한다.
    context = {

        # 입력값과 오류 메시지를 포함한 폼 객체이다.
        "form": form,

        # 등록·수정 공용 폼 형식에 사용할 화면 제목이다.
        "page_title": "입출고 등록",

        # 제출 버튼에 표시할 문구이다.
        "submit_text": "등록",

        # JavaScript에서 선택된 의약품의 현재 재고를 표시하기 위한 데이터이다.
        "medicine_stocks": medicine_stocks,
    }

    # 입출고 등록 폼 템플릿을 렌더링하여 사용자에게 반환한다.
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







# =========================================================
# 발주 목록
# =========================================================

# 현재 로그인한 사용자의 약국에 등록된 발주 내역을 조회하고,
# 페이지네이션을 적용하여 목록 화면에 표시하는 뷰이다.
@approved_pharmacy_required
def purchase_order_list(request):

    # 현재 사용자의 약국과 연결된 의약품에 대한 발주 내역만 조회한다.
    purchase_orders = (
        PurchaseOrder.objects

        # PurchaseOrder 모델에는 pharmacy 필드가 직접 없으므로
        # 발주와 연결된 Medicine 모델의 pharmacy 필드를 기준으로 필터링한다.
        #
        # 이를 통해 다른 약국의 발주 내역이 현재 사용자에게
        # 노출되는 것을 방지한다.
        .filter(
            medicine__pharmacy=request.user.pharmacy
        )

        # 발주 내역과 연결된 의약품 및 발주자 정보를
        # SQL JOIN으로 함께 조회한다.
        #
        # 템플릿에서 purchase_order.medicine 또는
        # purchase_order.ordered_by를 출력할 때
        # 추가 데이터베이스 조회가 반복되는 것을 줄일 수 있다.
        .select_related(
            "medicine",
            "ordered_by",
        )
        .select_related("medicine", "ordered_by")
        .order_by("-created_at")
    )

    # 조회된 발주 목록을 한 페이지당 10개씩 나눈다.
    #
    # PurchaseOrder 모델의 Meta.ordering에
    # ordering = ["-created_at"]이 설정되어 있으므로,
    # 별도의 order_by()가 없어도 최근 발주부터 정렬된다.
    paginator = Paginator(
        purchase_orders,
        10,
    )

    # URL의 GET 파라미터에서 현재 페이지 번호를 가져온다.
    # 예: ?page=2이면 두 번째 페이지를 요청한 것이다.
    page_number = request.GET.get("page")

    # 요청된 페이지 번호에 해당하는 Page 객체를 가져온다.
    #
    # get_page()는 페이지 번호가 없거나 잘못된 경우에도
    # 첫 페이지 또는 마지막 페이지를 적절하게 반환한다.
    page_obj = paginator.get_page(page_number)

    # 발주 목록 템플릿을 렌더링한다.
    return render(
        request,
        "inventory/purchase_order_list.html",
        {
            # 현재 페이지에 포함된 발주 내역을 전달한다.
            "purchase_orders": page_obj,

            # 현재 페이지 번호, 전체 페이지 수,
            # 이전·다음 페이지 여부 등을 사용하기 위해 전달한다.
            "page_obj": page_obj,
        },
    )


# =========================================================
# 발주 등록
# =========================================================

# 새로운 의약품 발주를 등록하는 뷰이다.
#
# GET 요청에서는 빈 발주 폼을 보여주고,
# POST 요청에서는 사용자가 입력한 값을 검증한 뒤 발주 내역을 저장한다.
@approved_pharmacy_required
def purchase_order_create(request):

    # 사용자가 발주 등록 폼을 제출한 경우 실행한다.
    if request.method == "POST":

        # POST 요청으로 전달된 입력값을 사용해
        # PurchaseOrderForm 객체를 생성한다.
        form = PurchaseOrderForm(
            request.POST,
            pharmacy=request.user.pharmacy,
        )

    # 처음 발주 등록 페이지에 접근한 GET 요청인 경우 실행한다.
    else:

        # 아무 데이터도 입력되지 않은 빈 발주 폼을 생성한다.
        form = PurchaseOrderForm(
            pharmacy=request.user.pharmacy,
        )

    # 현재 로그인한 사용자가 소속된 약국의 의약품만 조회한다.
    medicines = (
        Medicine.objects

        # 다른 약국의 의약품이 발주 선택 목록에 나타나지 않도록
        # 현재 사용자의 약국 조건을 적용한다.
        .filter(
            pharmacy=request.user.pharmacy
        )

        # 발주 폼의 의약품 선택 목록을
        # 의약품명 기준 오름차순으로 정렬한다.
        .order_by("name")
    )

    # 발주 폼의 medicine 선택 필드에서 사용할 QuerySet을
    # 현재 약국의 의약품 목록으로 다시 지정한다.
    #
    # forms.py에서는 전체 Medicine 객체를 조회하도록 되어 있으므로,
    # 뷰에서 현재 사용자의 약국 의약품만 선택할 수 있도록 제한한다.
    form.fields["medicine"].queryset = medicines

    # POST 요청이면서 폼 입력값이 유효한 경우에만
    # 실제 발주 등록을 처리한다.
    if request.method == "POST" and form.is_valid():

        # commit=False를 사용하여 데이터베이스에 즉시 저장하지 않고
        # 아직 저장되지 않은 PurchaseOrder 객체를 생성한다.
        #
        # 폼에 포함되지 않은 ordered_by 값을 추가하기 위해 사용한다.
        purchase_order = form.save(commit=False)

        # 현재 로그인한 사용자를 발주자로 지정한다.
        purchase_order.ordered_by = request.user

        # 발주자 정보까지 설정된 발주 객체를 데이터베이스에 저장한다.
        #
        # status 필드는 모델의 기본값인 WAIT,
        # 즉 "발주 대기" 상태로 저장된다.
        purchase_order.save()

        # 다음 화면에서 한 번 표시할
        # 발주 등록 완료 메시지를 저장한다.
        messages.success(
            request,
            (
                # 발주한 의약품 이름을 표시한다.
                f"{purchase_order.medicine.name} "

                # 발주 수량을 표시한다.
                f"{purchase_order.quantity}개 발주가 등록되었습니다."
            ),
        )

        # 발주 등록이 완료되면 발주 목록 페이지로 이동한다.
        #
        # POST 처리 후 redirect를 사용하므로,
        # 새로고침으로 같은 발주가 중복 등록되는 것을 방지할 수 있다.
        return redirect(
            "inventory:purchase_order_list"
        )

    # 현재 약국 의약품의 추가 정보를
    # 딕셔너리 목록 형태로 변환한다.
    #
    # 이 데이터는 purchase_order_form.html의 JavaScript에서
    # 선택한 의약품의 제조사, 현재 재고, 최소 재고 등을
    # 화면에 표시하는 데 사용할 수 있다.
    medicine_data = list(
        medicines.values(
            # 의약품을 구분하기 위한 기본키이다.
            "id",

            # 선택한 의약품의 제조사 정보이다.
            "manufacturer",

            # 현재 보유 중인 재고 수량이다.
            "stock",

            # 재고 부족을 판단하는 최소 재고 기준이다.
            "minimum_stock",
        )
    )

    # 발주 등록 템플릿으로 전달할 데이터를 구성한다.
    context = {
        # 입력 필드와 검증 오류를 포함한 발주 폼이다.
        "form": form,

        # JavaScript에서 의약품별 상세 정보를 표시하기 위한 데이터이다.
        "medicine_data": medicine_data,
    }

    # 발주 등록 폼 템플릿을 렌더링하여 반환한다.
    return render(
        request,
        "inventory/purchase_order_form.html",
        {
            "form": form,
            "medicine_data": medicine_data,
        },
    )


# =========================================================
# 발주 완료 처리
# =========================================================

# 발주 대기 상태의 발주를 발주 완료 상태로 변경하는 뷰이다.
#
# 이 단계는 시스템에 등록된 발주 요청을
# 실제 공급업체에 주문한 상태로 변경하는 역할을 한다.
@approved_pharmacy_required
def purchase_order_mark_ordered(request, pk):

    # URL로 전달받은 기본키와 현재 사용자의 약국 조건에 맞는
    # 발주 내역을 조회한다.
    purchase_order = get_object_or_404(
        PurchaseOrder,
        pk=pk,

        # 연결된 의약품이 현재 사용자의 약국에 속하는지 확인한다.
        # 다른 약국의 발주 상태를 변경하지 못하도록 제한한다.
        medicine__pharmacy=request.user.pharmacy,
    )

    # 상태 변경 요청은 POST 방식으로만 처리한다.
    #
    # GET 방식으로 접근한 경우 상태를 변경하지 않고
    # 발주 목록 페이지로 돌려보낸다.
    if request.method != "POST":
        return redirect(
            "inventory:purchase_order_list"
        )

    # 현재 상태가 발주 대기 상태인지 확인한다.
    #
    # 이미 발주 완료, 입고 완료 또는 취소된 내역은
    # 다시 발주 완료 처리할 수 없다.
    if purchase_order.status != PurchaseOrder.Status.WAIT:

        # 상태 변경이 불가능하다는 경고 메시지를 저장한다.
        messages.warning(
            request,
            "발주 대기 상태인 내역만 발주 완료 처리할 수 있습니다.",
        )

        # 경고 메시지를 보여주기 위해 발주 목록으로 이동한다.
        return redirect(
            "inventory:purchase_order_list"
        )

    # 발주 상태를 WAIT에서 ORDERED로 변경한다.
    purchase_order.status = PurchaseOrder.Status.ORDERED

    # 변경된 status 필드만 데이터베이스에 저장한다.
    #
    # update_fields를 사용하면 변경하지 않은 다른 필드는
    # 업데이트하지 않아도 된다.
    purchase_order.save(
        update_fields=[
            "status",
        ]
    )

    # 발주 완료 상태로 변경되었다는 성공 메시지를 저장한다.
    messages.success(
        request,
        "발주 완료 상태로 변경했습니다.",
    )

    # 처리 후 발주 목록 페이지로 이동한다.
    return redirect(
        "inventory:purchase_order_list"
    )


# =========================================================
# 입고 완료 처리
# =========================================================

# 발주 완료 상태의 발주를 실제 입고 완료 상태로 변경하는 뷰이다.
#
# 입고 완료 처리 시 다음 세 가지 작업이 함께 수행된다.
#
# 1. 입고 내역 생성
# 2. 의약품 현재 재고 증가
# 3. 발주 상태와 입고 완료 시각 변경
@approved_pharmacy_required
def purchase_order_receive(request, pk):

    # 기본키와 현재 사용자의 약국 조건에 맞는 발주 내역을 조회한다.
    purchase_order = get_object_or_404(

        # 발주와 연결된 의약품 정보를 SQL JOIN으로 함께 조회한다.
        # 이후 메시지나 처리 과정에서 medicine에 접근할 때
        # 추가 데이터베이스 조회를 줄일 수 있다.
        PurchaseOrder.objects.select_related("medicine"),

        pk=pk,

        # 다른 약국의 발주를 입고 처리하지 못하도록 제한한다.
        medicine__pharmacy=request.user.pharmacy,
    )

    # 입고 완료 처리는 POST 방식으로만 허용한다.
    #
    # GET 요청으로 접근한 경우에는 상태를 변경하지 않고
    # 발주 목록으로 이동한다.
    if request.method != "POST":
        return redirect(
            "inventory:purchase_order_list"
        )

    # 현재 발주 상태가 ORDERED인지 확인한다.
    #
    # 발주 대기, 입고 완료, 취소 상태의 내역은
    # 입고 완료 처리할 수 없다.
    if purchase_order.status != PurchaseOrder.Status.ORDERED:

        # 현재 상태에서는 입고 완료 처리가 불가능하다는
        # 경고 메시지를 저장한다.
        messages.warning(
            request,
            "발주 완료 상태인 내역만 입고 완료 처리할 수 있습니다.",
        )

        # 처리 없이 발주 목록 페이지로 이동한다.
        return redirect(
            "inventory:purchase_order_list"
        )

    # 아래의 데이터베이스 작업을 하나의 트랜잭션으로 묶는다.
    #
    # 처리 도중 하나라도 오류가 발생하면 모든 작업을 취소하여,
    # 재고만 증가하거나 발주 상태만 변경되는 데이터 불일치를 방지한다.
    with transaction.atomic():

        # 발주와 연결된 의약품 객체를 다시 조회한다.
        medicine = (
            Medicine.objects

            # 해당 의약품 데이터베이스 행에 잠금을 건다.
            #
            # 입고 처리 중 다른 사용자가 같은 의약품의 재고를
            # 동시에 변경하는 것을 방지하여 재고 수량의 정확성을 유지한다.
            .select_for_update()

            # PurchaseOrder의 medicine_id 값을 사용해
            # 발주 대상 의약품을 조회한다.
            .get(
                pk=purchase_order.medicine_id
            )
        )

        # 발주 입고에 해당하는 InventoryTransaction 기록을 생성한다.
        InventoryTransaction.objects.create(

            # 입고 대상 의약품이다.
            medicine=medicine,

            # 발주 물품이 들어왔으므로 입출고 구분을 입고로 지정한다.
            transaction_type=(
                InventoryTransaction.TransactionType.IN
            ),

            # 기존 발주에 등록된 수량만큼 입고 처리한다.
            quantity=purchase_order.quantity,

            # 해당 입고 기록이 어떤 발주에서 발생했는지
            # 확인할 수 있도록 발주 기본키를 비고에 기록한다.
            note=(
                f"발주 #{purchase_order.pk} 입고 완료"
            ),

            # 현재 로그인한 사용자를 입고 처리자로 저장한다.
            created_by=request.user,
        )

        # 현재 재고에 발주 수량을 더한다.
        medicine.stock += purchase_order.quantity

        # 변경된 재고와 마지막 수정 시각만 데이터베이스에 저장한다.
        medicine.save(
            update_fields=[
                "stock",
                "updated_at",
            ]
        )

        # 발주 상태를 입고 완료 상태로 변경한다.
        purchase_order.status = PurchaseOrder.Status.RECEIVED

        # Django 프로젝트의 시간대 설정을 반영한
        # 현재 날짜와 시간을 입고 완료 시각으로 기록한다.
        purchase_order.received_at = timezone.now()

        # 변경된 상태와 입고 완료일만 데이터베이스에 저장한다.
        purchase_order.save(
            update_fields=[
                "status",
                "received_at",
            ]
        )

    # 모든 입고 처리가 완료된 후 성공 메시지를 저장한다.
    messages.success(
        request,
        (
            # 입고된 의약품 이름을 표시한다.
            f"{purchase_order.medicine.name} "

            # 입고된 발주 수량을 표시한다.
            f"{purchase_order.quantity}개를 입고 처리했습니다."
        ),
    )

    # 처리 완료 후 발주 목록 페이지로 이동한다.
    return redirect(
        "inventory:purchase_order_list"
    )


# =========================================================
# 발주 취소
# =========================================================

# 발주 대기 또는 발주 완료 상태의 발주를 취소 상태로 변경하는 뷰이다.
#
# 이미 입고가 완료된 발주는 재고까지 반영되었으므로 취소할 수 없고,
# 이미 취소된 발주 역시 중복 취소할 수 없다.
@approved_pharmacy_required
def purchase_order_cancel(request, pk):

    # 기본키와 현재 사용자의 약국 조건에 맞는 발주를 조회한다.
    purchase_order = get_object_or_404(
        PurchaseOrder,
        pk=pk,

        # 다른 약국의 발주 내역을 취소하지 못하도록 제한한다.
        medicine__pharmacy=request.user.pharmacy,
    )

    # 발주 취소는 POST 방식으로만 처리한다.
    #
    # GET 방식으로 접근한 경우에는 상태를 변경하지 않고
    # 발주 목록으로 이동한다.
    if request.method != "POST":
        return redirect(
            "inventory:purchase_order_list"
        )

    # 현재 발주가 이미 입고 완료 상태인지 확인한다.
    if purchase_order.status == PurchaseOrder.Status.RECEIVED:

        # 입고 완료된 발주는 이미 재고가 증가했기 때문에
        # 단순 상태 변경만으로 취소할 수 없다는 경고 메시지를 저장한다.
        messages.warning(
            request,
            "이미 입고 완료된 발주는 취소할 수 없습니다.",
        )

        # 상태를 변경하지 않고 발주 목록으로 이동한다.
        return redirect(
            "inventory:purchase_order_list"
        )

    # 현재 발주가 이미 취소 상태인지 확인한다.
    if purchase_order.status == PurchaseOrder.Status.CANCELLED:

        # 같은 발주가 중복 취소되지 않도록 경고 메시지를 저장한다.
        messages.warning(
            request,
            "이미 취소된 발주입니다.",
        )

        # 상태를 변경하지 않고 발주 목록으로 이동한다.
        return redirect(
            "inventory:purchase_order_list"
        )

    # 발주 상태를 취소 상태로 변경한다.
    #
    # 이 조건까지 도달한 발주는 WAIT 또는 ORDERED 상태이다.
    purchase_order.status = PurchaseOrder.Status.CANCELLED

    # 변경된 status 필드만 데이터베이스에 저장한다.
    purchase_order.save(
        update_fields=[
            "status",
        ]
    )

    # 발주 취소가 완료되었다는 성공 메시지를 저장한다.
    messages.success(
        request,
        "발주를 취소했습니다.",
    )

    # 처리 완료 후 발주 목록 페이지로 이동한다.
    return redirect(
        "inventory:purchase_order_list"
    )
