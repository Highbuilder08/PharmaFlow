from django.urls import path

from . import views

app_name = 'inventory'

urlpatterns = [
    #의약품
    path("", views.medicine_list, name="medicine_list"),
    path('create/', views.medicine_create, name="medicine_create"),
    path("<int:pk>/detail/", views.medicine_detail, name="medicine_detail"),
    path("<int:pk>/update/", views.medicine_update, name="medicine_update"),
    path("<int:pk>/delete/", views.medicine_delete, name="medicine_delete"),
    
    #재고
    path('transactions/', views.transaction_list, name="transaction_list"),
    path("transactions/create/", views.transaction_create, name="transaction_create"),
    
    #발주
    path("purchase-orders/", views.purchase_order_list, name="purchase_order_list"),
    path("purchase-orders/create/", views.purchase_order_create, name="purchase_order_create"),
    path(
        "purchase-orders/<int:pk>/ordered/",
        views.purchase_order_mark_ordered,
        name="purchase_order_mark_ordered",
    ),
    path(
        "purchase-orders/<int:pk>/receive/",
        views.purchase_order_receive,
        name="purchase_order_receive",
    ),
    path(
        "purchase-orders/<int:pk>/cancel/",
        views.purchase_order_cancel,
        name="purchase_order_cancel",
    ),
    
]