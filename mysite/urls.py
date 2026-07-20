# ==================================================
# 파일 역할: 프로젝트 전체 URL을 각 Django 앱에 연결하는 최상위 URL 설정 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path

from accounts.forms import ApprovedAuthenticationForm


urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "accounts/login/",
        LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=ApprovedAuthenticationForm,
        ),
        name="login",
    ),

    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),

    path("consultation/", include("consultations.urls")),
    path("inventory/", include("inventory.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
