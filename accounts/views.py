# ==================================================
# 파일 역할: 회원가입, HIRA 약국 검색, 사용자·약국·마이페이지 기능을 처리하는 뷰 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

import xml.etree.ElementTree as ET

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

# AuditLog: "누가 언제 무엇을 했는지" 기록을 남기는 표 (consultations 앱에 정의됨)
from consultations.models import AuditLog

from .decorators import (
    owner_required,
    staff_manager_required,
    superuser_required,
)
from .forms import (
    MyPageUpdateForm,
    PasswordConfirmForm,
    PharmacyUpdateForm,
    SignUpForm,
    StaffCreateForm,
    StaffUpdateForm,
)
from .models import (
    Pharmacy,
    PharmacyOwnershipRequest,
    User,
)


# -------------------- 회원가입: 회원가입 요청을 처리하고 선택한 약국 및 점주 권한 신청 정보를 저장한다. --------------------
def signup(request):
    if request.user.is_authenticated:
        return redirect("core:index")

    if request.method == "POST":
        form = SignUpForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            data = form.cleaned_data

            selected_pharmacies = request.session.get("pharmacy_search_results", {})
            selected = selected_pharmacies.get(data["pharmacy_external_id"])

            if not selected:
                form.add_error(
                    None,
                    "약국 검색 결과를 다시 선택해 주세요.",
                )
                return render(request, "accounts/signup.html", {"form": form})

            expected_values = {
                "pharmacy_name": selected.get("name", ""),
                "pharmacy_address": selected.get("address", ""),
                "pharmacy_phone": selected.get("phone", ""),
            }
            if any(
                data.get(key, "").strip() != value.strip()
                for key, value in expected_values.items()
            ):
                form.add_error(
                    None,
                    "선택한 약국 정보가 변경되었습니다. 다시 검색해 선택해 주세요.",
                )
                return render(request, "accounts/signup.html", {"form": form})

            with transaction.atomic():
                pharmacy, created = Pharmacy.objects.get_or_create(
                    external_place_id=data["pharmacy_external_id"],
                    defaults={
                        "pharmacy_name": data["pharmacy_name"],
                        "address": data["pharmacy_address"],
                        "phone": data.get("pharmacy_phone", ""),
                        "latitude": (data.get("pharmacy_latitude") or None),
                        "longitude": (data.get("pharmacy_longitude") or None),
                        "data_source": Pharmacy.DataSource.HIRA,
                        "is_verified": True,
                    },
                )

                user = form.save(commit=False)
                user.pharmacy = pharmacy
                user.role = data["requested_role"]
                user.is_approved = False
                user.save()

                if user.role == User.Role.OWNER:
                    PharmacyOwnershipRequest.objects.update_or_create(
                        user=user,
                        pharmacy=pharmacy,
                        defaults={
                            "business_number": data["business_number"],
                            "status": (PharmacyOwnershipRequest.Status.PENDING),
                        },
                    )

            if user.role == User.Role.OWNER:
                messages.success(
                    request,
                    (
                        "회원가입과 점주 권한 신청이 완료되었습니다. "
                        "시스템 관리자 승인 후 로그인할 수 있습니다."
                    ),
                )
            else:
                messages.success(
                    request,
                    (
                        "회원가입이 완료되었습니다. "
                        "소속 약국 점주의 승인 후 로그인할 수 있습니다."
                    ),
                )

            return redirect("login")

    else:
        form = SignUpForm()

    return render(
        request,
        "accounts/signup.html",
        {
            "form": form,
        },
    )


# HIRA XML 항목에서 후보 태그 중 실제 값이 있는 텍스트를 찾아 반환한다.
def get_xml_text(item, *names):
    for name in names:
        value = item.findtext(name)

        if value:
            return value.strip()

    return ""


# -------------------- HIRA 약국 검색: 검색어를 HIRA 약국정보서비스에 전달하고 화면에서 사용할 JSON 결과로 변환한다. --------------------
@require_GET
def pharmacy_search(request):
    query = request.GET.get("q", "").strip()

    now_timestamp = timezone.now().timestamp()
    last_search = request.session.get("pharmacy_search_last_at", 0)
    if now_timestamp - last_search < 1.0:
        return JsonResponse(
            {
                "results": [],
                "error": "검색 요청이 너무 빠릅니다. 잠시 후 다시 시도하세요.",
            },
            status=429,
        )
    request.session["pharmacy_search_last_at"] = now_timestamp

    if len(query) < 2:
        return JsonResponse(
            {
                "results": [],
                "error": "검색어를 두 글자 이상 입력하세요.",
            },
            status=400,
        )

    if not settings.HIRA_SERVICE_KEY:
        return JsonResponse(
            {
                "results": [],
                "error": "HIRA API 인증키가 설정되지 않았습니다.",
            },
            status=500,
        )

    try:
        response = requests.get(
            (
                "https://apis.data.go.kr/"
                "B551182/pharmacyInfoService/"
                "getParmacyBasisList"
            ),
            params={
                "ServiceKey": settings.HIRA_SERVICE_KEY,
                "pageNo": 1,
                "numOfRows": 20,
                "yadmNm": query,
            },
            timeout=10,
        )

        response.raise_for_status()

    except requests.Timeout:
        return JsonResponse(
            {
                "results": [],
                "error": "약국 검색 요청 시간이 초과되었습니다.",
            },
            status=504,
        )

        return JsonResponse(
            {
                "results": [],
                "error": str(e),
            },
            status=502,
        )

    try:
        root = ET.fromstring(response.content)

    except ET.ParseError:
        return JsonResponse(
            {
                "results": [],
                "error": "약국 검색 응답을 해석할 수 없습니다.",
            },
            status=502,
        )

    result_code = root.findtext(
        ".//resultCode",
        default="",
    )

    if result_code not in ("00", "0"):
        result_message = root.findtext(
            ".//resultMsg",
            default="약국 검색에 실패했습니다.",
        )

        return JsonResponse(
            {
                "results": [],
                "error": result_message,
            },
            status=502,
        )

    results = []

    for item in root.findall(".//item"):
        external_id = get_xml_text(
            item,
            "ykiho",
            "YKIHO",
        )

        pharmacy_name = get_xml_text(
            item,
            "yadmNm",
            "YADMNM",
        )

        address = get_xml_text(
            item,
            "addr",
            "ADDR",
        )

        phone = get_xml_text(
            item,
            "telno",
            "TELNO",
        )

        longitude = get_xml_text(
            item,
            "XPos",
            "xPos",
            "xpos",
        )

        latitude = get_xml_text(
            item,
            "YPos",
            "yPos",
            "ypos",
        )

        if not external_id or not pharmacy_name:
            continue

        results.append(
            {
                "external_id": external_id,
                "name": pharmacy_name,
                "address": address,
                "phone": phone,
                "longitude": longitude,
                "latitude": latitude,
            }
        )

    request.session["pharmacy_search_results"] = {
        item["external_id"]: item for item in results
    }
    request.session.modified = True

    return JsonResponse(
        {
            "results": results,
        }
    )


# 사용자에게 소속 약국이 있으면 해당 약국 객체를 반환한다.
def _get_user_pharmacy(user):
    if not user.pharmacy_id:
        return None

    return user.pharmacy


# 현재 사용자가 지정한 약국 정보를 수정할 권한이 있는지 확인한다.
def _can_edit_pharmacy(user, pharmacy):
    if user.is_superuser:
        return True

    return (
        user.is_authenticated
        and user.is_approved
        and user.role == User.Role.OWNER
        and user.pharmacy_id == pharmacy.pk
    )


# -------------------- 약국 관리: 현재 사용자의 소속 약국 상세 정보를 보여준다. --------------------
@login_required
def pharmacy_detail(request):
    pharmacy = _get_user_pharmacy(request.user)

    if pharmacy is None:
        return render(
            request,
            "accounts/pharmacy_detail.html",
            {
                "pharmacy": None,
                "can_edit": False,
            },
        )

    return render(
        request,
        "accounts/pharmacy_detail.html",
        {
            "pharmacy": pharmacy,
            "can_edit": _can_edit_pharmacy(
                request.user,
                pharmacy,
            ),
        },
    )


# -------------------- 약국 관리: 승인된 점주 또는 관리자가 소속 약국 정보를 수정한다. --------------------
@login_required
def pharmacy_update(request):
    pharmacy = _get_user_pharmacy(request.user)

    if pharmacy is None:
        messages.error(
            request,
            "소속 약국 정보가 없습니다.",
        )

        return redirect("accounts:pharmacy_detail")

    if not _can_edit_pharmacy(
        request.user,
        pharmacy,
    ):
        messages.error(
            request,
            "약국 정보를 수정할 권한이 없습니다.",
        )

        return redirect("accounts:pharmacy_detail")

    if request.method == "POST":
        form = PharmacyUpdateForm(
            request.POST,
            instance=pharmacy,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "약국 정보가 수정되었습니다.",
            )

            return redirect("accounts:pharmacy_detail")

    else:
        form = PharmacyUpdateForm(
            instance=pharmacy,
        )

    return render(
        request,
        "accounts/pharmacy_form.html",
        {
            "form": form,
            "pharmacy": pharmacy,
            "title": "약국 정보 수정",
            "submit_text": "저장",
            "cancel_url_name": "accounts:pharmacy_detail",
        },
    )


# -------------------- 약국 관리: 관리자에게 전체 약국 목록을 페이지 단위로 보여준다. --------------------
@login_required
@superuser_required
def pharmacy_list(request):
    pharmacy_queryset = Pharmacy.objects.all().order_by("pharmacy_name")

    paginator = Paginator(
        pharmacy_queryset,
        10,
    )

    page_number = request.GET.get("page")

    pharmacies = paginator.get_page(
        page_number,
    )

    page_block_size = 5

    current_block = (pharmacies.number - 1) // page_block_size

    block_start = current_block * page_block_size + 1

    block_end = min(
        block_start + page_block_size - 1,
        paginator.num_pages,
    )

    custom_page_range = range(
        block_start,
        block_end + 1,
    )

    has_prev_block = block_start > 1
    has_next_block = block_end < paginator.num_pages

    prev_block_page = max(
        1,
        block_start - page_block_size,
    )

    next_block_page = min(
        paginator.num_pages,
        block_end + 1,
    )

    return render(
        request,
        "accounts/pharmacy_list.html",
        {
            "pharmacies": pharmacies,
            "custom_page_range": custom_page_range,
            "has_prev_block": has_prev_block,
            "has_next_block": has_next_block,
            "prev_block_page": prev_block_page,
            "next_block_page": next_block_page,
            "last_page": paginator.num_pages,
        },
    )


# -------------------- 약국 관리: 관리자가 약국 정보를 직접 등록한다. --------------------
@login_required
@superuser_required
def pharmacy_create(request):
    if request.method == "POST":
        form = PharmacyUpdateForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "약국이 등록되었습니다.",
            )

            return redirect("accounts:pharmacy_list")

    else:
        form = PharmacyUpdateForm()

    return render(
        request,
        "accounts/pharmacy_form.html",
        {
            "form": form,
            "title": "약국 등록",
            "submit_text": "등록",
            "cancel_url_name": "accounts:pharmacy_list",
        },
    )


# -------------------- 약국 관리: 관리자가 선택한 약국 정보를 수정한다. --------------------
@login_required
@superuser_required
def pharmacy_admin_update(request, pk):
    pharmacy = get_object_or_404(
        Pharmacy,
        pk=pk,
    )

    if request.method == "POST":
        form = PharmacyUpdateForm(
            request.POST,
            instance=pharmacy,
        )

        if form.is_valid():
            form.save()

            # 누가 어떤 약국 정보를 수정했는지 기록
            AuditLog.objects.create(
                user=request.user,
                action="약국 정보 수정",
                target=f"Pharmacy #{pharmacy.pk}",
                detail=pharmacy.pharmacy_name,
            )

            messages.success(
                request,
                f"{pharmacy.pharmacy_name} 정보를 수정했습니다.",
            )

            return redirect("accounts:pharmacy_list")

    else:
        form = PharmacyUpdateForm(
            instance=pharmacy,
        )

    return render(
        request,
        "accounts/pharmacy_form.html",
        {
            "form": form,
            "pharmacy": pharmacy,
            "title": "약국 정보 수정",
            "submit_text": "저장",
            "cancel_url_name": "accounts:pharmacy_list",
        },
    )


# -------------------- 약국 관리: 관리자가 선택한 약국을 삭제하되 소속 사용자가 있으면 삭제를 막는다. --------------------
@login_required
@superuser_required
def pharmacy_delete(request, pk):
    pharmacy = get_object_or_404(
        Pharmacy,
        pk=pk,
    )

    if request.method == "POST":
        # 삭제 후에는 pharmacy 객체를 못 쓰므로 기록에 쓸 이름/번호를 미리 저장해둠
        pharmacy_pk = pharmacy.pk
        pharmacy_name = pharmacy.pharmacy_name

        try:
            pharmacy.delete()

            # 누가 어떤 약국을 삭제했는지 기록
            AuditLog.objects.create(
                user=request.user,
                action="약국 삭제",
                target=f"Pharmacy #{pharmacy_pk}",
                detail=pharmacy_name,
            )

            messages.success(
                request,
                "약국이 삭제되었습니다.",
            )

        except ProtectedError:
            messages.error(
                request,
                "소속 사용자가 존재하는 약국은 삭제할 수 없습니다.",
            )

        return redirect("accounts:pharmacy_list")

    return render(
        request,
        "accounts/pharmacy_confirm_delete.html",
        {
            "pharmacy": pharmacy,
        },
    )


# -------------------- 소속 사용자 관리: 소속 약국의 약사와 직원 계정을 페이지 단위로 보여준다. --------------------
@login_required
@staff_manager_required
def user_list(request):
    user_queryset = (
        User.objects.filter(
            pharmacy=request.user.pharmacy,
            role__in=[
                User.Role.PHARMACIST,
                User.Role.STAFF,
            ],
            is_superuser=False,
        )
        .exclude(pk=request.user.pk)
        .order_by(
            "is_approved",
            "role",
            "name",
            "username",
        )
    )

    paginator = Paginator(
        user_queryset,
        10,
    )

    page_number = request.GET.get("page")

    users = paginator.get_page(
        page_number,
    )

    page_block_size = 5

    current_block = (users.number - 1) // page_block_size

    block_start = current_block * page_block_size + 1

    block_end = min(
        block_start + page_block_size - 1,
        paginator.num_pages,
    )

    custom_page_range = range(
        block_start,
        block_end + 1,
    )

    has_prev_block = block_start > 1
    has_next_block = block_end < paginator.num_pages

    prev_block_page = max(
        1,
        block_start - page_block_size,
    )

    next_block_page = min(
        paginator.num_pages,
        block_end + 1,
    )

    return render(
        request,
        "accounts/user_list.html",
        {
            "users": users,
            "custom_page_range": custom_page_range,
            "has_prev_block": has_prev_block,
            "has_next_block": has_next_block,
            "prev_block_page": prev_block_page,
            "next_block_page": next_block_page,
            "last_page": paginator.num_pages,
        },
    )


# -------------------- 소속 사용자 관리: 관리 권한자가 소속 약국의 직원 계정을 직접 생성한다. --------------------
@login_required
@staff_manager_required
def user_create(request):
    if request.method == "POST":
        form = StaffCreateForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            staff = form.save(commit=False)

            staff.pharmacy = request.user.pharmacy
            staff.role = User.Role.STAFF
            staff.is_approved = True

            staff.save()

            messages.success(
                request,
                f"{staff.name} 직원을 추가했습니다.",
            )

            return redirect("accounts:user_list")

    else:
        form = StaffCreateForm()

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "title": "직원 추가",
            "submit_text": "추가",
        },
    )


# -------------------- 소속 사용자 관리: 관리 권한자가 소속 사용자 정보를 수정한다. --------------------
@login_required
@staff_manager_required
def user_update(request, pk):
    staff = get_object_or_404(
        User,
        pk=pk,
        pharmacy=request.user.pharmacy,
        role__in=[
            User.Role.PHARMACIST,
            User.Role.STAFF,
        ],
        is_superuser=False,
    )

    if request.method == "POST":
        form = StaffUpdateForm(
            request.POST,
            request.FILES,
            instance=staff,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"{staff.name} 사용자 정보를 수정했습니다.",
            )

            return redirect("accounts:user_list")

    else:
        form = StaffUpdateForm(
            instance=staff,
        )

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "staff": staff,
            "title": "사용자 정보 수정",
            "submit_text": "저장",
        },
    )


# -------------------- 소속 사용자 관리: 사용자 기록을 보존하기 위해 계정을 삭제하지 않고 비활성화한다. --------------------
@login_required
@staff_manager_required
@require_POST
def user_delete(request, pk):
    staff = get_object_or_404(
        User,
        pk=pk,
        pharmacy=request.user.pharmacy,
        role__in=[
            User.Role.PHARMACIST,
            User.Role.STAFF,
        ],
        is_superuser=False,
    )

    staff_name = staff.name
    staff.is_active = False
    staff.is_approved = False
    staff.save(update_fields=["is_active", "is_approved"])

    # 누가 어떤 사용자 계정을 비활성화했는지 기록
    AuditLog.objects.create(
        user=request.user,
        action="사용자 계정 비활성화",
        target=f"User #{staff.pk}",
        detail=staff_name,
    )

    messages.success(
        request,
        f"{staff_name} 사용자 계정을 비활성화했습니다.",
    )

    return redirect("accounts:user_list")


# -------------------- 소속 사용자 관리: 점주가 가입 대기 중인 소속 사용자를 승인한다. --------------------
@login_required
@owner_required
@require_POST
def user_approve(request, pk):
    target_user = get_object_or_404(
        User,
        pk=pk,
        pharmacy=request.user.pharmacy,
        role__in=[
            User.Role.PHARMACIST,
            User.Role.STAFF,
        ],
        is_superuser=False,
    )

    target_user.is_approved = True
    target_user.save(update_fields=["is_approved"])

    # 누가 어떤 사용자를 승인했는지 기록
    AuditLog.objects.create(
        user=request.user,
        action="사용자 승인",
        target=f"User #{target_user.pk}",
        detail=target_user.name,
    )

    messages.success(
        request,
        f"{target_user.name} 사용자를 승인했습니다.",
    )

    return redirect("accounts:user_list")


# -------------------- 소속 사용자 관리: 점주가 소속 사용자의 승인 상태를 취소한다. --------------------
@login_required
@owner_required
@require_POST
def user_revoke(request, pk):
    target_user = get_object_or_404(
        User,
        pk=pk,
        pharmacy=request.user.pharmacy,
        role__in=[
            User.Role.PHARMACIST,
            User.Role.STAFF,
        ],
        is_superuser=False,
    )

    target_user.is_approved = False
    target_user.save(update_fields=["is_approved"])

    # 누가 어떤 사용자의 승인을 취소했는지 기록
    AuditLog.objects.create(
        user=request.user,
        action="사용자 승인 취소",
        target=f"User #{target_user.pk}",
        detail=target_user.name,
    )

    messages.success(
        request,
        f"{target_user.name} 사용자의 승인을 취소했습니다.",
    )

    return redirect("accounts:user_list")


# -------------------- 점주 권한 신청 관리: 관리자에게 처리 대기 중인 점주 권한 신청 목록을 보여준다. --------------------
@login_required
@superuser_required
def ownership_request_list(request):
    ownership_request_queryset = (
        PharmacyOwnershipRequest.objects.select_related(
            "user",
            "pharmacy",
        )
        .filter(
            status=PharmacyOwnershipRequest.Status.PENDING,
        )
        .order_by(
            "-created_at",
        )
    )

    paginator = Paginator(
        ownership_request_queryset,
        10,
    )

    page_number = request.GET.get("page")

    ownership_requests = paginator.get_page(
        page_number,
    )

    page_block_size = 5

    current_block = (ownership_requests.number - 1) // page_block_size

    block_start = current_block * page_block_size + 1

    block_end = min(
        block_start + page_block_size - 1,
        paginator.num_pages,
    )

    custom_page_range = range(
        block_start,
        block_end + 1,
    )

    has_prev_block = block_start > 1
    has_next_block = block_end < paginator.num_pages

    prev_block_page = max(
        1,
        block_start - page_block_size,
    )

    next_block_page = min(
        paginator.num_pages,
        block_end + 1,
    )

    return render(
        request,
        "accounts/ownership_request_list.html",
        {
            "ownership_requests": ownership_requests,
            "custom_page_range": custom_page_range,
            "has_prev_block": has_prev_block,
            "has_next_block": has_next_block,
            "prev_block_page": prev_block_page,
            "next_block_page": next_block_page,
            "last_page": paginator.num_pages,
        },
    )


# -------------------- 점주 권한 신청 관리: 점주 권한 신청을 승인하고 사용자와 약국 정보를 함께 갱신한다. --------------------
@login_required
@superuser_required
@require_POST
def ownership_request_approve(request, pk):
    try:
        with transaction.atomic():
            ownership_request = get_object_or_404(
                PharmacyOwnershipRequest.objects.select_for_update().select_related(
                    "user", "pharmacy"
                ),
                pk=pk,
                status=PharmacyOwnershipRequest.Status.PENDING,
            )
            user = ownership_request.user
            pharmacy = ownership_request.pharmacy
            business_number = ownership_request.business_number.strip()

            duplicate_pharmacy = (
                Pharmacy.objects.select_for_update()
                .filter(business_number=business_number)
                .exclude(pk=pharmacy.pk)
                .first()
            )
            if duplicate_pharmacy:
                messages.error(
                    request,
                    f"사업자등록번호 {business_number}는 이미 {duplicate_pharmacy.pharmacy_name}에 등록되어 있습니다.",
                )
                return redirect("accounts:ownership_request_list")

            ownership_request.status = PharmacyOwnershipRequest.Status.APPROVED
            ownership_request.processed_at = timezone.now()
            ownership_request.save(update_fields=["status", "processed_at"])

            user.pharmacy = pharmacy
            user.role = User.Role.OWNER
            user.is_approved = True
            user.save(update_fields=["pharmacy", "role", "is_approved"])

            pharmacy.business_number = business_number
            if not pharmacy.owner_name:
                pharmacy.owner_name = user.name
            pharmacy.save(update_fields=["business_number", "owner_name", "updated_at"])
    except IntegrityError:
        messages.error(request, "중복된 사업자등록번호로 승인할 수 없습니다.")
        return redirect("accounts:ownership_request_list")

    # 누가 어떤 사용자의 점주 권한 요청을 승인했는지 기록
    AuditLog.objects.create(
        user=request.user,
        action="점주 권한 승인",
        target=f"User #{user.pk}",
        detail=f"{user.name} → {pharmacy.pharmacy_name}",
    )

    messages.success(request, f"{user.name} 사용자의 점주 권한을 승인했습니다.")
    return redirect("accounts:ownership_request_list")


# -------------------- 점주 권한 신청 관리: 점주 권한 신청을 거절하고 처리 시각을 기록한다. --------------------
@login_required
@superuser_required
@require_POST
def ownership_request_reject(request, pk):
    with transaction.atomic():
        ownership_request = get_object_or_404(
            PharmacyOwnershipRequest.objects.select_for_update().select_related(
                "user", "pharmacy"
            ),
            pk=pk,
            status=PharmacyOwnershipRequest.Status.PENDING,
        )
        ownership_request.status = PharmacyOwnershipRequest.Status.REJECTED
        ownership_request.processed_at = timezone.now()
        ownership_request.save(update_fields=["status", "processed_at"])

        user = ownership_request.user
        user.is_approved = False
        user.save(update_fields=["is_approved"])

    # 누가 어떤 사용자의 점주 권한 요청을 거절했는지 기록
    AuditLog.objects.create(
        user=request.user,
        action="점주 권한 거절",
        target=f"User #{user.pk}",
        detail=user.name,
    )

    messages.success(request, f"{user.name} 사용자의 점주 권한 신청을 거절했습니다.")
    return redirect("accounts:ownership_request_list")


# -------------------- 마이페이지: 현재 비밀번호를 확인한 뒤 사용자 계정을 비활성화하고 로그아웃한다. --------------------
@login_required
@require_POST
def my_page_deactivate(request):
    if request.user.is_superuser:
        messages.error(
            request,
            "시스템 관리자 계정은 마이페이지에서 해지할 수 없습니다.",
        )

        return redirect("accounts:my_page")

    password = request.POST.get(
        "password",
        "",
    )

    if not request.user.check_password(password):
        password_form = PasswordConfirmForm(
            user=request.user,
        )

        messages.error(
            request,
            "현재 비밀번호가 올바르지 않습니다.",
        )

        return render(
            request,
            "accounts/my_page.html",
            {
                "account": request.user,
                "password_form": password_form,
                "open_deactivate_modal": True,
            },
            status=400,
        )

    account = request.user

    with transaction.atomic():
        account.is_active = False
        account.is_approved = False

        account.save(
            update_fields=[
                "is_active",
                "is_approved",
            ]
        )
        PharmacyOwnershipRequest.objects.filter(
            user=account,
            status=PharmacyOwnershipRequest.Status.PENDING,
        ).update(
            status=PharmacyOwnershipRequest.Status.REJECTED,
            processed_at=timezone.now(),
        )

    logout(request)

    messages.success(
        request,
        "계정 해지가 완료되었습니다.",
    )

    return redirect("login")


# -------------------- 마이페이지: 현재 사용자의 프로필과 승인 상태를 보여준다. --------------------
@login_required
def my_page(request):
    password_form = PasswordConfirmForm(
        user=request.user,
    )

    return render(
        request,
        "accounts/my_page.html",
        {
            "account": request.user,
            "password_form": password_form,
        },
    )


# -------------------- 마이페이지: 내 정보 수정 전 현재 비밀번호를 확인하고 세션에 인증 시각을 저장한다. --------------------
@login_required
@require_POST
def my_page_verify_password(request):
    form = PasswordConfirmForm(
        request.POST,
        user=request.user,
    )

    if form.is_valid():
        request.session["mypage_verified"] = True
        request.session["mypage_verified_at"] = timezone.now().timestamp()

        return redirect("accounts:my_page_update")

    return render(
        request,
        "accounts/my_page.html",
        {
            "account": request.user,
            "password_form": form,
            "open_password_modal": True,
        },
    )


# -------------------- 마이페이지: 최근 비밀번호 확인을 통과한 사용자의 개인 정보를 수정한다. --------------------
@login_required
def my_page_update(request):
    verified = request.session.get(
        "mypage_verified",
        False,
    )

    verified_at = request.session.get(
        "mypage_verified_at",
        0,
    )

    elapsed_seconds = timezone.now().timestamp() - verified_at

    if not verified or elapsed_seconds > 300:
        request.session.pop(
            "mypage_verified",
            None,
        )
        request.session.pop(
            "mypage_verified_at",
            None,
        )

        messages.warning(
            request,
            "내 정보 수정 전에 비밀번호를 확인해 주세요.",
        )

        return redirect("accounts:my_page")

    account = request.user

    if request.method == "POST":
        form = MyPageUpdateForm(
            request.POST,
            request.FILES,
            instance=account,
        )

        if form.is_valid():
            password_changed = bool(form.cleaned_data.get("new_password1"))

            account = form.save()

            if password_changed:
                update_session_auth_hash(
                    request,
                    account,
                )

            request.session.pop(
                "mypage_verified",
                None,
            )
            request.session.pop(
                "mypage_verified_at",
                None,
            )

            messages.success(
                request,
                "내 정보가 수정되었습니다.",
            )

            return redirect("accounts:my_page")

    else:
        form = MyPageUpdateForm(
            instance=account,
        )

    return render(
        request,
        "accounts/my_page_form.html",
        {
            "form": form,
            "account": account,
        },
    )
