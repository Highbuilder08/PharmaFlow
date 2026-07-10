# prescriptions/urls.py

from django.urls import path
from . import views

app_name = 'prescriptions'

urlpatterns = [
    # 처방전 URL
    path('', views.prescription_list, name='list'),
    path('create/', views.prescription_create, name='create'),
    path('<int:pk>/', views.prescription_detail, name='detail'),
    path('<int:pk>/delete/', views.prescription_delete, name='delete'),
    
    # 복약 상담 게시판 URL
    path('consultation/', views.consultation_list, name='consultation_list'),
    path('consultation/create/', views.consultation_create, name='consultation_create'),
    path('consultation/<int:pk>/', views.consultation_detail, name='consultation_detail'),
    path('consultation/<int:pk>/delete/', views.consultation_delete, name='consultation_delete'), 
    
    # 댓글 삭제 URL
    path('comment/<int:pk>/delete/', views.comment_delete, name='comment_delete'), 
]