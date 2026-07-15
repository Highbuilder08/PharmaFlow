import json

from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import (
    Pharmacy,
    PharmacyOwnershipRequest,
    User,
)
from consultations.models import Consultation

from .models import CalendarMemo


def index(request):
    notices = (
        Consultation.objects.filter(tag="NOTICE")
        .select_related("writer")
        .order_by("-created_at")[:3]
    )

    recent_posts = (
        Consultation.objects.exclude(tag="NOTICE")
        .select_related("writer")
        .order_by("-created_at")[:5]
    )

    context = {
        "notices": notices,
        "recent_posts": recent_posts,
    }

    # 관리자 전용 대시보드 정보
    if request.user.is_authenticated and request.user.is_superuser:
        today = timezone.localdate()

        context.update(
            {
                "pharmacy_total": Pharmacy.objects.count(),
                "ownership_pending_count": (
                    PharmacyOwnershipRequest.objects.filter(
                        status=PharmacyOwnershipRequest.Status.PENDING,
                    ).count()
                ),
                "user_total": User.objects.count(),
                "today_joined_count": User.objects.filter(
                    date_joined__date=today,
                ).count(),
                "recent_ownership_requests": (
                    PharmacyOwnershipRequest.objects.filter(
                        status=PharmacyOwnershipRequest.Status.PENDING,
                    )
                    .select_related(
                        "user",
                        "pharmacy",
                    )
                    .order_by("-created_at")[:5]
                ),
            },
        )

    return render(
        request,
        "core/index.html",
        context,
    )


@login_required
@require_GET
def calendar_memo_detail(request):
    date_text = request.GET.get("date", "").strip()

    try:
        memo_date = datetime.strptime(
            date_text,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return JsonResponse(
            {
                "success": False,
                "message": "올바른 날짜가 아닙니다.",
            },
            status=400,
        )

    memo = CalendarMemo.objects.filter(
        user=request.user,
        memo_date=memo_date,
    ).first()

    return JsonResponse(
        {
            "success": True,
            "date": memo_date.isoformat(),
            "content": memo.content if memo else "",
            "exists": memo is not None,
        },
    )


@login_required
@require_POST
def calendar_memo_save(request):
    try:
        data = json.loads(request.body.decode("utf-8"))

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "success": False,
                "message": "요청 형식이 올바르지 않습니다.",
            },
            status=400,
        )

    date_text = str(data.get("date", "")).strip()
    content = str(data.get("content", "")).strip()

    try:
        memo_date = datetime.strptime(
            date_text,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return JsonResponse(
            {
                "success": False,
                "message": "올바른 날짜가 아닙니다.",
            },
            status=400,
        )

    if len(content) > 2000:
        return JsonResponse(
            {
                "success": False,
                "message": "메모는 2,000자 이하로 입력해 주세요.",
            },
            status=400,
        )

    if not content:
        CalendarMemo.objects.filter(
            user=request.user,
            memo_date=memo_date,
        ).delete()

        return JsonResponse(
            {
                "success": True,
                "deleted": True,
                "message": "메모가 삭제되었습니다.",
            },
        )

    memo, created = CalendarMemo.objects.update_or_create(
        user=request.user,
        memo_date=memo_date,
        defaults={
            "content": content,
        },
    )

    return JsonResponse(
        {
            "success": True,
            "created": created,
            "content": memo.content,
            "message": "메모가 저장되었습니다.",
        },
    )


@login_required
@require_GET
def calendar_memo_dates(request):
    year_text = request.GET.get("year", "")
    month_text = request.GET.get("month", "")

    try:
        year = int(year_text)
        month = int(month_text)

        if month < 1 or month > 12:
            raise ValueError

    except ValueError:
        return JsonResponse(
            {
                "success": False,
                "message": "연도 또는 월이 올바르지 않습니다.",
            },
            status=400,
        )

    memo_dates = CalendarMemo.objects.filter(
        user=request.user,
        memo_date__year=year,
        memo_date__month=month,
    ).values_list(
        "memo_date",
        flat=True,
    )

    return JsonResponse(
        {
            "success": True,
            "dates": [memo_date.isoformat() for memo_date in memo_dates],
        },
    )
