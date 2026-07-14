import os
from django.db import models
from django.conf import settings
from inventory.models import Medicine, InventoryTransaction 
from django.utils import timezone

# 1. 처방전 모델
class Prescription(models.Model):
    pharmacy = models.ForeignKey('accounts.Pharmacy', on_delete=models.CASCADE, verbose_name="지정 약국", null=True)
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="작성자")
    patient_name = models.CharField(max_length=50, verbose_name="환자명")
    ssn_front = models.CharField(max_length=6, verbose_name="주민번호(앞자리)")
    phone = models.CharField(max_length=20, verbose_name="연락처")
    symptoms = models.TextField(verbose_name="증상")
    prescription_date = models.DateField(verbose_name="처방일")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일", null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    @property
    def smart_date(self):
        if not self.created_at:
            return ""
        
        local_created = timezone.localtime(self.created_at)
        local_now = timezone.localtime(timezone.now())
        
        if local_created.date() == local_now.date():
            return local_created.strftime("%H:%M") # 오늘이면 시간만 (예: 14:30)
        elif local_created.year == local_now.year:
            return local_created.strftime("%m/%d") # 올해면 월/일 (예: 07/13)
        else:
            return local_created.strftime("%Y/%m/%d") # 해가 지났으면 년/월/일 (예: 2025/12/25)

# 2. 처방전 약품 목록 (1:N 관계)
class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, verbose_name="처방 약품", null=True)
    
    dosage = models.CharField(max_length=50, verbose_name="복용법(예: 1일 3회)")
    duration = models.CharField(max_length=50, verbose_name="복용기간(예: 5일)")
    total_quantity = models.PositiveIntegerField(verbose_name="총 처방 수량(알/포)", default=1)

class PrescriptionAttachment(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='prescriptions/%Y/%m/', verbose_name="첨부파일")
    @property
    def filename(self):
        return os.path.basename(self.file.name)
    
class AuditLog(models.Model):
    # 누가(사용자), 어떤 작업을(등록/수정/삭제), 어떤 대상에게(처방전/게시판), 상세내용은 무엇인지 기록합니다.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="작업자")
    action = models.CharField(max_length=50, verbose_name="작업구분")
    target = models.CharField(max_length=100, verbose_name="작업대상")
    detail = models.TextField(verbose_name="상세내용 및 사유")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작업시간")

    class Meta:
        ordering = ['-created_at'] # 최신 로그가 가장 위에 오도록 정렬