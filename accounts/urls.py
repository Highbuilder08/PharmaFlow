from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),

    path("pharmacy/", views.pharmacy_detail, name="pharmacy_detail"),
    path("pharmacy/edit/", views.pharmacy_update, name="pharmacy_update"),

    path("pharmacy-search/", views.pharmacy_search, name="pharmacy_search"),

    path("pharmacies/", views.pharmacy_list, name="pharmacy_list"),
    path("pharmacies/create/", views.pharmacy_create, name="pharmacy_create"),
    path("pharmacies/<int:pk>/delete/", views.pharmacy_delete, name="pharmacy_delete"),

    path("users/", views.user_list, name="user_list"),
    path("users/<int:pk>/approve/", views.user_approve, name="user_approve"),
    path("users/<int:pk>/revoke/", views.user_revoke, name="user_revoke"),
]
