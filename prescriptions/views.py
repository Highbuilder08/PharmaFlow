# prescriptions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Prescription, PrescriptionAttachment, Consultation, ConsultationComment
from .forms import PrescriptionForm, ConsultationForm

# ==========================================
# 1. 처방전 (Prescription) 뷰
# ==========================================

@login_required
def prescription_list(request):
    prescriptions = Prescription.objects.all().order_by('-id')
    # 경로 변경: prescriptions/prescription_list.html
    return render(request, 'prescriptions/prescription_list.html', {'prescriptions': prescriptions})

@login_required
def prescription_detail(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    # 경로 변경: prescriptions/prescription_detail.html
    return render(request, 'prescriptions/prescription_detail.html', {'prescription': prescription})

@login_required
def prescription_create(request):
    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.writer = request.user
            prescription.save()

            files = request.FILES.getlist('attachments')
            for f in files:
                PrescriptionAttachment.objects.create(prescription=prescription, file=f)
            
            return redirect('prescriptions:list')
    else:
        form = PrescriptionForm()
    
    # 경로 변경: prescriptions/prescription_create.html
    return render(request, 'prescriptions/prescription_create.html', {'form': form})


# ==========================================
# 2. 복약 상담 게시판 (Consultation) 뷰
# ==========================================

@login_required
def consultation_list(request):
    consultations = Consultation.objects.all().order_by('-created_at')
    # 경로 변경: prescriptions/consultation_list.html
    return render(request, 'prescriptions/consultation_list.html', {'consultations': consultations})

@login_required
def consultation_detail(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    
    consultation.views += 1
    consultation.save()

    if request.method == 'POST':
        comment_content = request.POST.get('content')
        if comment_content:
            ConsultationComment.objects.create(
                consultation=consultation,
                writer=request.user,
                content=comment_content
            )
            return redirect('prescriptions:consultation_detail', pk=pk)

    # 경로 변경: prescriptions/consultation_detail.html
    return render(request, 'prescriptions/consultation_detail.html', {'consultation': consultation})

@login_required
def consultation_create(request):
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.writer = request.user
            consultation.save()
            return redirect('prescriptions:consultation_list')
    else:
        form = ConsultationForm()
    
    # 경로 변경: prescriptions/consultation_create.html
    return render(request, 'prescriptions/consultation_create.html', {'form': form})

# ==========================================
# 3. 삭제 (Delete) 뷰
# ==========================================

@login_required
def prescription_delete(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    
    # 권한 체크: 작성자 본인이거나 관리자만 삭제 가능
    if request.user == prescription.writer or request.user.is_superuser:
        if request.method == 'POST':
            prescription.delete()
            return redirect('prescriptions:list')
            
    # 권한이 없거나 GET 요청인 경우 상세 페이지로 돌려보냄
    return redirect('prescriptions:detail', pk=pk)

@login_required
def consultation_delete(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    
    if request.user == consultation.writer or request.user.is_superuser:
        if request.method == 'POST':
            consultation.delete()
            return redirect('prescriptions:consultation_list')
            
    return redirect('prescriptions:consultation_detail', pk=pk)

@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(ConsultationComment, pk=pk)
    consultation_pk = comment.consultation.pk # 돌아갈 게시글 번호 미리 저장
    
    if request.user == comment.writer or request.user.is_superuser:
        if request.method == 'POST':
            comment.delete()
            
    # 댓글 삭제 후 원래 있던 게시글 상세 화면으로 돌아감
    return redirect('prescriptions:consultation_detail', pk=consultation_pk)