# gunicorn.conf.py: gunicorn(웹 서버 프로그램)이 실행될 때 자동으로 읽어들이는 설정 파일
# "gunicorn -c gunicorn.conf.py mysite.wsgi:application" 처럼 실행하면 적용됨
import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")  # 어느 주소:포트로 요청을 받을지
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))  # 요청을 동시에 처리할 프로세스(워커) 개수

# accesslog/errorlog를 "-"로 두면 파일로 안 쓰고 화면(stdout/stderr)에 그대로 출력함.
# 운영 서버에서는 gunicorn을 systemd 서비스(pharmaflow)로 실행하는데,
# systemd는 stdout/stderr를 자동으로 journal(저널)에 모아주기 때문에
# 별도 로그 파일 없이 "journalctl -u pharmaflow" 명령으로 접속/에러 로그를 볼 수 있음.
# 이렇게 하면 로그 회전(rotate)도 logrotate가 아니라 journald가 알아서 처리해줌.
accesslog = "-"  # 접속 로그 (누가 어떤 요청을 보냈는지)
errorlog = "-"   # 에러 로그 (gunicorn 자체에서 발생한 에러)
loglevel = os.environ.get("LOG_LEVEL", "info").lower()  # 기록할 최소 등급 (기본: info)
