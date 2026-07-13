from django.urls import path
from . import views

app_name = 'prescriptions'

urlpatterns = [
    # [처방전 CRUD]
    path('', views.prescription_list, name='list'),
    path('create/', views.prescription_create, name='create'),
    path('<int:pk>/', views.prescription_detail, name='detail'),
    path('<int:pk>/update/', views.prescription_update, name='update'), # 수정
    path('<int:pk>/delete/', views.prescription_delete, name='delete'), # 삭제
    path('attachment/<int:pk>/delete/', views.attachment_delete, name='attachment_delete'), # [첨부파일 삭제]
    path('prescription/item/<int:pk>/delete/', views.prescription_item_delete, name='item_delete'),
    path('logs/', views.audit_log_list, name='audit_logs'),
]