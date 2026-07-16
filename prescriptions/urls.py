from django.urls import path
from . import views

app_name = 'prescriptions'

urlpatterns = [
    path('logs/', views.audit_log_list, name='audit_logs'),
]