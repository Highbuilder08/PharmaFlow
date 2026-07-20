# ==================================================
# 파일 역할: 사용자별 달력 메모 데이터를 정의하는 모델 모듈
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

from django.conf import settings
from django.db import models


# 사용자별로 특정 날짜에 작성한 달력 메모를 저장한다.
class CalendarMemo(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_memos",
        verbose_name="작성자",
    )

    memo_date = models.DateField(
        verbose_name="메모 날짜",
    )

    content = models.TextField(
        blank=True,
        verbose_name="메모 내용",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="작성일시",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시",
    )

    # Meta 클래스의 데이터 구조와 동작을 정의한다.
    class Meta:
        db_table = "calendar_memo"

        ordering = [
            "memo_date",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "memo_date",
                ],
                name="unique_calendar_memo_per_user_date",
            ),
        ]

        verbose_name = "달력 메모"
        verbose_name_plural = "달력 메모"

    # 관리자 화면과 로그에서 객체를 알아보기 쉬운 문자열로 표시한다.
    def __str__(self):
        return f"{self.user.username} - " f"{self.memo_date}"
