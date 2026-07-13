from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if (
                not request.user.is_superuser
                and request.user.role not in allowed_roles
            ):
                messages.error(
                    request,
                    "해당 페이지에 접근할 권한이 없습니다.",
                )
                return redirect("core:index")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
