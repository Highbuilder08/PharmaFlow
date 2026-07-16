import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# 보안 설정
# ==================================================

# 운영 서버:
# /etc/pharmaflow/pharmaflow.env의 DJANGO_SECRET_KEY 사용
#
# 개발 환경:
# 환경변수가 없으면 아래 개발용 키 사용
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    ("django-insecure-" "pharmaflow-development-secret-key-only"),
)

# 운영 서버의 EnvironmentFile:
# DJANGO_DEBUG=False
#
# 팀원 개발 환경:
# 환경변수가 없으면 DEBUG=True
DEBUG = (
    os.environ.get(
        "DJANGO_DEBUG",
        "True",
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
    "prescriptions.apps.PrescriptionsConfig",
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
# 개발 환경:
# 환경변수가 없으면 아래 기본값 사용
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get(
            "DB_NAME",
            "pharmaflow", # DB 이름
        ),
        "USER": os.environ.get(
            "DB_USER",
            "pharmaflow", # DB '사용자' 이름
        ),
        "PASSWORD": os.environ.get(
            "DB_PASSWORD",
            "", # 환경변수에서만 읽음
        ),
        "HOST": os.environ.get(
            "DB_HOST",
            "192.168.32.77", # DB 서버 주소
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

STATIC_ROOT = BASE_DIR / "staticfiles"


# ==================================================
# 업로드 파일
# ==================================================

MEDIA_URL = "/media/"

# 현재 개발 환경에서는 프로젝트 내부의 media 폴더를 사용합니다.
#
# 프로젝트 경로
# /home/tester/djangowork/PharmaFlow
#
# NFS 서버 연동이 완료되면 Server1에서 아래 경로에
# NFS 공유 폴더를 마운트할 예정입니다.
#
# NFS 서버
# 192.168.32.23:/srv/nfs/pharmaflow_media
#
# Server1 마운트 위치
# /home/tester/djangowork/PharmaFlow/media
#
# NFS를 위 경로에 마운트하면 Django 설정을 수정하지 않아도
# MEDIA_ROOT가 자동으로 NFS 저장소를 사용하게 됩니다.
MEDIA_ROOT = BASE_DIR / "media"


# ==================================================
# NFS 연동 예정 (참고용 메모)
# ==================================================

# ※ 아래 내용은 settings.py에서 실행되는 코드가 아닙니다.
# ※ 팀원의 NFS 서버 구축이 완료된 후 Server1에서 실행합니다.

# --------------------------------------------------
# 1. NFS 클라이언트 설치
# --------------------------------------------------
#
# sudo apt update
# sudo apt install nfs-common -y


# --------------------------------------------------
# 2. media 폴더 생성
# --------------------------------------------------
#
# mkdir -p /home/tester/djangowork/PharmaFlow/media


# --------------------------------------------------
# 3. NFS 서버 공유 확인
# --------------------------------------------------
#
# showmount -e 192.168.32.23
#
# 정상이라면
#
# /srv/nfs/pharmaflow_media
#
# 가 표시됩니다.


# --------------------------------------------------
# 4. NFS 수동 마운트
# --------------------------------------------------
#
# sudo mount -t nfs \
# 192.168.32.23:/srv/nfs/pharmaflow_media \
# /home/tester/djangowork/PharmaFlow/media


# --------------------------------------------------
# 5. 마운트 확인
# --------------------------------------------------
#
# mount | grep pharmaflow_media
#
# 또는
#
# df -h


# --------------------------------------------------
# 6. 테스트 파일 생성
# --------------------------------------------------
#
# touch /home/tester/djangowork/PharmaFlow/media/nfs_test.txt
#
# ls -l /home/tester/djangowork/PharmaFlow/media


# --------------------------------------------------
# 7. 테스트 파일 삭제
# --------------------------------------------------
#
# rm /home/tester/djangowork/PharmaFlow/media/nfs_test.txt


# --------------------------------------------------
# 8. 재부팅 후 자동 마운트
# --------------------------------------------------
#
# sudo nano /etc/fstab
#
# 맨 아래에 추가
#
# 192.168.32.23:/srv/nfs/pharmaflow_media /home/tester/djangowork/PharmaFlow/media nfs defaults,_netdev 0 0
#
# 저장 후
#
# sudo mount -a


# ==================================================
# Nginx 설정 예정
# ==================================================
#
# server 블록 안에 추가
#
# location /media/ {
#     alias /home/tester/djangowork/PharmaFlow/media/;
# }
#
# 설정 확인
#
# sudo nginx -t
#
# 재시작
#
# sudo systemctl restart nginx


# ==================================================
# 로그인 설정
# ==================================================

LOGIN_URL = "/accounts/login/"

LOGIN_REDIRECT_URL = "/"

LOGOUT_REDIRECT_URL = "/"


# ==================================================
# 외부 API
# ==================================================

# 운영 서버:
# EnvironmentFile에 HIRA_SERVICE_KEY 설정
#
# 개발 환경:
# 필요한 팀원은 직접 환경변수 설정
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


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
