from django.shortcuts import render

# Create your views here.
# consultations/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Consultation, ConsultationComment
from .forms import ConsultationForm

# 🚨 핵심: consultations 앱에 있는 데코레이터를 빌려옵니다!
from prescriptions.views import login_message_required 

# ==========================================
# 2. 복약 상담 게시판 (Consultation) CRUD
# ==========================================
def consultation_list(request):
    consultations = Consultation.objects.all().order_by('-created_at')
    return render(request, 'consultations/list.html', {'consultations': consultations})

@login_message_required
def consultation_detail(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.method == 'GET':
        consultation.views += 1
        consultation.save()

    if request.method == 'POST':
        comment_content = request.POST.get('content')
        if comment_content:
            ConsultationComment.objects.create(consultation=consultation, writer=request.user, content=comment_content)
            return redirect('consultations:detail', pk=pk)
    return render(request, 'consultations/detail.html', {'consultation': consultation})

@login_message_required
def consultation_create(request):
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.writer = request.user
            consultation.save()
            return redirect('consultations:list')
    else:
        form = ConsultationForm()
    return render(request, 'consultations/create.html', {'form': form})

@login_message_required
def consultation_update(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.user != consultation.writer and not request.user.is_superuser:
        return redirect('consultations:detail', pk=pk)

    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            form.save()
            return redirect('consultations:detail', pk=pk)
    else:
        form = ConsultationForm(instance=consultation)
    return render(request, 'consultations/update.html', {'form': form, 'consultation': consultation})

@login_message_required
def consultation_delete(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.user == consultation.writer or request.user.is_superuser:
        if request.method == 'POST':
            consultation.delete()
            return redirect('consultations:list')
    return redirect('consultations:detail', pk=pk)

@login_message_required
def comment_delete(request, pk):
    comment = get_object_or_404(ConsultationComment, pk=pk)
    consultation_pk = comment.consultation.pk
    if request.user == comment.writer or request.user.is_superuser:
        if request.method == 'POST':
            comment.delete()
    return redirect('consultations:detail', pk=consultation_pk)
