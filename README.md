
<p align="center">
    <img src="./images/logo.png" width="180" alt="PharmaFlow Logo">
</p>

<h1 align="center">PharmaFlow</h1>

<p align="center">
💊 약국 통합 관리 시스템
</p>

<p align="center">
Django · MariaDB · Nginx · Gunicorn · NFS
</p>

---

# 📌 프로젝트 소개

**PharmaFlow**는 약국 업무를 효율적으로 관리하기 위한 웹 기반 약국 통합 관리 시스템입니다.

회원 관리, 이메일 인증, 점주 승인, HIRA 약국 검색, 지도 기반 약국 선택,
의약품 재고 관리, 입출고 및 발주 관리, 자유 게시판, 첨부파일 관리,
일정 관리와 시스템 로그 기능을 하나의 시스템에서 제공합니다.

---

# 🎯 프로젝트 목적

- 약국 업무의 전산화
- 재고 및 입출고 관리 효율화
- 약국 관계자 간 정보 공유
- 실제 운영 환경 기반 서버 구축

---

# 👨‍💻 팀 구성

| 이름 | 담당 |
|------|------|
| **고건희** | Accounts, Core, 사용자 인증, 약국 관리, 서버 구축 |
| **서보성** | Inventory, 의약품·재고·입출고·발주 관리 |
| **홍성빈** | Consultations, Prescriptions, 게시판 및 처방 기능 |

---

# 🛠 기술 스택

- Python 3.12
- Django
- HTML5 / CSS3 / Bootstrap 5 / JavaScript
- MariaDB
- Ubuntu Server 24.04
- Gunicorn
- Nginx
- NFS
- Leaflet
- OpenStreetMap
- HIRA Open API
- Git / GitHub / GitHub Actions

---

# ✨ 주요 기능

## 계정 관리
- 회원가입 / 로그인
- 이메일 인증 (6자리 인증번호)
- 비밀번호 찾기 (아이디 + 이메일 확인)
- 점주 승인 및 직원 승인
- 마이페이지

## 약국 관리
- HIRA API 약국 검색
- 지도 기반 약국 선택
- 약국 정보 관리
- 직원 관리

## 재고 관리
- 의약품 관리
- 재고 관리
- 입출고 관리
- 발주 관리

## 게시판
- 자유 게시판
- 첨부파일 업로드
- 이미지 및 첨부파일 다운로드

## 기타
- 일정 관리
- 시스템 로그(Audit Log)

---

# 📁 프로젝트 구조

```text
PharmaFlow/
├── accounts/         # 회원, 인증, 약국 관리
├── consultations/    # 자유게시판
├── core/             # 메인 페이지
├── inventory/        # 재고/입출고/발주
├── prescriptions/    # 처방 관리
├── static/           # CSS, JS, 이미지
├── templates/        # 공통 템플릿
├── deploy/           # 서버 설정
├── images/
├── README.md
└── manage.py
```

---

# 🖥 서버 구성

```text
Client
   │
Nginx
   │
Gunicorn
   │
Django
 ├── MariaDB
 ├── NFS(Media)
 └── HIRA Open API
```

---

# 🔐 보안 기능

- Django CSRF 보호
- 환경변수 분리
- Gmail SMTP 이메일 인증
- 비밀번호 재설정
- 점주 승인 시스템
- 권한 기반 접근 제어

---

# ⚙ 운영 기능

- NFS 기반 미디어 저장
- MariaDB 백업
- NFS 백업
- Logrotate
- 환경변수 관리
- GitHub Actions(CI)
- SMTP 메일 발송

---

# 📈 프로젝트 특징

- 실제 운영 환경 기반 서버 구축
- MariaDB 분리 서버
- NFS 기반 파일 저장
- HIRA 공공데이터 API 연동
- Bootstrap 기반 반응형 UI
- Django 인증 시스템 확장
- GitHub 브랜치 협업

---

# 🚀 실행 방법

```bash
python -m venv djangoenv
source djangoenv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

# 📄 운영 문서

```text
deploy/SECURITY_AND_SETUP.md
```

---

# 📜 License

본 프로젝트는 교육 및 팀 프로젝트 목적으로 제작되었습니다.
