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