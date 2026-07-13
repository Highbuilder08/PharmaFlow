from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("pharmacies/", views.pharmacy_list, name="pharmacy_list"),
    path("pharmacies/create/", views.pharmacy_create, name="pharmacy_create"),
    path("pharmacies/<int:pk>/update/", views.pharmacy_update, name="pharmacy_update"),
    path("pharmacies/<int:pk>/delete/", views.pharmacy_delete, name="pharmacy_delete"),
    path(
        "ownership-requests/", 
        views.ownership_request_list, 
        name="ownership_request_list"
        ),

    path(
        "ownership-requests/<int:pk>/approve/", 
        views.ownership_request_approve, 
        name="ownership_request_approve",
    ),

    path(
        "ownership-requests/<int:pk>/reject/",
        views.ownership_request_reject,
        name="ownership_request_reject",
    ),
    
    path(
        "pharmacy-search/",
        views.pharmacy_search,
        name="pharmacy_search",
    ),
]
