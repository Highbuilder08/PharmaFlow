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
    # [상담 게시판 CRUD]
    path('consultation/', views.consultation_list, name='consultation_list'),
    path('consultation/create/', views.consultation_create, name='consultation_create'),
    path('consultation/<int:pk>/', views.consultation_detail, name='consultation_detail'),
    path('consultation/<int:pk>/update/', views.consultation_update, name='consultation_update'), # 수정
    path('consultation/<int:pk>/delete/', views.consultation_delete, name='consultation_delete'), # 삭제
    path('comment/<int:pk>/delete/', views.comment_delete, name='comment_delete'), # 댓글 삭제
]