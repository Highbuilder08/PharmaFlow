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
    path("prescription/", include("prescriptions.urls")),
    path("consultation/", include("consultations.urls")),
    path("inventory/", include("inventory.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
