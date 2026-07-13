from django.db import models
from django.conf import settings

# Create your models here.
# 4. 복약 상담 게시판 모델
class Consultation(models.Model):
    title = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="내용")
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="작성자")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")
    views = models.PositiveIntegerField(default=0, verbose_name="조회수")

# 5. 복약 상담 게시판 댓글 모델
class ConsultationComment(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='comments')
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="작성자")
    content = models.TextField(verbose_name="댓글 내용")
    created_at = models.DateTimeField(auto_now_add=True)