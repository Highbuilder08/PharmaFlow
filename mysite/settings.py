import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# 보안 설정
# ==================================================

# 운영 서버:
# /etc/pharmaflow/pharmaflow.env의 DJANGO_SECRET_KEY 사용

# 건강보험심사평가워(API 인증 기관)
# https://www.data.go.kr/iim/api/selectApiKeyList.do

# SECRET_KEY 발급 명령어
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 환경변수 + DB 계정 연동 설정값
# sudo vim /etc/pharmaflow/pharmaflow.env

# 시스템 리로드
# sudo systemctl daemon-reload
# sudo systemctl restart pharmaflow

# 개발 환경:
# 환경변수가 없으면 아래 개발용 키 사용
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
# 환경변수가 없으면 DEBUG=True
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
# 개발 환경:
# 환경변수가 없으면 아래 기본값 사용
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

STATIC_ROOT = BASE_DIR / "staticfiles"


# ==================================================
# 업로드 파일
# ==================================================

MEDIA_URL = "/media/"

# 여기서 MEDIA_ROOT는 "사용자가 올린 파일(사진, 첨부파일 등)을 실제로 저장하는 폴더"를 의미합니다.
#
# 현재 개발 환경에서는 프로젝트 내부의 media 폴더를 사용합니다.
#
# 프로젝트 경로
# /home/tester/djangowork/PharmaFlow
#
# NFS(Network File System)란: 여러 서버가 인터넷(사내망)으로 하나의 폴더를 공유해서 쓰는 방식입니다.
# 웹 서버(Server1)가 이 media 폴더 자리에 NFS 서버의 공유 폴더를 "마운트(연결)"하면,
# 실제 파일은 NFS 서버에 저장되지만 Server1 입장에서는 그냥 로컬 폴더처럼 보이게 됩니다.
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

# ※ 아래 내용은 settings.py에서 실행되는 코드가 아닙니다. (파이썬 코드 X, 그냥 메모입니다)
# ※ 서버 컴퓨터의 터미널(명령 프롬프트)에 직접 입력하는 명령어들을 적어놓은 것입니다.
# ※ 팀원의 NFS 서버 구축이 완료된 후 Server1에서 실행합니다.

# --------------------------------------------------
# 1. NFS 클라이언트 설치
# --------------------------------------------------
# Server1이 NFS 서버에 접속할 수 있도록 필요한 프로그램을 설치하는 단계
#
# sudo apt update
# sudo apt install nfs-common -y


# --------------------------------------------------
# 2. media 폴더 생성
# --------------------------------------------------
# NFS 공유 폴더를 연결(마운트)할 빈 폴더를 미리 만들어두는 단계
#
# mkdir -p /home/tester/djangowork/PharmaFlow/media


# --------------------------------------------------
# 3. NFS 서버 공유 확인
# --------------------------------------------------
# NFS 서버가 어떤 폴더를 공유하고 있는지 확인해보는 단계
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
# NFS 서버의 공유 폴더를 Server1의 media 폴더 자리에 실제로 연결하는 단계
#
# sudo mount -t nfs \
# 192.168.32.23:/srv/nfs/pharmaflow_media \
# /home/tester/djangowork/PharmaFlow/media


# --------------------------------------------------
# 5. 마운트 확인
# --------------------------------------------------
# 방금 연결(마운트)이 잘 되었는지 확인하는 단계
#
# mount | grep pharmaflow_media
#
# 또는
#
# df -h


# --------------------------------------------------
# 6. 테스트 파일 생성
# --------------------------------------------------
# 테스트 파일을 하나 만들어서, 정말 NFS 서버 쪽에 저장되는지 확인해보는 단계
#
# touch /home/tester/djangowork/PharmaFlow/media/nfs_test.txt
#
# ls -l /home/tester/djangowork/PharmaFlow/media


# --------------------------------------------------
# 7. 테스트 파일 삭제
# --------------------------------------------------
# 확인용으로 만들었던 테스트 파일을 지우는 단계 (실제 서비스에는 필요 없는 파일이므로)
#
# rm /home/tester/djangowork/PharmaFlow/media/nfs_test.txt


# --------------------------------------------------
# 8. 재부팅 후 자동 마운트
# --------------------------------------------------
# 서버를 껐다 켜도 매번 4번 명령어를 다시 입력하지 않도록,
# "컴퓨터가 켜질 때 자동으로 마운트해라"라고 설정 파일에 등록하는 단계
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
# Nginx(웹 서버)가 사용자 브라우저의 /media/ 요청을 받으면,
# 실제로는 이 media 폴더(=NFS 공유 폴더)에서 파일을 찾아 보내주도록 알려주는 설정입니다.
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


# 운영 환경 보안 기본값
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
