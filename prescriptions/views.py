from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Prescription, PrescriptionAttachment, Consultation, ConsultationComment
from .forms import PrescriptionForm, ConsultationForm

# ==========================================
# 1. 처방전 (Prescription) CRUD
# ==========================================
@login_required
def prescription_list(request):
    prescriptions = Prescription.objects.all().order_by('-id')
    return render(request, 'prescriptions/list.html', {'prescriptions': prescriptions})

@login_required
def prescription_detail(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    return render(request, 'prescriptions/detail.html', {'prescription': prescription})

@login_required
def prescription_create(request):
    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.writer = request.user
            prescription.save()
            for f in request.FILES.getlist('attachments'):
                PrescriptionAttachment.objects.create(prescription=prescription, file=f)
            return redirect('prescriptions:list')
    else:
        form = PrescriptionForm()
    return render(request, 'prescriptions/create.html', {'form': form})

@login_required
def prescription_update(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    if request.user != prescription.writer and not request.user.is_superuser:
        return redirect('prescriptions:detail', pk=pk)

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES, instance=prescription)
        if form.is_valid():
            form.save()
            for f in request.FILES.getlist('attachments'):
                PrescriptionAttachment.objects.create(prescription=prescription, file=f)
            return redirect('prescriptions:detail', pk=pk)
    else:
        form = PrescriptionForm(instance=prescription)
    return render(request, 'prescriptions/update.html', {'form': form, 'prescription': prescription})

@login_required
def prescription_delete(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    if request.user == prescription.writer or request.user.is_superuser:
        if request.method == 'POST':
            prescription.delete()
            return redirect('prescriptions:list')
    return redirect('prescriptions:detail', pk=pk)

@login_required
def attachment_delete(request, pk):
    attachment = get_object_or_404(PrescriptionAttachment, pk=pk)
    prescription_pk = attachment.prescription.pk
    if request.user == attachment.prescription.writer or request.user.is_superuser:
        if request.method == 'POST':
            attachment.delete()
    return redirect('prescriptions:detail', pk=prescription_pk)


# ==========================================
# 2. 복약 상담 게시판 (Consultation) CRUD
# ==========================================
@login_required
def consultation_list(request):
    consultations = Consultation.objects.all().order_by('-created_at')
    return render(request, 'consultation/list.html', {'consultations': consultations})

@login_required
def consultation_detail(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.method == 'GET':
        consultation.views += 1
        consultation.save()

    if request.method == 'POST':
        comment_content = request.POST.get('content')
        if comment_content:
            ConsultationComment.objects.create(consultation=consultation, writer=request.user, content=comment_content)
            return redirect('prescriptions:consultation_detail', pk=pk)
    return render(request, 'consultation/detail.html', {'consultation': consultation})

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
    return render(request, 'consultation/create.html', {'form': form})

@login_required
def consultation_update(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.user != consultation.writer and not request.user.is_superuser:
        return redirect('prescriptions:consultation_detail', pk=pk)

    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            form.save()
            return redirect('prescriptions:consultation_detail', pk=pk)
    else:
        form = ConsultationForm(instance=consultation)
    return render(request, 'consultation/update.html', {'form': form, 'consultation': consultation})

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
    consultation_pk = comment.consultation.pk
    if request.user == comment.writer or request.user.is_superuser:
        if request.method == 'POST':
            comment.delete()
    return redirect('prescriptions:consultation_detail', pk=consultation_pk)