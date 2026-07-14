from django.shortcuts import render

# Create your views here.
# consultations/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Consultation, ConsultationComment, ConsultationAttachment
from .forms import ConsultationForm
from django.db.models import Q

# 🚨 핵심: consultations 앱에 있는 데코레이터를 빌려옵니다!
from prescriptions.views import login_message_required 

# ==========================================
# 2. 복약 상담 게시판 (Consultation) CRUD
# ==========================================
def consultation_list(request):
    search_type = request.GET.get('search_type', '')
    q = request.GET.get('q', '')

    # 🚀 공지와 일반글을 완벽하게 분리하여 정렬합니다.
    # 공지: 'created_at' (오름차순 - 옛날 글이 위로, 나중 글이 아래로)
    notices = Consultation.objects.filter(tag='NOTICE').order_by('created_at')
    # 일반글: '-created_at' (내림차순 - 최신 글이 위로)
    normal_posts = Consultation.objects.exclude(tag='NOTICE').order_by('-created_at')

    # 검색어가 있는 경우 두 묶음 모두에게 검색 적용
    if q:
        if search_type == 'title':
            notices = notices.filter(title__icontains=q)
            normal_posts = normal_posts.filter(title__icontains=q)
        elif search_type == 'writer':
            notices = notices.filter(writer__username__icontains=q)
            normal_posts = normal_posts.filter(writer__username__icontains=q)
        else: # 전체
            notices = notices.filter(Q(title__icontains=q) | Q(writer__username__icontains=q))
            normal_posts = normal_posts.filter(Q(title__icontains=q) | Q(writer__username__icontains=q))

    # 🚀 두 개의 정렬된 리스트를 하나로 합쳐서 공지가 무조건 맨 위에 오도록 만듭니다!
    consultations = list(notices) + list(normal_posts)

    return render(request, 'consultations/list.html', {
        'consultations': consultations,
        'q': q,
        'search_type': search_type
    })
    
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
        # 👇 user=request.user 추가
        form = ConsultationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.writer = request.user
            consultation.save()
            for f in request.FILES.getlist('attachments'):
                ConsultationAttachment.objects.create(consultation=consultation, file=f)
            return redirect('consultations:list')
    else:
        # 👇 user=request.user 추가
        form = ConsultationForm(user=request.user)
    return render(request, 'consultations/create.html', {'form': form})

@login_message_required
def consultation_update(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.user != consultation.writer and not request.user.is_superuser:
        return redirect('consultations:detail', pk=pk)

    if request.method == 'POST':
        # 👇 user=request.user 추가
        form = ConsultationForm(request.POST, request.FILES, instance=consultation, user=request.user)
        if form.is_valid():
            form.save()
            for f in request.FILES.getlist('attachments'):
                ConsultationAttachment.objects.create(consultation=consultation, file=f)
            return redirect('consultations:detail', pk=pk)
    else:
        # 👇 user=request.user 추가
        form = ConsultationForm(instance=consultation, user=request.user)
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

@login_message_required
def attachment_delete(request, pk):
    attachment = get_object_or_404(ConsultationAttachment, pk=pk)
    consultation_pk = attachment.consultation.pk
    
    if request.user == attachment.consultation.writer or request.user.is_superuser:
        if request.method == 'POST':
            attachment.delete()
            
    return redirect('consultations:detail', pk=consultation_pk)

@login_message_required
def comment_update(request, pk):
    comment = get_object_or_404(ConsultationComment, pk=pk)
    consultation_pk = comment.consultation.pk
    
    # 🚀 권한 체크: 오직 '작성자 본인'만 수정 가능! (관리자도 남의 댓글 수정 불가)
    if request.user != comment.writer:
        messages.warning(request, "본인의 댓글만 수정할 수 있습니다.")
        return redirect('consultations:detail', pk=consultation_pk)

    # POST 요청(저장 버튼 누름)일 때만 내용 업데이트
    if request.method == 'POST':
        updated_content = request.POST.get('content', '').strip()
        if updated_content:
            comment.content = updated_content
            comment.save() # 수정일(updated_at) 자동 갱신됨
            
    # 작업이 끝나면 무조건 원래 있던 상세 페이지로 새로고침(이동)
    return redirect('consultations:detail', pk=consultation_pk)