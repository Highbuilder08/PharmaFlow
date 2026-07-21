```{=html}
<p align="center">
```
`<img src="./images/logo.png" width="170" alt="PharmaFlow Logo">`{=html}
```{=html}
</p>
```
```{=html}
<h1 align="center">
```
PharmaFlow
```{=html}
</h1>
```
```{=html}
<p align="center">
```
💊 약국 통합 관리 시스템
```{=html}
</p>
```
```{=html}
<p align="center">
```
Django · MariaDB · Nginx · Gunicorn · NFS
```{=html}
</p>
```

------------------------------------------------------------------------

## 📌 프로젝트 소개

**PharmaFlow**는 약국 업무를 효율적으로 관리하기 위한 웹 기반 약국 통합
관리 시스템입니다.

회원 관리, 점주 승인, 약국 관리, 의약품 재고 관리, 자유 게시판 기능을
하나의 시스템으로 제공합니다.

------------------------------------------------------------------------

## 🎯 프로젝트 목적

-   약국 업무의 전산화
-   재고 및 입출고 관리 효율화
-   약국 관계자 간 정보 공유
-   운영 환경 구축(Nginx, Gunicorn, MariaDB, NFS)

------------------------------------------------------------------------

## 👨‍💻 팀 구성

  이름     담당
  -------- ---------------------------------------------------
  고건희   Accounts, Core, 사용자 인증, 약국 관리, 서버 구축
  서보성   Inventory, 의약품/재고/입출고/발주 관리
  홍성빈   Consultations, Prescriptions, 게시판 및 처방 기능

------------------------------------------------------------------------

## 🛠 기술 스택

-   Python 3.12
-   Django
-   HTML5 / CSS3 / Bootstrap 5 / JavaScript
-   MariaDB
-   Ubuntu Server 24.04
-   Gunicorn
-   Nginx
-   NFS
-   Git / GitHub / GitHub Actions

------------------------------------------------------------------------

## ✨ 주요 기능

-   회원가입 / 로그인
-   점주 승인 시스템
-   HIRA API 약국 검색
-   약국 관리
-   직원 관리
-   의약품 및 재고 관리
-   입출고 및 발주 관리
-   자유 게시판
-   시스템 로그

------------------------------------------------------------------------

## 📁 프로젝트 구조

``` text
PharmaFlow/
├── accounts/
├── consultations/
├── core/
├── inventory/
├── prescriptions/
├── templates/
├── static/
├── media/
├── deploy/
└── mysite/
```

------------------------------------------------------------------------

## 🖥 서버 구성

``` text
사용자
   │
 Nginx
   │
Gunicorn
   │
 Django
   │
MariaDB

Media ──▶ NFS
```

------------------------------------------------------------------------

## 🚀 실행 방법

``` bash
python -m venv djangoenv
source djangoenv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

------------------------------------------------------------------------

## ⚙ 운영 기능

-   NFS 파일 저장
-   MariaDB 백업
-   NFS 백업
-   Logrotate
-   환경변수 분리
-   GitHub Actions(CI)

------------------------------------------------------------------------

## 📄 운영 문서

-   `deploy/SECURITY_AND_SETUP.md`

------------------------------------------------------------------------

## 📜 License

교육 및 팀 프로젝트 목적으로 제작되었습니다.
