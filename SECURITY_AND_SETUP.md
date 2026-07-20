# PharmaFlow 보안·실행 설정

## 1. 환경변수

`.env.example`을 참고해 운영 서버의 EnvironmentFile 또는 셸 환경변수를 설정합니다.

필수 운영 값:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

개발 환경에서는 `DJANGO_DEBUG=True`를 설정해야 개발용 임시 SECRET_KEY가 허용됩니다.

## 2. 반영한 주요 보완

- 직원 이미지 업로드 폼의 multipart 설정
- 직원 삭제 대신 계정 비활성화
- 점주 승인·거절 동시 처리 잠금
- 관리자 일괄 승인 중복·상태 검사
- 회원가입 약국 검색 결과 세션 검증 및 기존 약국 정보 덮어쓰기 방지
- 약국 검색 요청 간단 속도 제한
- inventory 승인·소속 약국 접근 검사
- 게시판 첨부 이미지 실파일 검증 및 MIME 계열 검사
- 게시글·댓글·첨부 삭제 감사 로그 생성
- 캘린더 허용 연도 범위 검사
- 운영 보안 기본값과 `.gitignore`, `.env.example` 추가

## 3. 적용 후 명령

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
python manage.py collectstatic --noinput
```

이번 수정에서는 모델 필드를 변경하지 않았으므로 새 마이그레이션이 생성되지 않는 것이 정상입니다.

## 4. 로그 회전 (log rotation)

| 우선순위 | 로그 | 관리 방식 |
| --- | --- | --- |
| ★★★ | Nginx 접근 로그 (`access.log`) | 패키지 기본 `/etc/logrotate.d/nginx`가 자동 처리 |
| ★★★ | Nginx 오류 로그 (`error.log`) | 패키지 기본 `/etc/logrotate.d/nginx`가 자동 처리 |
| ★★★ | Gunicorn 로그 (`journalctl -u pharmaflow`) | 파일로 저장하지 않고 systemd 서비스의 표준출력을 journald가 수집 |
| ★★ | systemd(journalctl) 로그 | journald 자체 보관 설정(`/etc/systemd/journald.conf`)으로 관리 |
| ★ | Django 자체 로그 | `settings.py`에서 `LOGGING`을 설정한 경우에만 존재 (추후 관리 대상 추가 가능) |

- **Nginx**: 별도 설정 없이 이미 회전됨 (로그 경로를 바꾼 경우만 `deploy/logrotate/pharmaflow`의 참고 1 블록 사용).
- **Gunicorn**: `gunicorn.conf.py`에서 `accesslog`/`errorlog`를 `"-"`(표준출력/표준에러)로 지정해
  systemd 서비스(`pharmaflow`)의 로그로 흘러가게 함. 로그 확인은 `journalctl -u pharmaflow`,
  보관 기간/용량 조정은 journald 설정(`deploy/logrotate/pharmaflow`의 참고 2 블록 참고).
- **systemd(journalctl)**: 서비스 시작/종료 등 시스템 로그. journald가 자체적으로
  오래된 로그를 정리(vacuuming)하며, 필요 시 `SystemMaxUse`/`MaxRetentionSec`로 조정.
- **Django 자체 로그**: `LOGGING` 설정 시 `logs/django.log`에 기록됨 (환경변수 `LOG_DIR`로 경로 변경 가능).
  실제 회전은 `deploy/logrotate/pharmaflow`를 운영 서버의 `/etc/logrotate.d/pharmaflow`로 복사해서 적용.
