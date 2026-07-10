from django.db import models
from django.conf import settings

# 1. 처방전 모델
class Prescription(models.fields):
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="작성자")
    patient_name = models.CharField(max_length=50, verbose_name="환자명")
    ssn_front = models.CharField(max_length=6, verbose_name="주민번호(앞자리)")
    phone = models.CharField(max_length=20, verbose_name="연락처")
    symptoms = models.TextField(verbose_name="증상")
    prescription_date = models.DateField(verbose_name="처방일")
    # pharmacy = models.ForeignKey('accounts.Pharmacy', ...) # 약국 모델 연결 (개발자1과 협의)

# 2. 처방전 약품 목록 (1:N 관계)
class PrescriptionItem(models.models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine_name = models.CharField(max_length=100, verbose_name="약품명(예: 타이레놀)")
    dosage = models.CharField(max_length=50, verbose_name="복용법(예: 1일 3회)")
    duration = models.CharField(max_length=50, verbose_name="복용기간(예: 5일)")

# 3. 처방전 첨부파일 (NFS 서버에 저장될 부분)
class PrescriptionAttachment(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='attachments')
    # upload_to를 설정하면 자동으로 연/월 폴더를 만들어 NFS(MEDIA_ROOT)에 저장됩니다.
    file = models.FileField(upload_to='prescriptions/%Y/%m/', verbose_name="첨부파일")

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