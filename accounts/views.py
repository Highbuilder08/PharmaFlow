from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PharmacyForm, SignUpForm
from .models import Pharmacy


def signup(request):
    if request.user.is_authenticated:
        return redirect("core:index")

    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            messages.success(
                request,
                "회원가입이 완료되었습니다.",
            )

            return redirect("core:index")
    else:
        form = SignUpForm()

    return render(
        request,
        "accounts/signup.html",
        {
            "form": form,
        },
    )


@login_required
def pharmacy_list(request):
    pharmacies = Pharmacy.objects.all().order_by("pharmacy_name")

    return render(
        request,
        "accounts/pharmacy_list.html",
        {
            "pharmacies": pharmacies,
        },
    )


@login_required
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
        },
    )


@login_required
def pharmacy_update(request, pk):
    pharmacy = get_object_or_404(Pharmacy, pk=pk)

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
        form = PharmacyForm(
            instance=pharmacy,
        )

    return render(
        request,
        "accounts/pharmacy_form.html",
        {
            "form": form,
            "title": "약국 수정",
        },
    )


@login_required
def pharmacy_delete(request, pk):
    pharmacy = get_object_or_404(Pharmacy, pk=pk)

    if request.method == "POST":
        pharmacy.delete()

        messages.success(
            request,
            "약국이 삭제되었습니다.",
        )

        return redirect("accounts:pharmacy_list")

    return render(
        request,
        "accounts/pharmacy_confirm_delete.html",
        {
            "pharmacy": pharmacy,
        },
    )

