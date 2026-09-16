# PharmaFlow EKS Manifests

Amazon EKS 환경에서 PharmaFlow를 배포하기 위한 Kubernetes Manifest입니다.

기존 `k8s/` 디렉터리는 로컬 kubeadm 검증 환경이며,
이 디렉터리는 AWS EKS 전용 구성입니다.

## Architecture

Internet
→ AWS ALB
→ pharmaflow-nginx Service
→ Nginx Pods
→ django Service
→ Django Pods
→ Amazon RDS MariaDB

Django와 Nginx는 Amazon EFS를 통해 Static/Media 데이터를 공유합니다.

## Prerequisites

배포 전에 다음 AWS 인프라가 준비되어 있어야 합니다.

- Amazon EKS Cluster
- EKS Managed Node Group
- Amazon EFS CSI Driver
- EKS Pod Identity Agent
- AWS Load Balancer Controller
- Amazon RDS MariaDB
- Amazon EFS
- Amazon ECR

## Runtime placeholders

실제 배포 전에 다음 값을 환경에 맞게 주입해야 합니다.

- `REPLACE-WITH-DJANGO-ECR-REPOSITORY-URL`
- `REPLACE-WITH-NGINX-ECR-REPOSITORY-URL`
- `REPLACE-WITH-IMAGE-TAG`
- `REPLACE-WITH-EFS-FILE-SYSTEM-ID`
- `REPLACE-WITH-RDS-ENDPOINT`
- `REPLACE-WITH-ALLOWED-HOSTS`

`secret.example.yaml`의 `REPLACE-ME` 값은 실제 Secret 생성 시에만 사용하며
실제 Secret 값은 Git에 커밋하지 않습니다.

## Shared storage

StorageClass:

- `efs-sc`

PVC:

- `pharmaflow-static`
- `pharmaflow-media`

두 PVC는 ReadWriteMany 방식으로 Django와 Nginx가 공유합니다.

## Deployment order

1. Namespace / ConfigMap / Secret 준비
2. EFS StorageClass
3. Static / Media PVC
4. Django Deployment / Service
5. Nginx Deployment / Service
6. ALB Ingress
7. Health Check 및 E2E 검증

## Health endpoints

- Liveness: `/health/live/`
- Readiness: `/health/ready/`

Django 및 Nginx Kubernetes Probe는 Django `ALLOWED_HOSTS` 검증을 위해
`Host: localhost` 헤더를 사용합니다.

ALB Health Check는 `/health/ready/`를 사용합니다.

## Validation status

EKS 실제 생성 전 다음 검증을 완료했습니다.

- YAML client-side dry-run
- Secret/Credential 패턴 검사
- 환경별 AWS Account ID / Private IP 하드코딩 검사
- Django/Nginx 공통 PVC 참조 검사

다음 항목은 실제 EKS 생성 후 검증합니다.

- EFS CSI Dynamic Provisioning
- EFS PVC Binding
- Multi-AZ Pod 분산
- Amazon RDS 연결
- AWS ALB 생성
- ALB → Nginx → Django 전체 E2E
- Pod 장애 및 Self-healing
