# Django Kubernetes 설계 (EKS 전환 타깃)

> 이 디렉터리(`k8s/django/`) + `k8s/base/configmap.yaml`, `k8s/base/secret.example.yaml`는
> Django 담당이 관리합니다. `k8s/nginx/`, `k8s/mariadb/`, `k8s/ingress/`, `k8s/base/namespace.yaml`은
> 건드리지 않았습니다.

## 저장소 이동 경위

원래 `PharmaFlow-Infrastructure` 저장소의 `feature/k8s-django-design` 브랜치에서 별도로
설계하던 내용이었는데, `main`(`bdfb342 Add local Kubernetes deployment manifests`)에
이미 로컬 kubeadm으로 검증된 실제 구조(`k8s/base`/`k8s/django`/`k8s/nginx`/`k8s/mariadb`/
`k8s/ingress`)가 있는 걸 뒤늦게 확인했습니다. 두 버전이 상당 부분 동일했습니다
(`runAsUser: 999`, `initContainer` chown, Probe `Host: localhost` 등 — 로컬 kind
검증 중 겪은 문제와 고친 방식이 사실상 같았습니다). 팀장 요청으로 Kubernetes manifest
관리 위치를 이 저장소로 통일하면서, 기존 `main`의 로컬 검증 버전 위에 Infrastructure
저장소에서 만든 **EKS 전환 타깃** 값(RDS/PVC/zone)을 다시 얹었습니다.

## `main`(로컬 검증) 대비 이 브랜치에서 바뀐 것

| 항목 | `main` (로컬 kubeadm 검증) | 이 브랜치 (EKS 전환 타깃) |
|---|---|---|
| DB | in-cluster `mariadb`(`k8s/mariadb/`) | AWS RDS (`k8s/base/configmap.yaml`의 `DB_HOST`, 플레이스홀더) |
| Static/Media volume | `emptyDir` | `persistentVolumeClaim` → `pvc.yaml`(EFS CSI, RWX) — 신규 파일 |
| `topologySpreadConstraints.topologyKey` | `kubernetes.io/hostname` | `topology.kubernetes.io/zone` |
| `EMAIL_BACKEND` | console(로컬 발송 안 함) | SMTP(SES) |
| `MARIADB_ROOT_PASSWORD`(Secret) | 있음(in-cluster mariadb 초기화용) | 제거 (RDS 전환 시 불필요) |

**바뀌지 않은 것** (지시대로 그대로 유지): `django` Deployment/Service 이름·포트,
`imagePullSecrets: ecr-registry-secret`, `runAsUser: 999`, `initContainer` volume-init,
Probe `Host: localhost`, `envFrom`(`pharmaflow-config`/`pharmaflow-secret`), replicas=2,
ECR 이미지 플레이스홀더(`REPLACE-WITH-ECR-REGISTRY/pharmaflow-django:REPLACE-WITH-IMAGE-TAG`
— `sha-<commit>` 태그 전략은 팀장 통합 단계에서 실제 값 채움).

## PVC 이름을 `django-*`가 아니라 `pharmaflow-*`로 지은 이유

Static/Media는 Django와 Nginx가 같은 파일을 봐야 합니다(Nginx가 `/static/`, `/media/`를
직접 서빙). `pvc.yaml`의 `pharmaflow-static`/`pharmaflow-media`를 Nginx Deployment도
그대로 마운트해야 하며, Nginx 쪽에서 별도 PVC를 새로 만들면 EFS 동적 프로비저닝
특성상 서로 다른 디렉터리가 생겨 파일 공유가 깨집니다. Nginx 담당의 EKS 전환
작업(`emptyDir` → EFS CSI PVC) 때 이 점을 공유해야 합니다.

팀장 지시(수정본, 2026-09-16): 이 PVC는 최종적으로 공통 Storage 영역에서 한 번만
관리할 예정이라 `pvc.yaml` 자체는 통합 단계에서 제거될 수 있습니다. 그때까지는
Django Deployment가 `pharmaflow-static`/`pharmaflow-media`라는 이름을 그대로
참조하도록 여기서 정의해둔 상태입니다.

## 로컬 kind 실검증에서 발견하고 고친 문제 2건 (Infrastructure 저장소 단계에서 확인, 참고용)

**1) 컨테이너가 아예 안 뜸**
- 증상: `Error: container has runAsNonRoot and image has non-numeric user (django), cannot verify user is non-root`
- 원인: pod의 `securityContext.runAsNonRoot: true`와 Dockerfile의 `USER django`(이름, 숫자 아님)가 만나면
  kubelet이 실제 uid를 확인할 방법이 없어서 컨테이너 시작 자체를 거부합니다.
- 수정: django 컨테이너에 `securityContext.runAsUser: 999`를 명시.

**2) 컨테이너는 뜨는데 Readiness/Liveness가 계속 실패**
- 증상: `django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: '10.244.0.9:8000'` → probe 요청이 400
- 원인: kubelet이 probe를 pod IP로 직접 보내는데, 그 IP가 그대로 HTTP Host 헤더로 들어가서
  Django `ALLOWED_HOSTS` 검증에 걸림 (예전 ALB 헬스체크 때 `django_allowed_hosts: ["*"]`로
  우회했던 것과 같은 원인).
- 수정: `ALLOWED_HOSTS`를 통째로 여는 대신, probe의 `httpGet.httpHeaders`에 고정
  `Host: localhost`를 넣고 `ConfigMap`의 `DJANGO_ALLOWED_HOSTS`에 `localhost`만 추가.

## 검증 범위

이 브랜치 내용은 스키마 레벨(`kubectl apply --dry-run=server`)과 로컬 `kind`
라이브 테스트(`DB_ENGINE=sqlite3`로 RDS 대체)까지만 확인했습니다. **실제 EKS 배포나
AWS 리소스 생성은 하지 않았습니다.** EFS CSI 실바인딩과 실제 zone 기반 분산은
EKS 클러스터가 있어야 확인 가능합니다.

## 남은 확인 필요 항목

- **StorageClass 이름**: EFS CSI 애드온 설정 후 `pvc.yaml`의 `efs-sc` 플레이스홀더를 실제 이름으로 교체
- **Secret 관리 방식**: 지금은 평범한 K8s `Secret`(템플릿만 커밋, 실제 값은 `kubectl apply`로 직접 주입).
  Sealed Secrets나 External Secrets Operator로 바꿀지는 팀 결정 필요
- **`k8s/mariadb/` 처리**: RDS로 전환하면 이 디렉터리는 더 이상 필요 없어 보이는데, 로컬 검증용으로
  계속 남겨둘지 팀 결정 필요 (이번 작업에서는 건드리지 않았음)
- **Infrastructure 저장소의 `feature/k8s-django-design` 브랜치**: 팀장이 원격에서 확인 후 직접 삭제 예정
