# PharmaFlow EKS Manifests

Amazon EKS 환경에서 PharmaFlow를 배포하기 위한 Kubernetes Manifest입니다.

기존 `k8s/` 디렉터리는 로컬 kubeadm 검증 환경이며,
이 디렉터리는 AWS EKS 전용 구성입니다.

로컬 환경과 EKS 환경은 각각 독립적으로 배포할 수 있도록 Namespace를 포함한
Manifest를 환경별로 분리해서 관리합니다.

> [!WARNING]
> `kubectl apply -f k8s/eks/ -R` 방식으로 전체 Manifest를 일괄 적용하지 않습니다.
> Namespace 생성 순서가 보장되지 않으며 `secret.example.yaml`의 예제 값이
> 실제 Secret으로 생성될 수 있습니다.
>
> 반드시 아래 Deployment order에 따라 단계별로 배포하고,
> 실제 Secret은 `secret.example.yaml`을 직접 적용하지 않고 별도로 생성합니다.

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
- `REPLACE-WITH-RDS-USERNAME`
- `REPLACE-WITH-ACM-CERTIFICATE-ARN`

`secret.example.yaml`의 `REPLACE-ME` 값은 실제 Secret 생성 시에만 사용하며
실제 Secret 값은 Git에 커밋하지 않습니다.

## Shared storage

EFS CSI Dynamic Provisioning은 Access Point 기반(`efs-ap`)으로 사용하며,
Django 컨테이너의 실행 UID/GID와 일치하도록 StorageClass에
`uid: 999`, `gid: 999`를 명시합니다.

Django Pod는 `fsGroup: 999`를 사용합니다.

`reclaimPolicy: Retain` 환경에서 PVC를 삭제 후 다시 생성하면
새로운 EFS Access Point가 생성되어 기존 데이터가 앱에서 보이지 않을 수 있으므로,
운영 데이터가 생성된 이후에는 PVC를 임의로 삭제/재생성하지 않습니다.

StorageClass:

- `efs-sc`

PVC:

- `pharmaflow-static`
- `pharmaflow-media`

두 PVC는 ReadWriteMany 방식으로 Django와 Nginx가 공유합니다.

## Deployment order

1. Namespace 생성
2. ConfigMap / 실제 Secret 준비
3. EFS StorageClass 생성
4. Static / Media PVC 생성 및 Bound 확인
5. Django Migration Job 실행 및 Complete 확인
   - Job의 Pod template은 immutable이므로 새 이미지 배포 전에 기존 Migration Job을 삭제합니다.
   - Migration Job을 새 이미지 태그로 생성한 뒤 Complete 상태를 확인합니다.
   - 완료된 Job은 `ttlSecondsAfterFinished: 300`에 의해 자동 정리됩니다.
6. Django Collectstatic Job 실행 및 Complete 확인
   - 공용 `pharmaflow-static` EFS PVC에 정적 파일을 한 번만 생성합니다.
   - Django replicas별 동시 `collectstatic` 실행을 방지하기 위해 Deployment와 분리합니다.
   - 새 이미지 배포 전 기존 Collectstatic Job을 삭제한 뒤 새 이미지 태그로 다시 생성합니다.
   - 완료된 Job은 `ttlSecondsAfterFinished: 300`에 의해 자동 정리됩니다.
7. Django Deployment / Service 배포
8. Nginx Deployment / Service 배포
9. ALB Ingress 배포
10. Health Check 및 E2E 검증

## Migration Job execution

새 이미지 배포 시 기존 Migration Job을 제거한 뒤 다시 생성합니다.

```bash
kubectl delete job \
  pharmaflow-django-migrate \
  -n pharmaflow-dev \
  --ignore-not-found

kubectl apply \
  -f k8s/eks/django/migrate-job.yaml

kubectl wait \
  -n pharmaflow-dev \
  --for=condition=complete \
  job/pharmaflow-django-migrate \
  --timeout=300s
```

Migration Job이 `Complete`된 것을 확인한 뒤 다음 단계로 진행합니다.

Migration Job이 실패한 경우 TTL에 의해 Job/Pod가 정리되기 전에
`kubectl logs`와 `kubectl describe job`을 사용해 실패 원인을 확인합니다.

향후 Argo CD 기반 GitOps로 전환할 경우 Migration Job은
PreSync hook 및 `BeforeHookCreation` 정책으로 자동화하는 방안을 검토합니다.

## Collectstatic Job execution

Migration이 완료된 후 기존 Collectstatic Job을 제거하고 새 이미지 기준으로 다시 생성합니다.

```bash
kubectl delete job \
  pharmaflow-django-collectstatic \
  -n pharmaflow-dev \
  --ignore-not-found

kubectl apply \
  -f k8s/eks/django/collectstatic-job.yaml

kubectl wait \
  -n pharmaflow-dev \
  --for=condition=complete \
  job/pharmaflow-django-collectstatic \
  --timeout=300s
```

Collectstatic Job이 `Complete`된 것을 확인한 뒤 Django Deployment를 진행합니다.

Collectstatic Job이 실패한 경우 TTL에 의해 Job/Pod가 정리되기 전에
`kubectl logs`와 `kubectl describe job`을 사용해 실패 원인을 확인합니다.

향후 Argo CD 기반 GitOps로 전환할 경우 Collectstatic Job도
Migration Job과 동일하게 PreSync hook 및 `BeforeHookCreation` 정책으로
자동화하는 방안을 검토합니다.

## RDS TLS

Amazon RDS MariaDB는 `require_secure_transport=1` 환경을 사용합니다.

Django 이미지에는 AWS RDS global CA bundle을 포함하며,
EKS ConfigMap의 `DB_SSL_CA`를 통해 다음 경로를 Django에 전달합니다.

`/etc/ssl/certs/aws-rds-global-bundle.pem`

Django는 `DB_SSL_CA`가 설정된 경우에만 MariaDB SSL 옵션을 활성화하므로
기존 로컬 MariaDB 환경에서는 TLS 설정 없이 사용할 수 있습니다.

실제 EKS/RDS 연결 단계에서는 TLS 연결 성공 여부뿐 아니라
실제로 적용된 TLS 검증 수준도 확인합니다.

## Health endpoints

- Liveness: `/health/live/`
- Readiness: `/health/ready/`

Django 및 Nginx Kubernetes Probe는 Django `ALLOWED_HOSTS` 검증을 위해
`Host: localhost` 헤더를 사용합니다.

ALB Health Check는 `/health/ready/`를 사용합니다.

Nginx는 `/health/live/`, `/health/ready/` 요청을 Django로 전달할 때
`Host: localhost`를 사용하며, 일반 사용자 요청은 기존 `Host` 값을 유지합니다.

## Validation status

EKS 실제 생성 전 다음 검증을 완료했습니다.

- YAML 문법 및 client-side 파싱 확인
- Kubernetes API server-side dry-run (13/13)
- README Deployment order 기반 단계별 적용 검증
- Secret/Credential 패턴 검사
- 환경별 AWS Account ID / Private IP 하드코딩 검사
- Django/Nginx 공통 PVC 참조 검사
- Django Docker image build
- AWS RDS CA bundle image inclusion
- Django runtime image의 불필요한 `curl` 제거 확인
- Django `manage.py check`
- Django RDS TLS configuration
- Migration Job client/server-side dry-run
- Collectstatic Job client/server-side dry-run
- EFS Access Point UID/GID configuration
- Django Deployment PodSpec server-side 검증
- Namespace 환경별 Manifest 정합성 확인

다음 항목은 실제 EKS 생성 후 검증합니다.

- EFS CSI Dynamic Provisioning
- EFS PVC Binding
- EFS UID/GID 실제 쓰기 권한
- Django Migration Job 실제 Complete
- Django Collectstatic Job 실제 Complete 및 EFS Static 파일 생성
- Amazon RDS TLS 실제 연결 및 TLS 검증 수준 확인
- Multi-AZ Pod 분산
- AWS ALB 생성
- ALB Target Health
- `/health/ready/` 실제 응답
- ALB → Nginx → Django 전체 E2E
- Static/Media EFS 공유
- Pod 장애 및 Self-healing
