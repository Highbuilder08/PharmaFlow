# PharmaFlow 운영 매뉴얼

## 1. 프로젝트 개요

### 1.1 프로젝트명

PharmaFlow

### 1.2 프로젝트 목적

PharmaFlow는 약국 운영에 필요한 회원 및 약국 관리, 의약품 재고 관리,
입출고 관리, 발주 관리, 상담 관리 기능을 제공하는 Django 기반 약국 통합
관리 시스템이다.

### 1.3 운영 환경

-   운영체제: Ubuntu Server 24.04
-   Python: 3.12
-   Django: 5.x
-   Web Server: Nginx
-   Application Server: Gunicorn
-   Database: MariaDB
-   Storage: NFS
-   Version Control: GitHub

## 2. 시스템 구성

### 2.1 전체 구조

``` text
사용자(Client)
      │
      ▼
Nginx
      │
      ▼
Gunicorn
      │
      ▼
Django
   ├──────────┐
   ▼          ▼
MariaDB      NFS
```

### 2.2 서버 역할

#### Server1 (Web Server)

-   Django 실행
-   Gunicorn 실행
-   Nginx 실행
-   MariaDB 연결
-   NFS 연결
-   백업 스크립트 및 cron 실행

#### MariaDB Server

-   PharmaFlow 데이터베이스 저장
-   원격 접속 허용

#### NFS Server

-   업로드 파일(Media) 저장

## 3. 서버 및 디렉터리 구성

### 프로젝트 경로

``` text
/home/tester/djangowork/PharmaFlow
```

### 주요 디렉터리

``` text
PharmaFlow/
├── accounts/
├── consultations/
├── core/
├── inventory/
├── deploy/
│   ├── backup/
│   ├── logrotate/
│   └── manual/
├── media/
├── static/
├── templates/
└── manage.py
```

### 가상환경

``` text
/home/tester/djangoenv
```

### NFS 마운트 경로

``` text
/home/tester/djangowork/PharmaFlow/media
```

## 4. 서비스 관리

### Gunicorn

``` bash
sudo systemctl status pharmaflow
sudo systemctl restart pharmaflow
journalctl -u pharmaflow
```

### Nginx

``` bash
sudo nginx -t
sudo systemctl status nginx
sudo systemctl reload nginx
sudo systemctl restart nginx
```

### MariaDB

``` bash
sudo systemctl status mariadb
sudo systemctl restart mariadb
```

### NFS

``` bash
mount | grep nfs
mountpoint /home/tester/djangowork/PharmaFlow/media
df -h
```

## 5. 백업 및 복원

### MariaDB

-   백업 스크립트: `/home/tester/backup_mariadb.sh`
-   실행 시간: 매일 12:00
-   30일 경과 백업 자동 삭제

복원:

``` bash
mariadb --defaults-extra-file=/home/tester/.my.cnf pharmaflow < backup.sql
```

### NFS

-   백업 스크립트: `/home/tester/backup_nfs.sh`
-   실행 시간: 매일 12:10
-   30일 경과 백업 자동 삭제

복원:

``` bash
rsync -av 백업폴더/ /home/tester/djangowork/PharmaFlow/media/
```

## 6. 로그 관리

-   Django: deploy/logrotate/pharmaflow
-   Nginx: /var/log/nginx/access.log, error.log
-   Gunicorn: journalctl -u pharmaflow
-   journald 사용량: `journalctl --disk-usage`

## 7. 장애 대응

1.  Nginx 상태 확인
2.  Gunicorn 상태 확인
3.  Django 점검
4.  MariaDB 연결 확인
5.  NFS 마운트 확인

## 8. 배포 및 유지보수

``` bash
git pull origin main
source /home/tester/djangoenv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
sudo systemctl restart pharmaflow
sudo systemctl reload nginx
```

## 9. HTTPS 관리

구축 예정 - 도메인 연결 - Let's Encrypt 인증서 발급 - Nginx HTTPS 설정 -
Django 보안 설정

## 10. CI/CD

구축 예정 - GitHub Actions - 자동 테스트 - 자동 배포

## 11. 참고 사항

-   백업 성공 여부를 주기적으로 확인한다.
-   로그 용량을 점검한다.
-   NFS 마운트 상태를 확인한다.
-   복원 테스트를 정기적으로 수행한다.
