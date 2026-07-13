from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("pharmacies/", views.pharmacy_list, name="pharmacy_list"),
    path("pharmacies/create/", views.pharmacy_create, name="pharmacy_create"),
    path("pharmacies/<int:pk>/update/", views.pharmacy_update, name="pharmacy_update"),
    #path("pharmacies/<int:pk>/delete/", views.pharmacy_delete, name="pharmacy_delete"),
]
