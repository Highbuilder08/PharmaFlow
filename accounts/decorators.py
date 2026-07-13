from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import User


def superuser_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(
                request,
                "시스템 관리자만 접근할 수 있습니다.",
            )

            return redirect("core:index")

        return view_func(request, *args, **kwargs)

    return wrapper


def owner_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if (
            request.user.role != User.Role.OWNER
            or not request.user.is_approved
            or request.user.pharmacy_id is None
        ):
            messages.error(
                request,
                "소속 약국의 점주만 접근할 수 있습니다.",
            )

            return redirect("core:index")

        return view_func(request, *args, **kwargs)

    return wrapper
