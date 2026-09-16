# ============================================================
# PharmaFlow Django - Docker Image
#
# 빌드 (저장소 루트에서):
#   docker build -f Docker/django/Dockerfile -t pharmaflow-django .
#
# 실행:
#   docker run --rm -p 8000:8000 --env-file .env pharmaflow-django
#
# Golden AMI v6(systemd + Gunicorn) 구성을 그대로 컨테이너화한 것.
# systemd는 쓰지 않고 Gunicorn을 컨테이너의 메인 프로세스(PID 1)로 직접 실행한다.
# DB/SECRET_KEY/SES/HIRA 등 비밀값은 이미지에 포함하지 않고
# 전부 런타임 환경변수(docker run -e / --env-file / K8s Secret 등)로 주입한다.
# ============================================================

# ---- 1단계: 빌드 ----
# mysqlclient는 소스에서 컴파일되므로 컴파일러/헤더가 필요하다.
# 이 계층은 최종 이미지에 포함되지 않는다 (venv만 복사).
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ---- 2단계: 런타임 ----
# 컴파일러 없이, mysqlclient가 링크하는 런타임 공유 라이브러리만 설치한다.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    ca-certificates \
    curl \
    && curl -fsSL \
      https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
      -o /etc/ssl/certs/aws-rds-global-bundle.pem \
    && test -s /etc/ssl/certs/aws-rds-global-bundle.pem \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system django \
    && useradd --system --gid django --home-dir /app --no-create-home django

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY . .

# 정적/미디어/로그 - 운영에서는 이 경로에 외부 Volume(EFS, k8s PVC 등)을 마운트한다.
# 마운트 없이 단독 실행할 때도 죽지 않도록 빈 디렉터리를 미리 만들어둔다.
# 외부 볼륨은 어떤 UID로 마운트될지 미리 알 수 없으므로, 마운트 대상 3곳만
# world-writable로 열어둔다 (앱 소스 코드 자체는 django:django 소유 그대로 유지).
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R django:django /app \
    && chmod -R 0777 /app/staticfiles /app/media /app/logs

# 컨테이너 환경의 합리적인 기본값만 지정한다.
# DB_*, DJANGO_SECRET_KEY, EMAIL_*, HIRA_SERVICE_KEY 는 여기 두지 않는다 - 런타임 주입 전용.
ENV DJANGO_DEBUG=False \
    GUNICORN_BIND=0.0.0.0:8000 \
    GUNICORN_WORKERS=3 \
    LOG_LEVEL=INFO

USER django

EXPOSE 8000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "mysite.wsgi:application"]
