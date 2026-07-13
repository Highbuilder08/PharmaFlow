from django.urls import path
from . import views

app_name = 'consultations' 

urlpatterns = [
    path('', views.consultation_list, name='list'),
    path('create/', views.consultation_create, name='create'),
    path('<int:pk>/', views.consultation_detail, name='detail'),
    path('<int:pk>/update/', views.consultation_update, name='update'),
    path('<int:pk>/delete/', views.consultation_delete, name='delete'),
    path('comment/<int:pk>/delete/', views.comment_delete, name='comment_delete'),
]