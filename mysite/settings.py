# ==================================================
# 파일 역할: PharmaFlow 프로젝트의 앱, 데이터베이스, 보안, 정적·미디어 파일 설정 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# 보안 설정
# ==================================================

# 운영 서버:
# /etc/pharmaflow/pharmaflow.env의 DJANGO_SECRET_KEY 사용

# 건강보험심사평가원(API 인증 기관)
# https://www.data.go.kr/iim/api/selectApiKeyList.do

# SECRET_KEY 발급 명령어
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 환경변수 + DB 계정 연동 설정값
# sudo vim /etc/pharmaflow/pharmaflow.env

# 시스템 리로드
# sudo systemctl daemon-reload
# sudo systemctl restart pharmaflow

# 개발 환경:
# 환경변수 적용중
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")

# 개발 환경에서는 임시 키를 허용하지만 운영 환경에서는 필수입니다.
if not SECRET_KEY:
    if os.environ.get("DJANGO_DEBUG", "False").lower() == "true":
        SECRET_KEY = "django-insecure-development-only-change-me"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY 환경변수가 필요합니다.")

# 운영 서버의 EnvironmentFile:
# DJANGO_DEBUG=False
#
# 팀원 개발 환경:
# 환경변수가 없으면 DEBUG=False
DEBUG = (
    os.environ.get(
        "DJANGO_DEBUG",
        "False",
    ).lower()
    == "true"
)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "192.168.32.87,127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]


# ==================================================
# 애플리케이션
# ==================================================

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
    "consultations.apps.ConsultationsConfig",
]


# ==================================================
# 미들웨어
# ==================================================

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


# ==================================================
# 템플릿
# ==================================================

TEMPLATES = [
    {
        "BACKEND": ("django.template.backends.django." "DjangoTemplates"),
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                ("django.template.context_processors." "request"),
                ("django.contrib.auth.context_processors." "auth"),
                ("django.contrib.messages.context_processors." "messages"),
            ],
        },
    },
]


WSGI_APPLICATION = "mysite.wsgi.application"


# ==================================================
# 데이터베이스
# ==================================================

# 운영 서버:
# EnvironmentFile에 설정된 DB_* 값을 사용
#
# GitHub Actions:
# DB_ENGINE=django.db.backends.sqlite3 환경변수를 설정하여
# 외부 MariaDB 서버 없이 임시 SQLite 데이터베이스로 검사합니다.
DB_ENGINE = os.environ.get(
    "DB_ENGINE",
    "django.db.backends.mysql",
)

if DB_ENGINE == "django.db.backends.sqlite3":
    # CI 환경에서 사용하는 임시 SQLite 데이터베이스
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "ci.sqlite3",
        }
    }
else:
    # 실제 운영 서버에서 사용하는 MariaDB 데이터베이스
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get(
                "DB_NAME",
                "pharmaflow",
            ),
            "USER": os.environ.get(
                "DB_USER",
                "pharmaflow",
            ),
            "PASSWORD": os.environ.get(
                "DB_PASSWORD",
                "",
            ),
            "HOST": os.environ.get(
                "DB_HOST",
                "192.168.32.77",
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


# ==================================================
# 사용자 모델
# ==================================================

AUTH_USER_MODEL = "accounts.User"


# ==================================================
# 비밀번호 검증
# ==================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": ("django.contrib.auth.password_validation." "MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation." "CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation." "NumericPasswordValidator"),
    },
]


# ==================================================
# 국제화
# ==================================================

LANGUAGE_CODE = "ko-kr"

TIME_ZONE = "Asia/Seoul"

USE_I18N = True

USE_TZ = True


# ==================================================
# 정적 파일
# ==================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# collectstatic 산출물이 모이는 위치입니다.
# 운영 환경에서는 Nginx가 직접 서빙하는 경로나 공유 스토리지(EFS 등)로
# 바꿔야 할 수 있어, 코드 수정 없이 환경변수로 지정할 수 있게 합니다.
# 개발 환경에서는 기본값(프로젝트 내부 staticfiles/)을 그대로 사용합니다.
STATIC_ROOT = Path(os.environ.get("STATIC_ROOT", BASE_DIR / "staticfiles"))


# ==================================================
# 업로드 파일
# ==================================================

MEDIA_URL = "/media/"

# 사용자가 업로드한 사진·첨부파일의 실제 저장 위치입니다.
# 개발 환경에서는 프로젝트 내부의 media/ 디렉터리를 사용합니다.
# 운영 환경에서는 이 경로에 NFS 공유 디렉터리를 마운트하여 사용합니다.
MEDIA_ROOT = BASE_DIR / "media"


# ==================================================
# 로그인 설정
# ==================================================

LOGIN_URL = "/accounts/login/"

LOGIN_REDIRECT_URL = "/"

LOGOUT_REDIRECT_URL = "/"


# ==================================================
# 이메일(SMTP)
# ==================================================

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER or "webmaster@localhost",
)

# 비밀번호 재설정 링크의 기본 유효시간(30분)
PASSWORD_RESET_TIMEOUT = int(
    os.environ.get("PASSWORD_RESET_TIMEOUT", "1800")
)


# ==================================================
# 외부 API
# ==================================================

# 운영 서버:
# EnvironmentFile에 HIRA_SERVICE_KEY 설정
#
# 개발 환경:
# 필요한 팀원은 직접 환경변수 적용중
HIRA_SERVICE_KEY = os.environ.get(
    "HIRA_SERVICE_KEY",
    "",
)


# ==================================================
# HTTPS 적용 후 활성화
# ==================================================

# SECURE_PROXY_SSL_HEADER = (
#     "HTTP_X_FORWARDED_PROTO",
#     "https",
# )

# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# SECURE_HSTS_SECONDS = 3600
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = False


# 운영 환경 보안 기본값
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==================================================
# 로그
# ==================================================

# 운영 서버:
# EnvironmentFile에 LOG_DIR 설정 (예: /var/log/pharmaflow)
#
# 개발 환경:
# 환경변수가 없으면 프로젝트 폴더 안의 logs/ 사용
LOG_DIR = Path(os.environ.get("LOG_DIR", BASE_DIR / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 실제로 로그 파일을 잘라내고(rotate) 압축·삭제하는 작업은
# 이 settings.py가 아니라 서버의 logrotate가 담당합니다.
# (gunicorn은 여러 워커 프로세스가 동시에 같은 로그 파일에 쓰기 때문에,
#  각 프로세스가 각자 파일 크기를 보고 회전을 시도하면 로그가 깨질 수 있습니다.
#  그래서 Django 쪽은 파일에 쓰기만 하고, WatchedFileHandler로
#  logrotate가 파일 이름을 바꿔치기했을 때 자동으로 새 파일을 다시 여는 역할만 합니다.)
LOGGING = {
    "version": 1,  # 이 로깅 설정 형식의 버전 번호 (Django에서 항상 1로 고정)
    "disable_existing_loggers": False,  # Django가 원래 갖고 있던 다른 로그 설정을 끄지 않고 그대로 둠
    # formatters: 로그 한 줄을 어떤 모양으로 찍을지 정하는 곳
    "formatters": {
        "verbose": {
            # 예: [2026-07-20 12:00:00] INFO django.request: 에러 내용
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    # handlers: 로그를 "어디에" 남길지 정하는 곳 (화면 / 파일 등)
    "handlers": {
        "console": {  # 터미널 화면에 바로 출력
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {  # logs/django.log 파일에 기록
            "class": "logging.handlers.WatchedFileHandler",
            "filename": LOG_DIR / "django.log",
            "formatter": "verbose",
        },
    },
    # root: 별도로 지정하지 않은 나머지 모든 로그가 기본으로 사용하는 설정
    "root": {
        "handlers": ["console", "file"],  # 화면과 파일에 동시에 기록
        "level": os.environ.get(
            "LOG_LEVEL", "INFO"
        ),  # 이 등급 이상만 기록 (기본: INFO)
    },
    # loggers: 특정 이름의 로그만 따로 다르게 다루고 싶을 때 사용
    "loggers": {
        # 페이지 처리 중 발생한 500 에러 등을 별도로 크게 남김
        "django.request": {
            "handlers": ["console", "file"],
            "level": "ERROR",  # ERROR 이상(진짜 문제인 것)만 기록
            "propagate": False,  # root로 또 전달해서 중복 기록되지 않게 함
        },
    },
}
