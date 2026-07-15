from django.conf import settings
from django.db import models


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

    def __str__(self):
        return f"{self.user.username} - " f"{self.memo_date}"
