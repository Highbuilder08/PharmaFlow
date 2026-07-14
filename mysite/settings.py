import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


# 보안 설정
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = os.environ.get(
    "DJANGO_DEBUG",
    "False",
).lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "192.168.32.87,127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]


# 애플리케이션
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "accounts.apps.AccountsConfig",
    "core.apps.CoreConfig",
    "inventory.apps.InventoryConfig",
    "prescriptions.apps.PrescriptionsConfig",
    "consultations.apps.ConsultationsConfig",
]


# 미들웨어
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "mysite.urls"


# 템플릿
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "mysite.wsgi.application"


# 데이터베이스
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get(
            "DB_NAME",
            "pharmaflow",
        ),
        "USER": os.environ.get(
            "DB_USER",
            "admin",
        ),
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ.get(
            "DB_HOST",
            "192.168.32.87",
        ),
        "PORT": os.environ.get(
            "DB_PORT",
            "3306",
        ),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# 사용자 모델
AUTH_USER_MODEL = "accounts.User"


# 비밀번호 검증
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# 국제화
LANGUAGE_CODE = "ko-kr"

TIME_ZONE = "Asia/Seoul"

USE_I18N = True

USE_TZ = True


# 정적 파일
STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# 업로드 파일
MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# 로그인 설정
LOGIN_URL = "/accounts/login/"

LOGIN_REDIRECT_URL = "/"

LOGOUT_REDIRECT_URL = "/"


# 외부 API
HIRA_SERVICE_KEY = os.environ.get(
    "HIRA_SERVICE_KEY",
    "",
)

# HTTPS 적용 후 활성화
# SECURE_PROXY_SSL_HEADER = (
#     "HTTP_X_FORWARDED_PROTO",
#     "https",
# )

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
