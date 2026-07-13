from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages  # 👈 메시지 띄우기용
from functools import wraps          # 👈 데코레이터 만들기용
from .models import Prescription, PrescriptionAttachment, PrescriptionItem, AuditLog
from inventory.models import Medicine, InventoryTransaction # 약국 재고 가져오기
from django.forms import inlineformset_factory 
from .forms import PrescriptionForm, PrescriptionItemForm 

def login_message_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 만약 로그인하지 않은 사용자라면?
        if not request.user.is_authenticated:
            # 경고 메시지를 담아두고
            messages.warning(request, '로그인 전엔 글 목록만 확인 가능합니다.')
            
            if 'consultation' in request.path:
                return redirect('consultations:list') 
            else:
                return redirect('prescriptions:list')
                
        return view_func(request, *args, **kwargs)
    return wrapper

# ==========================================
# 1. 처방전 (Prescription) CRUD
# ==========================================
def prescription_list(request):
    prescriptions = Prescription.objects.all().order_by('-id')
    return render(request, 'prescriptions/list.html', {'prescriptions': prescriptions})

@login_message_required
def prescription_detail(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    return render(request, 'prescriptions/detail.html', {'prescription': prescription})

@login_message_required
def prescription_create(request):
    # 🌟 부모(처방전)와 자식(약품) 폼을 하나로 묶어주는 마법의 폼셋!
    ItemFormSet = inlineformset_factory(
        Prescription, 
        PrescriptionItem, 
        form=PrescriptionItemForm, 
        extra=1, # 처방할 때 기본으로 보여줄 약품 입력 칸 개수
        can_delete=False
    )

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES)
        formset = ItemFormSet(request.POST) # 폼셋 데이터도 같이 받음
        
        if form.is_valid() and formset.is_valid():
            # 1. 처방전 먼저 임시 저장 (ID 생성)
            prescription = form.save(commit=False)
            prescription.writer = request.user
            prescription.save()
            
            # 2. 첨부파일 저장
            for f in request.FILES.getlist('attachments'):
                PrescriptionAttachment.objects.create(prescription=prescription, file=f)
            
            # 3. 폼셋(약품) 저장 및 재고 연동
            formset.instance = prescription # 약품들에 처방전 ID를 싹 연결해줌
            items = formset.save(commit=False)
            for item in items:
                item.save() # 개별 약품 저장
                
                # 🚀 개발자 2님의 DB에 재고 차감 및 출고 기록 남기기
                medicine = item.medicine
                medicine.stock -= item.total_quantity
                medicine.save()
                
                InventoryTransaction.objects.create(
                    medicine=medicine,
                    transaction_type='OUT',
                    quantity=item.total_quantity
                )
                
            return redirect('prescriptions:detail', pk=prescription.id)
    else:
        form = PrescriptionForm()
        formset = ItemFormSet()
        
    return render(request, 'prescriptions/create.html', {
        'form': form, 
        'formset': formset
    })

@login_message_required
def prescription_update(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    
    # 권한 체크
    if request.user != prescription.writer and not request.user.is_superuser:
        return redirect('prescriptions:detail', pk=pk)

    # 🌟 부모(처방전)와 자식(약품)을 묶어주는 폼셋 생성
    ItemFormSet = inlineformset_factory(
        Prescription, 
        PrescriptionItem, 
        form=PrescriptionItemForm, 
        extra=1, # 수정 창에도 빈칸 1개를 띄워 약을 추가할 수 있게 함
        can_delete=False # 복잡한 재고 꼬임을 막기 위해 삭제는 일단 비활성화
    )

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES, instance=prescription)
        formset = ItemFormSet(request.POST, instance=prescription)

        if form.is_valid() and formset.is_valid():
            form.save() # 환자 정보 수정 저장
            
            # 첨부파일 추가 저장
            for f in request.FILES.getlist('attachments'):
                PrescriptionAttachment.objects.create(prescription=prescription, file=f)
            
            # 약품 정보 저장 및 재고 차감 로직
            items = formset.save(commit=False)
            for item in items:
                # 🚀 핵심: '수정' 창이므로, 기존 약의 재고가 또 깎이지 않게 "새로 추가된 약"인지 확인!
                is_new = item.pk is None 
                item.save()
                
                if is_new:
                    medicine = item.medicine
                    medicine.stock -= item.total_quantity
                    medicine.save()
                    
                    InventoryTransaction.objects.create(
                        medicine=medicine,
                        transaction_type='OUT',
                        quantity=item.total_quantity
                    )
            return redirect('prescriptions:detail', pk=pk)
    else:
        form = PrescriptionForm(instance=prescription)
        formset = ItemFormSet(instance=prescription)

    # 💡 화면에 '재고 없음' 문구를 띄우기 위해 재고가 있는지 미리 검사
    has_stock = Medicine.objects.filter(stock__gt=0).exists()

    return render(request, 'prescriptions/update.html', {
        'form': form, 
        'formset': formset, 
        'prescription': prescription,
        'has_stock': has_stock # HTML로 검사 결과 전달
    })

@login_message_required
def prescription_delete(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    if request.user == prescription.writer or request.user.is_superuser:
        if request.method == 'POST':
            prescription.delete()
            return redirect('prescriptions:list')
    return redirect('prescriptions:detail', pk=pk)

@login_message_required
def attachment_delete(request, pk):
    attachment = get_object_or_404(PrescriptionAttachment, pk=pk)
    prescription_pk = attachment.prescription.pk
    if request.user == attachment.prescription.writer or request.user.is_superuser:
        if request.method == 'POST':
            attachment.delete()
    return redirect('prescriptions:detail', pk=prescription_pk)

@login_message_required
def prescription_item_delete(request, pk):
    item = get_object_or_404(PrescriptionItem, pk=pk)
    prescription_pk = item.prescription.pk
    
    if request.user == item.prescription.writer or request.user.is_superuser:
        if request.method == 'POST':
            # 🚀 1. HTML에서 날아온 삭제 사유 받기
            delete_reason = request.POST.get('delete_reason', '').strip()
            
            # 백엔드 2차 검증: 사유가 비어있으면 에러 띄우고 삭제 중단
            if not delete_reason:
                messages.warning(request, "삭제 사유를 반드시 입력해야 합니다.")
                return redirect('prescriptions:detail', pk=prescription_pk)
            
            medicine = item.medicine
            medicine.stock += item.total_quantity
            medicine.save()
            
            InventoryTransaction.objects.create(
                medicine=medicine,
                transaction_type='IN',
                quantity=item.total_quantity
            )
            
            # 🚀 2. 관리자용 로그에 삭제 기록 및 사유 남기기
            AuditLog.objects.create(
                user=request.user,
                action='삭제',
                target='처방 약품',
                detail=f"[{prescription_pk}번 처방전] 약품 '{medicine.name}' 삭제. (사유: {delete_reason})"
            )
            
            item.delete()
            messages.success(request, "약품이 삭제되고 재고가 복구되었습니다.")
            
    return redirect('prescriptions:update', pk=prescription_pk)

@login_message_required
def audit_log_list(request):
    # 관리자(superuser)가 아니면 접근 차단
    if not request.user.is_superuser:
        messages.warning(request, "관리자만 접근 가능한 페이지입니다.")
        return redirect('prescriptions:list')
    
    logs = AuditLog.objects.all()
    return render(request, 'prescriptions/audit_logs.html', {'logs': logs})