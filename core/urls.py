# ==================================================
# 파일 역할: core 앱의 화면과 달력 메모 API URL을 연결하는 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

from django.urls import path

from . import views

app_name = "core"


urlpatterns = [
    path(
        "",
        views.index,
        name="index",
    ),
    path(
        "calendar/memo/",
        views.calendar_memo_detail,
        name="calendar_memo_detail",
    ),
    path(
        "calendar/memo/save/",
        views.calendar_memo_save,
        name="calendar_memo_save",
    ),
    path(
        "calendar/memo/dates/",
        views.calendar_memo_dates,
        name="calendar_memo_dates",
    ),
    path(
        "health/live/",
        views.health_live,
        name="health_live",
    ),
    path(
        "health/ready/",
        views.health_ready,
        name="health_ready",
    ),
    # PR #78로 먼저 배포된 경로. readiness의 별칭으로 유지한다.
    path(
        "health/",
        views.health_ready,
        name="health",
    ),
]
