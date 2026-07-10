from django.urls import path
from . import views

app_name = 'prescriptions'

urlpatterns = [
    # 처방전 URL
    path('', views.prescription_list, name='list'),
    path('create/', views.prescription_create, name='create'),
    path('<int:pk>/', views.prescription_detail, name='detail'),
    
    # 상담 게시판 URL
    path('consultation/', views.consultation_list, name='consultation_list'),
    path('consultation/create/', views.consultation_create, name='consultation_create'),
]