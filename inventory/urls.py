from django.urls import path

from . import views

app_name = 'inventory'

urlpatterns = [
    path("", views.medicine_list, name="medicine_list"),
    path('create/', views.medicine_create, name="medicine_create"),
    path("<int:pk>/update/", views.medicine_update, name="medicine_update"),
]