import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .decorators import owner_required, superuser_required
from .forms import PharmacyForm, SignUpForm
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
                    external_place_id=data["pharmacy_place_id"],
                    defaults={
                        "pharmacy_name": data["pharmacy_name"],
                        "address": data["pharmacy_address"],
                        "phone": data.get("pharmacy_phone", ""),
                        "latitude": data["pharmacy_latitude"],
                        "longitude": data["pharmacy_longitude"],
                        "data_source": Pharmacy.DataSource.KAKAO,
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
                message = (
                    "회원가입과 점주 권한 신청이 완료되었습니다. "
                    "시스템 관리자 승인 후 로그인할 수 있습니다."
                )
            else:
                message = (
                    "회원가입이 완료되었습니다. "
                    "소속 약국 점주의 승인 후 로그인할 수 있습니다."
                )

            messages.success(request, message)
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

    if not settings.KAKAO_REST_API_KEY:
        return JsonResponse(
            {
                "results": [],
                "error": "카카오 REST API 키가 설정되지 않았습니다.",
            },
            status=500,
        )

    try:
        response = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={
                "Authorization": (
                    f"KakaoAK {settings.KAKAO_REST_API_KEY}"
                ),
            },
            params={
                "query": query,
                "category_group_code": "PM9",
                "size": 15,
            },
            timeout=5,
        )

        response.raise_for_status()
    except requests.RequestException:
        return JsonResponse(
            {
                "results": [],
                "error": "약국 검색 서비스에 연결할 수 없습니다.",
            },
            status=502,
        )

    results = []

    for document in response.json().get("documents", []):
        results.append(
            {
                "place_id": document["id"],
                "name": document["place_name"],
                "address": (
                    document.get("road_address_name")
                    or document.get("address_name")
                    or ""
                ),
                "phone": document.get("phone", ""),
                "longitude": document["x"],
                "latitude": document["y"],
            }
        )

    return JsonResponse(
        {
            "results": results,
        }
    )


@login_required
def pharmacy_list(request):
    if request.user.is_superuser:
        pharmacies = Pharmacy.objects.all()
    elif request.user.pharmacy_id:
        pharmacies = Pharmacy.objects.filter(
            pk=request.user.pharmacy_id
        )
    else:
        pharmacies = Pharmacy.objects.none()

    pharmacies = pharmacies.order_by("pharmacy_name")

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
        form = PharmacyForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "약국이 등록되었습니다.",
            )
            return redirect("accounts:pharmacy_list")
    else:
        form = PharmacyForm()

    return render(
        request,
        "accounts/pharmacy_form.html",
        {
            "form": form,
            "title": "약국 등록",
            "submit_text": "등록",
        },
    )


@login_required
def pharmacy_update(request, pk):
    pharmacy = get_object_or_404(Pharmacy, pk=pk)

    if not (
        request.user.is_superuser
        or (
            request.user.role == User.Role.OWNER
            and request.user.is_approved
            and request.user.pharmacy_id == pharmacy.pk
        )
    ):
        messages.error(
            request,
            "해당 약국을 수정할 권한이 없습니다.",
        )
        return redirect("accounts:pharmacy_list")

    if request.method == "POST":
        form = PharmacyForm(
            request.POST,
            instance=pharmacy,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "약국 정보가 수정되었습니다.",
            )
            return redirect("accounts:pharmacy_list")
    else:
        form = PharmacyForm(instance=pharmacy)

    return render(
        request,
        "accounts/pharmacy_form.html",
        {
            "form": form,
            "title": "약국 수정",
            "submit_text": "수정",
        },
    )


@login_required
@superuser_required
def pharmacy_delete(request, pk):
    pharmacy = get_object_or_404(Pharmacy, pk=pk)

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

        return redirect("accounts:pharmacy_list")

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
        .exclude(pk=request.user.pk)
        .exclude(is_superuser=True)
        .order_by("is_approved", "name", "username")
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
            "다른 점주 계정은 이 화면에서 승인할 수 없습니다.",
        )
        return redirect("accounts:user_list")

    target_user.is_approved = True
    target_user.save(update_fields=["is_approved"])

    messages.success(
        request,
        f"{target_user.name} 사용자를 승인했습니다.",
    )

    return redirect("accounts:user_list")


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
            "다른 점주 계정은 이 화면에서 처리할 수 없습니다.",
        )
        return redirect("accounts:user_list")

    target_user.is_approved = False
    target_user.save(update_fields=["is_approved"])

    messages.success(
        request,
        f"{target_user.name} 사용자의 승인을 취소했습니다.",
    )

    return redirect("accounts:user_list")


@login_required
@superuser_required
def ownership_request_list(request):
    ownership_requests = (
        PharmacyOwnershipRequest.objects
        .select_related("user", "pharmacy")
        .order_by("status", "-id")
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
        PharmacyOwnershipRequest,
        pk=pk,
    )

    if ownership_request.status != PharmacyOwnershipRequest.Status.PENDING:
        messages.error(
            request,
            "이미 처리된 점주 권한 신청입니다.",
        )
        return redirect("accounts:ownership_request_list")

    with transaction.atomic():
        ownership_request.status = (
            PharmacyOwnershipRequest.Status.APPROVED
        )
        ownership_request.save(update_fields=["status"])

        user = ownership_request.user
        user.role = User.Role.OWNER
        user.pharmacy = ownership_request.pharmacy
        user.is_approved = True
        user.save(
            update_fields=[
                "role",
                "pharmacy",
                "is_approved",
            ]
        )

    messages.success(
        request,
        f"{user.name} 사용자의 점주 권한을 승인했습니다.",
    )

    return redirect("accounts:ownership_request_list")


@login_required
@superuser_required
@require_POST
def ownership_request_reject(request, pk):
    ownership_request = get_object_or_404(
        PharmacyOwnershipRequest,
        pk=pk,
    )

    if ownership_request.status != PharmacyOwnershipRequest.Status.PENDING:
        messages.error(
            request,
            "이미 처리된 점주 권한 신청입니다.",
        )
        return redirect("accounts:ownership_request_list")

    ownership_request.status = (
        PharmacyOwnershipRequest.Status.REJECTED
    )
    ownership_request.save(update_fields=["status"])

    messages.success(
        request,
        f"{ownership_request.user.name} 사용자의 "
        "점주 권한 신청을 거절했습니다.",
    )

    return redirect("accounts:ownership_request_list")


