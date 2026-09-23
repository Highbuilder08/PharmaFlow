# ==================================================
# 파일 역할: Redis(Django cache framework) 관련 공용 키·헬퍼 모듈
# 관리자 Dashboard 집계 캐시의 조회/저장/무효화를 여기 한 곳에 모아
# core/views.py와 accounts/views.py가 같은 로직을 공유하도록 한다.
# ==================================================

import logging

from django.core.cache import cache
from prometheus_client import Counter

logger = logging.getLogger(__name__)

# 관리자 Dashboard 숫자 집계 캐시 키. 사용자별로 값이 달라지지 않는
# 전역 집계이므로 superuser 전체가 하나의 키를 공유한다.
ADMIN_DASHBOARD_SUMMARY_KEY = "pharmaflow:dashboard:admin:summary"

# 초기 TTL. 이 값 안에는 today_joined_count처럼 "오늘" 기준으로
# 계산되는 값이 있어, 자정을 넘겨도 최대 오차가 이 초 수로 제한된다.
ADMIN_DASHBOARD_SUMMARY_TTL = 60

# result 값은 hit/miss/error 세 가지로 고정한다. 캐시 키 문자열은
# label로 넣지 않는다 - 대상 캐시가 늘어나도 label 카디널리티가
# 늘어나지 않게 하기 위함이다.
DASHBOARD_CACHE_REQUESTS = Counter(
    "pharmaflow_dashboard_cache_requests_total",
    "관리자 Dashboard 캐시 조회 결과(hit/miss/error) 횟수",
    ["result"],
)


def get_admin_dashboard_summary():
    """캐시에서 관리자 Dashboard 집계를 읽는다.

    Redis 연결 실패 등으로 조회가 실패하면 예외를 삼키고 None을 반환해,
    호출 측이 캐시 MISS와 동일하게 RDS 조회 경로로 계속 진행하게 한다.
    """
    try:
        summary = cache.get(ADMIN_DASHBOARD_SUMMARY_KEY)
    except Exception:
        logger.warning(
            "Redis 캐시 조회 실패 - RDS 조회로 진행합니다. key=%s",
            ADMIN_DASHBOARD_SUMMARY_KEY,
            exc_info=True,
        )
        DASHBOARD_CACHE_REQUESTS.labels(result="error").inc()
        return None

    DASHBOARD_CACHE_REQUESTS.labels(
        result="hit" if summary is not None else "miss",
    ).inc()
    return summary


def set_admin_dashboard_summary(summary):
    """관리자 Dashboard 집계를 캐시에 저장한다.

    저장이 실패해도 이미 계산된 summary는 이번 요청의 응답에 그대로
    사용되므로, 여기서 발생하는 예외는 사용자 요청에 영향을 주지 않도록
    로그만 남기고 삼킨다.
    """
    try:
        cache.set(
            ADMIN_DASHBOARD_SUMMARY_KEY,
            summary,
            timeout=ADMIN_DASHBOARD_SUMMARY_TTL,
        )
    except Exception:
        logger.warning(
            "Redis 캐시 저장 실패 - 캐시 없이 계속 진행합니다. key=%s",
            ADMIN_DASHBOARD_SUMMARY_KEY,
            exc_info=True,
        )


def invalidate_admin_dashboard_summary():
    """관리자 Dashboard 집계 캐시를 무효화한다.

    Pharmacy/User/PharmacyOwnershipRequest 변경 후
    transaction.on_commit()으로만 호출해, 트랜잭션이 실제로 커밋된
    뒤에만 캐시가 지워지도록 한다(롤백된 변경 때문에 캐시가 잘못
    지워지는 것을 방지).

    Redis 장애로 삭제가 실패해도 이미 DB 트랜잭션은 커밋된 뒤이므로
    데이터 정합성에는 영향이 없다 - 최악의 경우 다음 TTL 만료까지
    최대 ADMIN_DASHBOARD_SUMMARY_TTL초 동안만 이전 값이 노출된다.
    """
    try:
        cache.delete(ADMIN_DASHBOARD_SUMMARY_KEY)
    except Exception:
        logger.warning(
            "Redis 캐시 무효화 실패 - 다음 TTL 만료까지 이전 값이 남습니다. key=%s",
            ADMIN_DASHBOARD_SUMMARY_KEY,
            exc_info=True,
        )
