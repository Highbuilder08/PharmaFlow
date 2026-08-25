# ==================================================
# 파일 역할: accounts 앱의 자동 테스트를 작성하는 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

from django.test import TestCase

# Create your tests here.


import json

from django.core import mail
from django.test import override_settings
from django.urls import reverse

from .models import User


# 이메일을 사용하는 기능들이 실제로 메일을 발송하는지 확인한다.
# (테스트 러너는 자동으로 인메모리 백엔드를 사용하므로 실제 발송은 일어나지 않는다)
class EmailSendingTests(TestCase):
    # 회원가입 이메일 인증번호 요청이 인증 메일을 발송하는지 확인한다.
    def test_signup_verification_sends_code_mail(self):
        response = self.client.post(
            reverse("accounts:email_verification_send"),
            data=json.dumps({"email": "new-user@example.com"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("인증번호", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["new-user@example.com"])

    # 비밀번호 재설정 요청(아이디+이메일 일치)이 재설정 메일을 발송하는지 확인한다.
    def test_password_reset_sends_mail(self):
        User.objects.create_user(
            username="reset-user",
            password="StrongPass123!",
            email="reset-user@example.com",
        )
        response = self.client.post(
            reverse("password_reset"),
            data={"username": "reset-user", "email": "reset-user@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["reset-user@example.com"])

    # 발신자 주소가 하드코딩이 아니라 설정(DEFAULT_FROM_EMAIL)을 따르는지 확인한다.
    @override_settings(DEFAULT_FROM_EMAIL="PharmaFlow <noreply@pharmaflow.homes>")
    def test_sender_address_follows_settings(self):
        self.client.post(
            reverse("accounts:email_verification_send"),
            data=json.dumps({"email": "sender-check@example.com"}),
            content_type="application/json",
        )
        self.assertEqual(mail.outbox[0].from_email, "PharmaFlow <noreply@pharmaflow.homes>")
