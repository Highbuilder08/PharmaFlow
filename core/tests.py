# ==================================================
# 파일 역할: 달력 메모 기능의 자동 테스트를 정의하는 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User


# 달력 메모 API의 유효성 검사와 저장 동작을 확인한다.
class CalendarMemoTests(TestCase):
    # 각 테스트 실행 전에 로그인된 테스트 사용자를 준비한다.
    def setUp(self):
        self.user = User.objects.create_user(username="memo-user", password="StrongPass123!")
        self.client.force_login(self.user)

    # 허용 범위를 벗어난 연도를 요청하면 400 응답인지 확인한다.
    def test_invalid_year_is_rejected(self):
        response = self.client.get(reverse("core:calendar_memo_dates"), {"year": "9999", "month": "1"})
        self.assertEqual(response.status_code, 400)

    # 정상 메모 저장 요청이 성공하는지 확인한다.
    def test_memo_save(self):
        response = self.client.post(
            reverse("core:calendar_memo_save"),
            data=json.dumps({"date": "2026-07-16", "content": "메모"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])


# ALB Health Check 엔드포인트의 응답 규격을 확인한다.
class HealthCheckTests(TestCase):
    # 로그인 없이 GET 요청이 200과 healthy 상태를 반환하는지 확인한다.
    # (ALB는 인증 정보 없이 호출하므로 setUp 로그인 없이 요청한다)
    def test_health_returns_200_without_auth(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    # DB 연결이 끊어진 상황에서 503과 unhealthy 상태를 반환하는지 확인한다.
    def test_health_returns_503_when_db_is_down(self):
        from unittest import mock

        from django.db import DatabaseError

        with mock.patch(
            "core.views.connection.cursor",
            side_effect=DatabaseError("connection refused"),
        ):
            response = self.client.get(reverse("core:health"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unhealthy")

    # GET 외의 메서드가 뷰 수준에서 405로 거부되는지 확인한다.
    # (운영에서는 CSRF 미들웨어가 그보다 먼저 403으로 차단한다. 어느 쪽이든 거부된다)
    def test_health_rejects_post(self):
        response = self.client.post(reverse("core:health"))
        self.assertEqual(response.status_code, 405)


# liveness/readiness 분리 후 각 엔드포인트의 역할을 확인한다.
class LivenessReadinessTests(TestCase):
    # liveness가 로그인 없이 200을 반환하고, 이때 DB 쿼리가 0건인지 확인한다.
    def test_live_returns_200_without_any_db_query(self):
        with self.assertNumQueries(0):
            response = self.client.get(reverse("core:health_live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "alive")

    # DB가 죽어도 liveness는 200인지 확인한다. (ASG 교체 루프 방지의 핵심 성질)
    def test_live_returns_200_even_when_db_is_down(self):
        from unittest import mock

        from django.db import DatabaseError

        with mock.patch(
            "core.views.connection.cursor",
            side_effect=DatabaseError("connection refused"),
        ):
            response = self.client.get(reverse("core:health_live"))

        self.assertEqual(response.status_code, 200)

    # readiness가 로그인 없이 200과 healthy 상태를 반환하는지 확인한다.
    def test_ready_returns_200_without_auth(self):
        response = self.client.get(reverse("core:health_ready"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    # DB 연결이 끊어지면 readiness만 503이 되는지 확인한다.
    def test_ready_returns_503_when_db_is_down(self):
        from unittest import mock

        from django.db import DatabaseError

        with mock.patch(
            "core.views.connection.cursor",
            side_effect=DatabaseError("connection refused"),
        ):
            response = self.client.get(reverse("core:health_ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unhealthy")
