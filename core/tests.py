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
