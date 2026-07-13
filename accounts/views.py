import xml.etree.ElementTree as ET

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .decorators import owner_required, superuser_required
from .forms import PharmacyUpdateForm, SignUpForm
from .models import Pharmacy, PharmacyOwnershipRequest, User


def signup(request):
    if request.user.is_authenticated:
        return redirect("core:index")

    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data

            with transaction.atomic():
                pharmacy, created = Pharmacy.objects.update_or_create(
                    external_place_id=data["pharmacy_external_id"],
                    defaults={
                        "pharmacy_name": data["pharmacy_name"],
                        "address": data["pharmacy_address"],
                        "phone": data.get("pharmacy_phone", ""),
                        "latitude": (
                            data.get("pharmacy_latitude") or None
                        ),
                        "longitude": (
                            data.get("pharmacy_longitude") or None
                        ),
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
                            "status": (
                                PharmacyOwnershipRequest.Status.PENDING
                            ),
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

            return redirect("accounts:login")

    else:
        form = SignUpForm()

    return render(
        request,
        "accounts/signup.html",
        {
            "form": form,
        },
    )


def get_xml_text(item, *names):
    for name in names:
        value = item.findtext(name)

        if value:
            return value.strip()

    return ""


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
                "http://apis.data.go.kr/"
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

    return JsonResponse(
        {
            "results": results,
        }
    )


def _get_user_pharmacy(user):
    if not user.pharmacy_id:
        return None

    return user.pharmacy


def _can_edit_pharmacy(user, pharmacy):
    def _can_edit_pharmacy(user, pharmacy):
        if user.is_superuser or user.is_staff:
            return True

    return (
        user.is_authenticated
        and user.is_approved
        and user.role == User.Role.OWNER
        and user.pharmacy_id == pharmacy.pk
    )


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


@login_required
def pharmacy_update(request):
    pharmacy = _get_user_pharmacy(request.user)

    if pharmacy is None:
        messages.error(
            request,
            "소속 약국 정보가 없습니다.",
        )

        return redirect(
            "accounts:pharmacy_detail"
        )

    if not _can_edit_pharmacy(
        request.user,
        pharmacy,
    ):
        messages.error(
            request,
            "약국 정보를 수정할 권한이 없습니다."
        )
        
        return redirect(
            "accounts:pharmacy_detail"
        )

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

            return redirect(
                "accounts:pharmacy_detail"
            )

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


@login_required
@superuser_required
def pharmacy_list(request):

    pharmacies = (
        Pharmacy.objects
        .all()
        .order_by("pharmacy_name")
    )

    return render(
        request,
        "accounts/pharmacy_list.html",
        {
            "pharmacies": pharmacies,
        },
    )


@login_required
@superuser_required
def pharmacy_create(request):
    if request.method == "POST":
        form = PharmacyUpdateForm(
            request.POST
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "약국이 등록되었습니다.",
            )

            return redirect(
                "accounts:pharmacy_list"
            )

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


@login_required
@superuser_required
def pharmacy_delete(request, pk):
    pharmacy = get_object_or_404(
        Pharmacy,
        pk=pk,
    )

    if request.method == "POST":
        try:
            pharmacy.delete()

            messages.success(
                request,
                "약국이 삭제되었습니다.",
            )

        except ProtectedError:
            messages.error(
                request,
                "소속 사용자가 존재하는 약국은 삭제할 수 없습니다.",
            )

        return redirect(
            "accounts:pharmacy_list"
        )

    return render(
        request,
        "accounts/pharmacy_confirm_delete.html",
        {
            "pharmacy": pharmacy,
        },
    )


@login_required
@owner_required
def user_list(request):
    users = (
        User.objects.filter(
            pharmacy=request.user.pharmacy,
        )
        .exclude(
            pk=request.user.pk
        )
        .exclude(
            is_superuser=True
        )
        .order_by(
            "is_approved",
            "name",
            "username",
        )
    )

    return render(
        request,
        "accounts/user_list.html",
        {
            "users": users,
        },
    )


@login_required
@owner_required
@require_POST
def user_approve(request, pk):
    target_user = get_object_or_404(
        User,
        pk=pk,
        pharmacy=request.user.pharmacy,
        is_superuser=False,
    )

    if target_user.role == User.Role.OWNER:
        messages.error(
            request,
            "점주 계정은 이 화면에서 승인할 수 없습니다.",
        )

        return redirect(
            "accounts:user_list"
        )

    target_user.is_approved = True

    target_user.save(
        update_fields=[
            "is_approved",
        ]
    )

    messages.success(
        request,
        f"{target_user.name} 사용자를 승인했습니다.",
    )

    return redirect(
        "accounts:user_list"
    )


@login_required
@owner_required
@require_POST
def user_revoke(request, pk):
    target_user = get_object_or_404(
        User,
        pk=pk,
        pharmacy=request.user.pharmacy,
        is_superuser=False,
    )

    if target_user.role == User.Role.OWNER:
        messages.error(
            request,
            "점주 계정은 이 화면에서 처리할 수 없습니다.",
        )

        return redirect(
            "accounts:user_list"
        )

    target_user.is_approved = False

    target_user.save(
        update_fields=[
            "is_approved",
        ]
    )

    messages.success(
        request,
        f"{target_user.name} 사용자의 승인을 취소했습니다.",
    )

    return redirect(
        "accounts:user_list"
    )
