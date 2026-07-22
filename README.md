<p align="center">
<img src="./images/logo.png" width="220" alt="PharmaFlow Logo">
</p>

<h1 align="center">PharmaFlow</h1>

<p align="center">💊 약국 통합 관리 시스템</p>

<p align="center">Django · MariaDB · Nginx · Gunicorn · NFS</p>

---

# 📌 프로젝트 소개

**PharmaFlow**는 약국 업무를 효율적으로 관리하기 위한 웹 기반 약국 통합 관리 시스템입니다.

회원 관리와 약국 관리부터 의약품 재고, 입출고, 발주, 자유 게시판,
일정 관리까지 하나의 시스템에서 수행할 수 있도록 설계되었습니다.

또한 HIRA Open API, Gmail SMTP, Leaflet 지도, MariaDB, NFS,
Gunicorn, Nginx를 연동하여 실제 운영 환경을 고려한 프로젝트입니다.

---

# ✨ 주요 기능

- 회원가입 / 로그인
- 이메일 인증
- 비밀번호 찾기
- HIRA API 약국 검색
- 약국 관리
- 직원 관리
- 의약품·재고·입출고·발주 관리
- 자유 게시판
- 첨부파일 업로드 및 다운로드
- 일정 관리
- Audit Log

---

# 📷 주요 화면

## 🏠 메인 대시보드

<p align="center"><img src="./images/dashboard.png" width="100%"></p>

---

## 💊 의약품 재고 관리

<p align="center"><img src="./images/inventory.png" width="100%"></p>

---

## 📦 입출고 관리

<p align="center"><img src="./images/transactions.png" width="100%"></p>

---

## 💬 자유 게시판

<p align="center"><img src="./images/board.png" width="100%"></p>

---

## 👤 점주 회원가입

<p align="center"><img src="./images/owner_signup.png" width="70%"></p>

---

# 🛠 기술 스택

- Python 3.12
- Django
- Bootstrap 5
- JavaScript
- MariaDB
- Nginx
- Gunicorn
- NFS
- Leaflet
- OpenStreetMap
- HIRA Open API
- Git / GitHub / GitHub Actions

---

# 🔐 보안 기능

- Django CSRF 보호
- 환경변수 분리
- Gmail SMTP 이메일 인증
- 비밀번호 재설정
- 권한 기반 접근 제어

---

# 📈 프로젝트 특징

- 실제 운영 환경 기반 서버 구축
- MariaDB 분리 서버
- NFS 기반 파일 저장
- HIRA 공공데이터 API 연동
- Bootstrap 기반 반응형 UI
- GitHub 브랜치 협업

---

# 📚 Data Source

- 약국 정보 조회 기능은 건강보험심사평가원(HIRA) Open API를 활용하였습니다.
- 공공데이터포털(Open API)를 통해 제공되는 건강보험심사평가원 약국 정보를 사용하였습니다.

---

# 📜 License

본 프로젝트는 교육 및 학습을 위한 팀 프로젝트로 제작되었습니다.
상업적 이용을 목적으로 하지 않습니다.

---

# 👥 Team

- 고건희
- 서보성
- 홍성빈

---

## 📚 Project Purpose

본 프로젝트는 Django 기반 웹 개발, 서버 구축, 데이터베이스 연동,
파일 공유(NFS), 웹 서버(Nginx), 애플리케이션 서버(Gunicorn),
GitHub 협업 및 실제 운영 환경 구성을 학습하기 위한 팀 프로젝트입니다.
