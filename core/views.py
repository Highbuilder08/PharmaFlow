# ==================================================
# 파일 역할: 메인 화면과 달력 메모 조회·저장 기능을 처리하는 뷰 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

import json

from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, connection
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from accounts.models import (
    Pharmacy,
    PharmacyOwnershipRequest,
    User,
)
from consultations.models import Consultation
from inventory.models import Medicine

from .models import CalendarMemo


# -------------------- 메인 화면: 메인 화면에 공지, 최근 게시글과 관리자용 요약 정보를 전달한다. --------------------
@ensure_csrf_cookie
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
        current_timezone = timezone.get_current_timezone()
        today_start = timezone.make_aware(
            datetime.combine(today, time.min),
            current_timezone,
        )
        tomorrow_start = timezone.make_aware(
            datetime.combine(today + timedelta(days=1), time.min),
            current_timezone,
        )

        context.update(
            {
                "pharmacy_total": Pharmacy.objects.count(),
                "ownership_pending_count": (
                    PharmacyOwnershipRequest.objects.filter(
                        status=PharmacyOwnershipRequest.Status.PENDING,
                    ).count()
                ),
                "user_total": User.objects.count(),
                # 현재 Django 시간대를 기준으로 오늘 00:00 이상,
                # 내일 00:00 미만에 가입한 회원을 집계한다.
                # 날짜 변환을 DB에 맡기는 date_joined__date 방식보다
                # DB 시간대 설정 차이의 영향을 덜 받는다.
                "today_joined_count": User.objects.filter(
                    date_joined__gte=today_start,
                    date_joined__lt=tomorrow_start,
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

    # 일반 사용자는 본인이 소속된 약국의 재고 요약을 확인한다.
    elif request.user.is_authenticated and request.user.pharmacy_id:
        medicines = Medicine.objects.filter(pharmacy_id=request.user.pharmacy_id)
        seven_days_ago = timezone.now() - timedelta(days=7)

        context.update(
            {
                "inventory_total": medicines.count(),
                "low_stock_count": medicines.filter(
                    stock__lte=F("minimum_stock"),
                ).count(),
                "normal_stock_count": medicines.filter(
                    stock__gt=F("minimum_stock"),
                ).count(),
                "recently_updated_count": medicines.filter(
                    updated_at__gte=seven_days_ago,
                ).count(),
                "recent_medicines": medicines.order_by("-updated_at")[:5],
            },
        )

    return render(
        request,
        "core/index.html",
        context,
    )


# -------------------- 달력 메모 API: 선택한 날짜의 사용자 메모를 조회해 JSON으로 반환한다. --------------------
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


# -------------------- 달력 메모 API: 달력 메모를 새로 저장하거나 수정하며 빈 내용이면 기존 메모를 삭제한다. --------------------
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


# -------------------- 달력 메모 API: 특정 연·월에 메모가 등록된 날짜 목록을 JSON으로 반환한다. --------------------
@login_required
@require_GET
def calendar_memo_dates(request):
    year_text = request.GET.get("year", "")
    month_text = request.GET.get("month", "")

    try:
        year = int(year_text)
        month = int(month_text)

        if year < 1900 or year > 2100 or month < 1 or month > 12:
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


# -------------------- Health Check: ALB/ASG가 인스턴스 상태를 판정할 때 호출하는 엔드포인트. --------------------
# 용도를 둘로 분리한다. 어느 쪽도 로그인 없이 GET으로 호출되며 데이터를 변경하지 않는다.
#
#   /health/live/  (liveness)  : Django 프로세스가 요청을 받을 수 있는가만 본다.
#                                DB를 조회하지 않으므로 RDS 장애와 무관하게 200이다.
#                                → "인스턴스를 교체하면 나아지는가?"에 답한다.
#                                  (ASG 인스턴스 교체 판정에 적합)
#   /health/ready/ (readiness) : Django + DB 연결까지 본다. SELECT 1 실패 시 503.
#                                → "지금 트래픽을 보내도 되는가?"에 답한다.
#                                  (ALB Target Group 라우팅 판정에 적합)
#
# 이렇게 나누면 RDS 장애 시 ready만 503이 되어 트래픽은 차단되지만,
# live는 200이므로 ASG가 멀쩡한 인스턴스를 교체하는 루프는 생기지 않는다.
#
# /health/ 는 readiness의 별칭이다. PR #78로 먼저 배포된 경로라
# Target Group 설정이 어느 쪽을 가리켜도 동작하도록 유지한다.
@never_cache
@require_GET
def health_live(request):
    # 이 응답이 나갔다는 것 자체가 프로세스 생존의 증거다. 아무것도 조회하지 않는다.
    return JsonResponse({"status": "alive"})


@never_cache
@require_GET
def health_ready(request):
    # DB 연결이 살아 있는지 최소 비용으로 확인한다.
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        # 연결 실패 = 이 인스턴스는 요청을 처리할 수 없는 상태이므로 503을 반환해
        # ALB Target Group에서 제외되도록 한다.
        return JsonResponse({"status": "unhealthy"}, status=503)

    return JsonResponse({"status": "healthy"})
