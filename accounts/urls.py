from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    # 회원
    path("signup/", views.signup, name="signup"),

    # 점주(본인 약국)
    path("pharmacy/", views.pharmacy_detail, name="pharmacy_detail"),
    path("pharmacy/edit/", views.pharmacy_update, name="pharmacy_update"),
    path("pharmacy-search/", views.pharmacy_search, name="pharmacy_search"),

    # 관리자(전체 약국 관리)
    path("pharmacies/", views.pharmacy_list, name="pharmacy_list"),
    path("pharmacies/create/", views.pharmacy_create, name="pharmacy_create"),
    path("pharmacies/<int:pk>/edit/", views.pharmacy_admin_update, name="pharmacy_admin_update"),
    path("pharmacies/<int:pk>/delete/", views.pharmacy_delete, name="pharmacy_delete"),

    # 직원 관리
    path("users/", views.user_list, name="user_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:pk>/update/", views.user_update, name="user_update"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
    path("users/<int:pk>/approve/", views.user_approve, name="user_approve"),
    path("users/<int:pk>/revoke/", views.user_revoke, name="user_revoke"),
    
    # 점주 승인
    path("ownership-requests/", views.ownership_request_list, name="ownership_request_list"),
    path("ownership-requests/<int:pk>/approve/", views.ownership_request_approve, name="ownership_request_approve"),
    path("ownership-requests/<int:pk>/reject/", views.ownership_request_reject, name="ownership_request_reject"),
]
