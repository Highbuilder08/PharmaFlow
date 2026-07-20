# Django에서 URL 경로를 등록할 때 사용하는 함수이다.
from django.urls import path

# 현재 inventory 앱의 views.py를 가져온다.
# URL 요청이 들어오면 연결된 View 함수가 실행된다.
from . import views


# =========================================================
# URL Namespace
# =========================================================
#
# app_name은 URL 네임스페이스(namespace)를 지정한다.
#
# 프로젝트에 같은 이름의 URL이 여러 앱에 존재할 수 있으므로
# 앱 이름을 함께 사용하여 구분한다.
#
# 예:
# {% url 'inventory:medicine_list' %}
# redirect("inventory:medicine_list")
app_name = "inventory"


# =========================================================
# Inventory 앱 URL 목록
# =========================================================
#
# urlpatterns는 inventory 앱에서 처리할 URL과
# 실행할 View를 연결하는 목록이다.
#
# Django는 위에서부터 순서대로 URL을 검사하여
# 일치하는 첫 번째 URL을 실행한다.
urlpatterns = [

    # =====================================================
    # 의약품(Medicine)
    # =====================================================

    # 의약품 목록
    #
    # URL:
    # /inventory/
    #
    # 실행 View:
    # medicine_list()
    path(
        "",
        views.medicine_list,
        name="medicine_list",
    ),

    # 의약품 등록
    #
    # URL:
    # /inventory/create/
    #
    # GET : 등록 화면
    # POST : 등록 처리
    path(
        "create/",
        views.medicine_create,
        name="medicine_create",
    ),

    # 의약품 상세
    #
    # URL 예시:
    # /inventory/3/detail/
    #
    # <int:pk>는 URL에서 정수를 받아
    # pk 매개변수로 View에 전달한다.
    path(
        "<int:pk>/detail/",
        views.medicine_detail,
        name="medicine_detail",
    ),

    # 의약품 수정
    #
    # URL 예시:
    # /inventory/3/update/
    path(
        "<int:pk>/update/",
        views.medicine_update,
        name="medicine_update",
    ),

    # 의약품 삭제
    #
    # URL 예시:
    # /inventory/3/delete/
    path(
        "<int:pk>/delete/",
        views.medicine_delete,
        name="medicine_delete",
    ),

    # =====================================================
    # 입출고(InventoryTransaction)
    # =====================================================

    # 입출고 내역 목록
    #
    # URL:
    # /inventory/transactions/
    path(
        "transactions/",
        views.transaction_list,
        name="transaction_list",
    ),

    # 입출고 등록
    #
    # URL:
    # /inventory/transactions/create/
    #
    # GET : 등록 화면
    # POST : 입출고 처리
    path(
        "transactions/create/",
        views.transaction_create,
        name="transaction_create",
    ),

    # =====================================================
    # 발주(PurchaseOrder)
    # =====================================================

    # 발주 목록
    #
    # URL:
    # /inventory/purchase-orders/
    path(
        "purchase-orders/",
        views.purchase_order_list,
        name="purchase_order_list",
    ),

    # 발주 등록
    #
    # URL:
    # /inventory/purchase-orders/create/
    path(
        "purchase-orders/create/",
        views.purchase_order_create,
        name="purchase_order_create",
    ),

    # 발주 완료 처리
    #
    # URL 예시:
    # /inventory/purchase-orders/5/ordered/
    #
    # 발주 대기(WAIT) 상태를
    # 발주 완료(ORDERED) 상태로 변경한다.
    path(
        "purchase-orders/<int:pk>/ordered/",
        views.purchase_order_mark_ordered,
        name="purchase_order_mark_ordered",
    ),

    # 입고 완료 처리
    #
    # URL 예시:
    # /inventory/purchase-orders/5/receive/
    #
    # 발주 완료(ORDERED) 상태를
    # 입고 완료(RECEIVED) 상태로 변경한다.
    #
    # 이 과정에서
    # 1. 입고 내역 생성
    # 2. 재고 증가
    # 3. 입고 완료 시각 저장
    # 이 함께 수행된다.
    path(
        "purchase-orders/<int:pk>/receive/",
        views.purchase_order_receive,
        name="purchase_order_receive",
    ),

    # 발주 취소
    #
    # URL 예시:
    # /inventory/purchase-orders/5/cancel/
    #
    # 발주를 취소(CANCELLED) 상태로 변경한다.
    # 이미 입고 완료된 발주는 취소할 수 없다.
    path(
        "purchase-orders/<int:pk>/cancel/",
        views.purchase_order_cancel,
        name="purchase_order_cancel",
    ),
]