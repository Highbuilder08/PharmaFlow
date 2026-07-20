# ==================================================
# 파일 역할: 사용자 역할과 승인 상태에 따라 접근 권한을 검사하는 데코레이터 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import User


# 시스템 관리자만 해당 뷰를 실행할 수 있도록 검사한다.
def superuser_required(view_func):
    # wrapper 기능을 처리한다.
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


# 승인된 점주만 해당 뷰를 실행할 수 있도록 검사한다.
def owner_required(view_func):
    # wrapper 기능을 처리한다.
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


# 직원 관리 권한이 있는 사용자만 해당 뷰를 실행할 수 있도록 검사한다.
def staff_manager_required(view_func):
    # wrapper 기능을 처리한다.
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user

        can_manage_staff = (
            user.is_authenticated
            and user.is_approved
            and user.pharmacy_id is not None
            and user.role in (
                User.Role.OWNER,
                User.Role.PHARMACIST,
            )
        )

        if not can_manage_staff:
            messages.error(
                request,
                "직원 관리 권한이 없습니다.",
            )

            return redirect("core:index")

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return wrapper
