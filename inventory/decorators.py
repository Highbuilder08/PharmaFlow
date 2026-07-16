from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def approved_pharmacy_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect("login")
        if not user.is_superuser and (not user.is_approved or not user.pharmacy_id):
            messages.error(request, "승인된 소속 약국 사용자만 재고 관리 기능을 이용할 수 있습니다.")
            return redirect("core:index")
        if user.is_superuser and not user.pharmacy_id:
            messages.error(request, "재고 관리 대상 약국을 가진 계정으로 접속해 주세요.")
            return redirect("core:index")
        return view_func(request, *args, **kwargs)
    return wrapper
