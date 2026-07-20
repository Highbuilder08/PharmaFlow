# os 모듈: 파일 경로에서 파일 이름만 뽑아낼 때 사용
import os
# models: DB에 저장할 표(테이블) 모양을 파이썬 클래스로 만들 때 사용
from django.db import models
# settings: 우리 프로젝트의 설정값(예: 로그인 계정 모델이 뭔지)을 가져올 때 사용
from django.conf import settings
# timezone: 지금 시각, 시간대 변환 등 날짜/시간 관련 기능
from django.utils import timezone

# Create your models here.
# 4. 복약 상담 게시판 모델
# Consultation = 게시판 글 하나(제목, 내용 등)를 나타내는 표(테이블)
class Consultation(models.Model):

    # 글에 붙일 수 있는 태그 종류 목록
    # 왼쪽은 DB에 실제로 저장되는 값, 오른쪽은 화면에 보여줄 한글 이름
    TAG_CHOICES = [
        ('NOTICE', '공지'),
        ('CHAT', '잡담'),
        ('QUESTION', '질문'),
        ('COUNSEL', '상담'),
        ('INFO', '정보'),
    ]

    # 이 글의 태그 (기본값은 '잡담')
    tag = models.CharField(
        max_length=10,
        choices=TAG_CHOICES,
        default='CHAT',
        verbose_name="태그"
    )

    title = models.CharField(max_length=200, verbose_name="제목")  # 글 제목 (최대 200자)
    content = models.TextField(verbose_name="내용")  # 글 내용 (길이 제한 없음)
    # writer: 이 글을 쓴 사람 (User 모델과 연결, 그 사람이 탈퇴하면 글도 같이 삭제)
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="작성자")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")  # 처음 저장될 때 자동으로 기록되는 작성 시각
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")  # 저장할 때마다 자동으로 갱신되는 수정 시각
    views = models.PositiveIntegerField(default=0, verbose_name="조회수")  # 조회수 (0 이상의 정수만 가능)

    # smart_date: 목록 화면에서 날짜를 상황에 맞게 짧게 보여주기 위한 계산값
    @property
    def smart_date(self):
        if not self.created_at:
            return ""

        # 저장된 시각을 우리 시간대(서버 시간대) 기준으로 변환
        local_created = timezone.localtime(self.created_at)
        local_now = timezone.localtime(timezone.now())

        # 오늘 쓴 글이면 "시:분"만 표시
        if local_created.date() == local_now.date():
            return local_created.strftime("%H:%M")
        # 올해 쓴 글이면 "월/일"만 표시
        elif local_created.year == local_now.year:
            return local_created.strftime("%m/%d")
        # 그 외(작년 이전)에는 "연/월/일" 전체 표시
        else:
            return local_created.strftime("%Y/%m/%d")

# 5. 복약 상담 게시판 댓글 모델
# ConsultationComment = 어떤 글(Consultation)에 달린 댓글 하나를 나타내는 표
class ConsultationComment(models.Model):
    # 이 댓글이 어느 글에 달렸는지 (그 글이 삭제되면 댓글도 같이 삭제)
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='comments')
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="작성자")  # 댓글 쓴 사람
    content = models.TextField(verbose_name="댓글 내용")
    created_at = models.DateTimeField(auto_now_add=True)  # 댓글 작성 시각
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")  # 댓글 수정 시각

# ConsultationAttachment = 글에 첨부된 파일 하나를 나타내는 표
class ConsultationAttachment(models.Model):
    # 이 첨부파일이 어느 글에 속하는지 (그 글이 삭제되면 첨부파일도 같이 삭제)
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='attachments')
    # 실제 파일은 media/consultations/연도/월/ 폴더 밑에 저장됨
    file = models.FileField(upload_to='consultations/%Y/%m/', verbose_name="첨부파일")

    # filename: 저장된 전체 경로에서 파일 이름만 뽑아서 보여주기 위한 계산값
    @property
    def filename(self):
        return os.path.basename(self.file.name)

# AuditLog = "누가 언제 무엇을 삭제/수정했는지" 기록을 남기는 표 (관리자가 확인용)
class AuditLog(models.Model):
    # 작업한 사람 (탈퇴해서 사라져도 기록 자체는 남기고 user 칸만 비움)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="작업자")
    action = models.CharField(max_length=50, verbose_name="작업구분")  # 어떤 작업인지 (예: "게시글 삭제")
    target = models.CharField(max_length=100, verbose_name="작업대상")  # 무엇을 대상으로 했는지 (예: "Consultation #3")
    detail = models.TextField(verbose_name="상세내용 및 사유")  # 상세 내용
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작업시간")  # 작업이 일어난 시각

    class Meta:
        ordering = ['-created_at']  # 최신 기록이 맨 위로 오도록 정렬