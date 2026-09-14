# PharmaFlow Django - Docker

Golden AMI v6(systemd + Gunicorn) 구성을 컨테이너화한 이미지. systemd는 쓰지 않고
Gunicorn을 컨테이너의 메인 프로세스(PID 1)로 직접 실행한다.

## 빌드

저장소 루트에서 실행한다 (build context가 루트여야 `manage.py`, `requirements.txt` 등에 접근 가능).

```bash
docker build -f Docker/django/Dockerfile -t pharmaflow-django .
```

## 실행

DB/SECRET_KEY/SES/HIRA 등 비밀값은 이미지에 포함되어 있지 않다. 실행할 때 환경변수로 주입한다.
전체 변수 목록은 저장소 루트의 `.env.example` 참고.

```bash
docker run -d --name pharmaflow \
  -p 8000:8000 \
  -e DJANGO_SECRET_KEY=<실제 값> \
  -e DJANGO_DEBUG=False \
  -e DJANGO_ALLOWED_HOSTS=<도메인/ALB DNS> \
  -e DB_NAME=pharmaflow \
  -e DB_USER=pharmaflow_user \
  -e DB_PASSWORD=<실제 값> \
  -e DB_HOST=<RDS 엔드포인트> \
  -e DB_PORT=3306 \
  pharmaflow-django
```

`--env-file .env` 로 한 번에 넘겨도 된다 (`.env`는 `.dockerignore`/`.gitignore`에 걸려 있어 이미지·Git 어디에도 들어가지 않는다).

### 로컬에서 DB 없이 빠르게만 확인하고 싶을 때

`DB_ENGINE=django.db.backends.sqlite3` 를 주면 RDS 연결 없이 SQLite로 뜬다
(`/health/ready/` 는 DB 엔진과 무관하게 `SELECT 1` 이 통하는지만 보므로 SQLite에서도 200이 나온다).

```bash
docker run -d --name pharmaflow -p 8000:8000 \
  -e DJANGO_SECRET_KEY=dev-only \
  -e DJANGO_ALLOWED_HOSTS=localhost \
  -e DB_ENGINE=django.db.backends.sqlite3 \
  pharmaflow-django
```

## Static / Media 외부 Volume

`/app/staticfiles`(STATIC_ROOT 기본값), `/app/media`, `/app/logs` 세 경로는 컨테이너
내부에 빈 디렉터리로 미리 만들어 두었고, 외부 볼륨이 어떤 UID로 마운트되든 쓸 수 있도록
`chmod 0777` 해두었다 (앱 소스 코드 자체는 그대로 `django` 유저 소유).

**Named volume (k8s PVC와 동일한 동작 - 권장)**

```bash
docker volume create pharmaflow-static
docker run --rm -v pharmaflow-static:/app/staticfiles pharmaflow-django \
  python manage.py collectstatic --noinput
```

**호스트 디렉터리 bind mount** — 호스트 디렉터리는 컨테이너 이미지의 권한을 상속하지 않고
호스트 자체 권한을 그대로 쓰므로, `--user`로 호스트 UID를 맞춰줘야 쓰기가 된다.

```bash
mkdir -p ./static_data
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$(pwd)/static_data:/app/staticfiles" \
  pharmaflow-django python manage.py collectstatic --noinput
```

운영에서는 EFS를 이 경로들에 마운트한다 (Ansible role의 media/static EFS 마운트와 동일한 목적).

## DB 마이그레이션 (1회성 실행)

```bash
docker run --rm --env-file .env pharmaflow-django python manage.py migrate --noinput
```

## Health Check

- `/health/live/` — 프로세스 생존 여부만 확인 (DB 조회 없음)
- `/health/ready/` — `SELECT 1` 로 DB 연결 확인, 실패 시 503

```bash
curl localhost:8000/health/live/
curl localhost:8000/health/ready/
```

## 검증 완료 항목

- [x] `docker build` 성공
- [x] `docker run` 컨테이너 정상 기동 (Gunicorn이 PID 1, systemd 없음 - `/proc/1/comm` 확인)
- [x] Gunicorn `0.0.0.0:8000` 정상 바인딩
- [x] `/health/live/` → 200
- [x] `/health/ready/` → 200
- [x] 환경변수 외부 주입 (`docker run -e` / `--env-file`)
- [x] 이미지에 Secret 미포함 (`docker inspect` 로 baked-in ENV 확인, `.env` 이미지 내 미존재)
- [x] non-root 유저(`django`, uid 999)로 실행
- [x] Static/Media 외부 Volume 마운트 (named volume, host bind mount + `--user` 둘 다 검증)
