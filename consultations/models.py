import os
from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.
# 4. 복약 상담 게시판 모델
class Consultation(models.Model):
    
    TAG_CHOICES = [
        ('NOTICE', '공지'),
        ('CHAT', '잡담'),
        ('QUESTION', '질문'),
        ('COUNSEL', '상담'),
        ('INFO', '정보'),
    ]
    
    tag = models.CharField(
        max_length=10,
        choices=TAG_CHOICES,
        default='CHAT',
        verbose_name="태그"
    )
    
    title = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="내용")
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="작성자")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    views = models.PositiveIntegerField(default=0, verbose_name="조회수")
    @property
    def smart_date(self):
        if not self.created_at:
            return ""
        
        local_created = timezone.localtime(self.created_at)
        local_now = timezone.localtime(timezone.now())
        
        if local_created.date() == local_now.date():
            return local_created.strftime("%H:%M")
        elif local_created.year == local_now.year:
            return local_created.strftime("%m/%d")
        else:
            return local_created.strftime("%Y/%m/%d")

# 5. 복약 상담 게시판 댓글 모델
class ConsultationComment(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='comments')
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="작성자")
    content = models.TextField(verbose_name="댓글 내용")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
class ConsultationAttachment(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='consultations/%Y/%m/', verbose_name="첨부파일")

    @property
    def filename(self):
        return os.path.basename(self.file.name)