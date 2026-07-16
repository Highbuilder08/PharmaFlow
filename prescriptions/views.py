from django.shortcuts import render, redirect
from django.contrib import messages
from .models import AuditLog
from consultations.views import login_message_required 

@login_message_required
def audit_log_list(request):
    # 관리자(superuser)가 아니면 접근 차단
    if not request.user.is_superuser:
        messages.warning(request, "관리자만 접근 가능한 페이지입니다.")
        return redirect('core:index') # 권한 없으면 메인 화면으로 튕겨냄
    
    logs = AuditLog.objects.all()
    return render(request, 'prescriptions/audit_logs.html', {'logs': logs})