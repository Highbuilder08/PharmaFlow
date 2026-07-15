from django.shortcuts import render

from consultations.models import Consultation


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

    return render(
        request,
        "core/index.html",
        {
            "notices": notices,
            "recent_posts": recent_posts,
        },
    )
