import xml.etree.ElementTree as ET

import requests # pip install requests 필요

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from django.db import IntegrityError, transaction

from .decorators import owner_required, staff_manager_required, superuser_required
from .models import Pharmacy, PharmacyOwnershipRequest, User
from .forms import (
    PharmacyUpdateForm,
    SignUpForm,
    StaffCreateForm,
    StaffUpdateForm,
)


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
@staff_manager_required
def user_list(request):
    users = (
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

    return render(
        request,
        "accounts/user_list.html",
        {
            "users": users,
        },
    )


@login_required
@staff_manager_required
def user_create(request):
    if request.method == "POST":
        form = StaffCreateForm(request.POST)

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

            return redirect(
                "accounts:user_list"
            )

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


@login_required
@staff_manager_required
def user_update(request, pk):
    staff = get_object_or_404(
        User,
        pk=pk,
        pharmacy=request.user.pharmacy,
        role=User.Role.STAFF,
        is_superuser=False,
    )

    if request.method == "POST":
        form = StaffUpdateForm(
            request.POST,
            instance=staff,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"{staff.name} 직원 정보를 수정했습니다.",
            )

            return redirect(
                "accounts:user_list"
            )

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
            "title": "직원 정보 수정",
            "submit_text": "저장",
        },
    )


@login_required
@staff_manager_required
@require_POST
def user_delete(request, pk):
    staff = get_object_or_404(
        User,
        pk=pk,
        pharmacy=request.user.pharmacy,
        role=User.Role.STAFF,
        is_superuser=False,
    )

    staff_name = staff.name
    staff.delete()

    messages.success(
        request,
        f"{staff_name} 직원을 삭제했습니다.",
    )

    return redirect("accounts:user_list")


@login_required
@superuser_required
def ownership_request_list(request):
    ownership_requests = (
        PharmacyOwnershipRequest.objects
        .select_related(
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

    return render(
        request,
        "accounts/ownership_request_list.html",
        {
            "ownership_requests": ownership_requests,
        },
    )


@login_required
@superuser_required
@require_POST
def ownership_request_approve(request, pk):
    ownership_request = get_object_or_404(
        PharmacyOwnershipRequest.objects.select_related(
            "user",
            "pharmacy",
        ),
        pk=pk,
        status=PharmacyOwnershipRequest.Status.PENDING,
    )

    user = ownership_request.user
    pharmacy = ownership_request.pharmacy
    business_number = ownership_request.business_number.strip()

    duplicate_pharmacy = (
        Pharmacy.objects
        .filter(business_number=business_number)
        .exclude(pk=pharmacy.pk)
        .first()
    )

    if duplicate_pharmacy:
        messages.error(
            request,
            (
                f"사업자등록번호 {business_number}는 이미 "
                f"{duplicate_pharmacy.pharmacy_name}에 등록되어 있습니다. "
                "신청 정보를 확인해 주세요."
            ),
        )

        return redirect(
            "accounts:ownership_request_list"
        )

    try:
        with transaction.atomic():
            ownership_request.status = (
                PharmacyOwnershipRequest.Status.APPROVED
            )
            ownership_request.processed_at = timezone.now()

            ownership_request.save(
                update_fields=[
                    "status",
                    "processed_at",
                ]
            )

            user.pharmacy = pharmacy
            user.role = User.Role.OWNER
            user.is_approved = True

            user.save(
                update_fields=[
                    "pharmacy",
                    "role",
                    "is_approved",
                ]
            )

            pharmacy.business_number = business_number

            if not pharmacy.owner_name:
                pharmacy.owner_name = user.name

            pharmacy.save(
                update_fields=[
                    "business_number",
                    "owner_name",
                    "updated_at",
                ]
            )

    except IntegrityError:
        messages.error(
            request,
            (
                "승인 처리 중 중복된 사업자등록번호가 확인되었습니다. "
                "신청 정보를 다시 확인해 주세요."
            ),
        )

        return redirect(
            "accounts:ownership_request_list"
        )

    messages.success(
        request,
        (
            f"{user.name} 사용자의 "
            f"{pharmacy.pharmacy_name} 점주 권한을 승인했습니다."
        ),
    )

    return redirect(
        "accounts:ownership_request_list"
    )


@login_required
@superuser_required
@require_POST
def ownership_request_reject(request, pk):
    ownership_request = get_object_or_404(
        PharmacyOwnershipRequest.objects.select_related(
            "user",
            "pharmacy",
        ),
        pk=pk,
        status=PharmacyOwnershipRequest.Status.PENDING,
    )

    ownership_request.status = (
        PharmacyOwnershipRequest.Status.REJECTED
    )

    ownership_request.processed_at = timezone.now()

    ownership_request.save(
        update_fields=[
            "status",
            "processed_at",
        ]
    )

    user = ownership_request.user
    user.is_approved = False

    user.save(
        update_fields=[
            "is_approved",
        ]
    )

    messages.success(
        request,
        f"{user.name} 사용자의 점주 권한 신청을 거절했습니다.",
    )

    return redirect(
        "accounts:ownership_request_list"
    )


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

            messages.success(
                request,
                f"{pharmacy.pharmacy_name} 정보를 수정했습니다.",
            )

            return redirect(
                "accounts:pharmacy_list"
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
            "cancel_url_name": "accounts:pharmacy_list",
        },
    )
    

@login_required
@staff_manager_required
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
    target_user.save(
        update_fields=["is_approved"]
    )

    messages.success(
        request,
        f"{target_user.name} 사용자를 승인했습니다.",
    )

    return redirect("accounts:user_list")


@login_required
@staff_manager_required
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
    target_user.save(
        update_fields=["is_approved"]
    )

    messages.success(
        request,
        f"{target_user.name} 사용자의 승인을 취소했습니다.",
    )

    return redirect("accounts:user_list")

