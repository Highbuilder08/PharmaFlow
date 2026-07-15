from django.urls import path

from . import views

app_name = 'inventory'

urlpatterns = [
    path("", views.medicine_list, name="medicine_list"),
    path('create/', views.medicine_create, name="medicine_create"),
    
    path('transactions/', views.transaction_list, name="transaction_list"),
    path("transactions/create/", views.transaction_create, name="transaction_create"),
    
    path("purchase-orders/", views.purchase_order_list, name="purchase_order_list"),
    path("purchase-orders/create/", views.purchase_order_create, name="purchase_order_create"),
    
    
    path("<int:pk>/detail/", views.medicine_detail, name="medicine_detail"),
    path("<int:pk>/update/", views.medicine_update, name="medicine_update"),
    path("<int:pk>/delete/", views.medicine_delete, name="medicine_delete"),
    
    
]