# ==================================================
# 파일 역할: 회원가입, HIRA 약국 검색, 사용자·약국·마이페이지 기능을 처리하는 뷰 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

import json
import logging
import re
import secrets
import xml.etree.ElementTree as ET

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
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
    CustomPasswordResetForm,
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


logger = logging.getLogger(__name__)


# 비밀번호 재설정 요청에서 아이디와 이메일을 함께 확인한다.
class CustomPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    form_class = CustomPasswordResetForm
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")



# 회원가입 이메일 인증 세션에서 사용하는 키와 제한값이다.
EMAIL_VERIFICATION_SESSION_KEY = "signup_email_verification"
EMAIL_CODE_EXPIRES_SECONDS = 300
EMAIL_RESEND_SECONDS = 60
EMAIL_MAX_ATTEMPTS = 5
EMAIL_VERIFIED_EXPIRES_SECONDS = 1800


def _read_json_request(request):
    """JSON 요청 본문을 사전으로 변환하며 잘못된 요청은 None으로 처리한다."""
    try:
        return json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


@require_POST
def email_verification_send(request):
    """회원가입 이메일로 6자리 인증번호를 발송한다."""
    data = _read_json_request(request)
    if data is None:
        return JsonResponse(
            {"success": False, "message": "요청 형식이 올바르지 않습니다."},
            status=400,
        )

    email = str(data.get("email", "")).strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse(
            {"success": False, "message": "올바른 이메일 주소를 입력해 주세요."},
            status=400,
        )

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse(
            {"success": False, "message": "이미 가입된 이메일입니다."},
            status=400,
        )

    now = int(timezone.now().timestamp())
    current = request.session.get(EMAIL_VERIFICATION_SESSION_KEY, {})
    last_sent_at = int(current.get("sent_at", 0) or 0)
    if current.get("email") == email and now - last_sent_at < EMAIL_RESEND_SECONDS:
        wait_seconds = EMAIL_RESEND_SECONDS - (now - last_sent_at)
        return JsonResponse(
            {
                "success": False,
                "message": f"{wait_seconds}초 후에 인증번호를 다시 요청할 수 있습니다.",
            },
            status=429,
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    subject = "[PharmaFlow] 회원가입 이메일 인증번호"
    message = (
        "PharmaFlow 회원가입 이메일 인증번호입니다.\n\n"
        f"인증번호: {code}\n\n"
        "인증번호는 5분 동안 유효합니다. "
        "본인이 요청하지 않았다면 이 메일을 무시해 주세요."
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("회원가입 인증 메일 발송에 실패했습니다.")
        return JsonResponse(
            {
                "success": False,
                "message": "인증 메일을 발송하지 못했습니다. 잠시 후 다시 시도해 주세요.",
            },
            status=502,
        )

    request.session[EMAIL_VERIFICATION_SESSION_KEY] = {
        "email": email,
        "code_hash": make_password(code),
        "sent_at": now,
        "expires_at": now + EMAIL_CODE_EXPIRES_SECONDS,
        "attempts": 0,
        "verified": False,
        "verified_at": 0,
    }
    request.session.modified = True

    return JsonResponse(
        {
            "success": True,
            "message": "인증번호를 이메일로 발송했습니다. 5분 안에 입력해 주세요.",
            "resend_after": EMAIL_RESEND_SECONDS,
        }
    )


@require_POST
def email_verification_check(request):
    """사용자가 입력한 이메일 인증번호를 확인한다."""
    data = _read_json_request(request)
    if data is None:
        return JsonResponse(
            {"success": False, "message": "요청 형식이 올바르지 않습니다."},
            status=400,
        )

    email = str(data.get("email", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    verification = request.session.get(EMAIL_VERIFICATION_SESSION_KEY, {})
    now = int(timezone.now().timestamp())

    if verification.get("email") != email:
        return JsonResponse(
            {"success": False, "message": "인증번호를 발송한 이메일과 일치하지 않습니다."},
            status=400,
        )

    if now > int(verification.get("expires_at", 0) or 0):
        request.session.pop(EMAIL_VERIFICATION_SESSION_KEY, None)
        return JsonResponse(
            {"success": False, "message": "인증번호가 만료되었습니다. 다시 발송해 주세요."},
            status=400,
        )

    attempts = int(verification.get("attempts", 0) or 0)
    if attempts >= EMAIL_MAX_ATTEMPTS:
        request.session.pop(EMAIL_VERIFICATION_SESSION_KEY, None)
        return JsonResponse(
            {"success": False, "message": "인증 시도 횟수를 초과했습니다. 다시 발송해 주세요."},
            status=429,
        )

    if not re.fullmatch(r"\d{6}", code) or not check_password(
        code,
        verification.get("code_hash", ""),
    ):
        verification["attempts"] = attempts + 1
        request.session[EMAIL_VERIFICATION_SESSION_KEY] = verification
        request.session.modified = True
        return JsonResponse(
            {
                "success": False,
                "message": f"인증번호가 올바르지 않습니다. 남은 횟수: {EMAIL_MAX_ATTEMPTS - attempts - 1}회",
            },
            status=400,
        )

    verification["verified"] = True
    verification["verified_at"] = now
    verification.pop("code_hash", None)
    request.session[EMAIL_VERIFICATION_SESSION_KEY] = verification
    request.session.modified = True

    return JsonResponse(
        {"success": True, "message": "이메일 인증이 완료되었습니다."}
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

            verification = request.session.get(
                EMAIL_VERIFICATION_SESSION_KEY,
                {},
            )
            now = int(timezone.now().timestamp())
            verified_at = int(verification.get("verified_at", 0) or 0)
            email_verified = (
                verification.get("verified") is True
                and verification.get("email") == data["email"].strip().lower()
                and now - verified_at <= EMAIL_VERIFIED_EXPIRES_SECONDS
            )

            if not email_verified:
                form.add_error(
                    "email",
                    "이메일 인증을 완료해 주세요.",
                )
                return render(request, "accounts/signup.html", {"form": form})

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
                            "business_name": data["business_name"],
                            "status": (PharmacyOwnershipRequest.Status.PENDING),
                        },
                    )

            request.session.pop(EMAIL_VERIFICATION_SESSION_KEY, None)

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

    if len(query) < 2:
        return JsonResponse(
            {
                "results": [],
                "error": "검색어를 두 글자 이상 입력하세요.",
            },
            status=400,
        )

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

    except requests.RequestException:
        logger.exception("HIRA 약국 검색 API 요청에 실패했습니다.")
        return JsonResponse(
            {
                "results": [],
                "error": "HIRA 약국 검색 서비스에 연결할 수 없습니다.",
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
            current_user=request.user,
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
            current_user=request.user,
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
    pharmacy_queryset = (
        Pharmacy.objects.prefetch_related("users").all().order_by("pharmacy_name")
    )

    paginator = Paginator(
        pharmacy_queryset,
        10,
    )

    page_number = request.GET.get("page")

    pharmacies = paginator.get_page(
        page_number,
    )

    # 템플릿에서 추가 쿼리 없이 점주 계정 상태를 표시하도록 연결한다.
    for pharmacy in pharmacies.object_list:
        pharmacy.owner_account = next(
            (
                account
                for account in pharmacy.users.all()
                if account.role == User.Role.OWNER and not account.is_superuser
            ),
            None,
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


# -------------------- 약국 관리: 관리자가 선택한 약국 정보를 수정한다. --------------------
@login_required
@superuser_required
def pharmacy_admin_update(request, pk):
    pharmacy = get_object_or_404(
        Pharmacy,
        pk=pk,
    )

    # 관리자 화면에서는 현재 로그인한 관리자 계정이 아니라
    # 해당 약국의 점주 계정을 찾아 이메일 초기값과 저장 대상을 연결한다.
    pharmacy_account_user = (
        User.objects.filter(
            pharmacy=pharmacy,
            role=User.Role.OWNER,
            is_active=True,
        )
        .exclude(email="")
        .order_by("pk")
        .first()
    )

    # 예전 데이터에서 역할이 점주로 저장되지 않았더라도,
    # 해당 약국에 소속된 이메일 보유 계정을 대체 대상으로 사용한다.
    if pharmacy_account_user is None:
        pharmacy_account_user = (
            User.objects.filter(
                pharmacy=pharmacy,
                is_active=True,
            )
            .exclude(email="")
            .order_by("pk")
            .first()
        )

    if request.method == "POST":
        form = PharmacyUpdateForm(
            request.POST,
            instance=pharmacy,
            current_user=pharmacy_account_user,
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
            current_user=pharmacy_account_user,
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


# -------------------- 약국 관리: 관리자가 해당 약국의 점주 계정을 비활성화한다. --------------------
@login_required
@superuser_required
@require_POST
def pharmacy_owner_deactivate(request, pk):
    pharmacy = get_object_or_404(Pharmacy, pk=pk)
    owner = (
        User.objects.filter(
            pharmacy=pharmacy,
            role=User.Role.OWNER,
            is_superuser=False,
            is_active=True,
        )
        .order_by("pk")
        .first()
    )

    if owner is None:
        messages.warning(request, "비활성화할 점주 계정이 없습니다.")
        return redirect("accounts:pharmacy_list")

    with transaction.atomic():
        owner.is_active = False
        owner.is_approved = False
        owner.save(update_fields=["is_active", "is_approved"])

        PharmacyOwnershipRequest.objects.filter(
            user=owner,
            pharmacy=pharmacy,
            status=PharmacyOwnershipRequest.Status.PENDING,
        ).update(
            status=PharmacyOwnershipRequest.Status.REJECTED,
            processed_at=timezone.now(),
        )

        AuditLog.objects.create(
            user=request.user,
            action="점주 계정 비활성화",
            target=f"User #{owner.pk}",
            detail=f"{owner.username} / {pharmacy.pharmacy_name}",
        )

    messages.success(
        request,
        f"{owner.username} 점주 계정을 비활성화했습니다.",
    )
    return redirect("accounts:pharmacy_list")


def _delete_with_protected_relations(instance, deleted_labels=None, seen=None):
    """PROTECT로 연결된 하위 업무 데이터를 먼저 삭제한 뒤 대상 객체를 삭제한다.

    약국 삭제 시 발주, 입출고, 재고처럼 PROTECT 관계로 보존되던 데이터를
    하위 객체부터 순서대로 제거한다. 같은 객체를 반복 처리하지 않도록
    모델 라벨과 기본키 조합을 기록한다.
    """
    if deleted_labels is None:
        deleted_labels = []
    if seen is None:
        seen = set()

    identity = (instance._meta.label_lower, instance.pk)
    if identity in seen:
        return deleted_labels
    seen.add(identity)

    try:
        verbose_name = str(instance._meta.verbose_name)
        instance.delete()
        deleted_labels.append(verbose_name)
        return deleted_labels
    except ProtectedError as exc:
        # 보호된 객체를 먼저 제거한 뒤 원래 객체 삭제를 다시 시도한다.
        protected_objects = list(exc.protected_objects)
        if not protected_objects:
            raise

        for protected_object in protected_objects:
            _delete_with_protected_relations(
                protected_object,
                deleted_labels=deleted_labels,
                seen=seen,
            )

        verbose_name = str(instance._meta.verbose_name)
        instance.delete()
        deleted_labels.append(verbose_name)
        return deleted_labels


# -------------------- 약국 관리: 관리자가 선택한 약국을 삭제하되 소속 사용자가 있으면 삭제를 막는다. --------------------
@login_required
@superuser_required
def pharmacy_delete(request, pk):
    pharmacy = get_object_or_404(Pharmacy, pk=pk)

    if request.method == "POST":
        active_owner_exists = pharmacy.users.filter(
            role=User.Role.OWNER,
            is_active=True,
            is_superuser=False,
        ).exists()

        if active_owner_exists:
            messages.error(
                request,
                "활성 점주 계정이 있어 약국을 삭제할 수 없습니다. "
                "먼저 점주 해지를 진행해 주세요.",
            )
            return redirect("accounts:pharmacy_list")

        pharmacy_pk = pharmacy.pk
        pharmacy_name = pharmacy.pharmacy_name

        try:
            with transaction.atomic():
                # 사용자 계정 자체는 보존하되 로그인과 승인을 차단하고
                # 삭제 대상 약국과의 소속 관계만 해제한다.
                pharmacy.users.filter(is_superuser=False).update(
                    pharmacy=None,
                    is_active=False,
                    is_approved=False,
                )

                # 점주 권한 신청 기록도 약국 삭제 대상에 포함한다.
                # 과거 승인·거절 기록까지 FK로 약국을 보호할 수 있으므로
                # 해당 약국의 신청 기록을 명시적으로 먼저 삭제한다.
                PharmacyOwnershipRequest.objects.filter(
                    pharmacy=pharmacy,
                ).delete()

                # 발주, 입출고, 재고 등 PROTECT 관계로 연결된 업무 데이터를
                # 하위 객체부터 재귀적으로 삭제한 다음 약국을 삭제한다.
                deleted_labels = _delete_with_protected_relations(pharmacy)

                AuditLog.objects.create(
                    user=request.user,
                    action="약국 삭제",
                    target=f"Pharmacy #{pharmacy_pk}",
                    detail=(
                        f"{pharmacy_name} 및 연결 데이터 삭제: "
                        + ", ".join(sorted(set(deleted_labels)))
                    ),
                )

            messages.success(
                request,
                (
                    f"{pharmacy_name} 약국과 연결된 재고·입출고·"
                    "발주 데이터를 모두 삭제했습니다."
                ),
            )

        except Exception:
            logger.exception(
                "약국 및 연결 데이터 삭제에 실패했습니다. pharmacy_id=%s",
                pharmacy_pk,
            )
            messages.error(
                request,
                (
                    "약국과 연결 데이터를 삭제하지 못했습니다. "
                    "서버 로그에서 남아 있는 연결 관계를 확인해 주세요."
                ),
            )

        return redirect("accounts:pharmacy_list")

    return render(
        request,
        "accounts/pharmacy_confirm_delete.html",
        {
            "pharmacy": pharmacy,
            "active_users": pharmacy.users.filter(
                is_active=True,
                is_superuser=False,
            ).order_by("role", "username"),
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
            business_name = ownership_request.business_name.strip()

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
            pharmacy.business_name = business_name

            if not pharmacy.owner_name:
                pharmacy.owner_name = user.name

            pharmacy.save(
                update_fields=[
                    "business_number",
                    "business_name",
                    "owner_name",
                    "updated_at",
                ]
            )
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
