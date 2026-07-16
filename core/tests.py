import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class CalendarMemoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="memo-user", password="StrongPass123!")
        self.client.force_login(self.user)

    def test_invalid_year_is_rejected(self):
        response = self.client.get(reverse("core:calendar_memo_dates"), {"year": "9999", "month": "1"})
        self.assertEqual(response.status_code, 400)

    def test_memo_save(self):
        response = self.client.post(
            reverse("core:calendar_memo_save"),
            data=json.dumps({"date": "2026-07-16", "content": "메모"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
