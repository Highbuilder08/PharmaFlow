from django.shortcuts import render

# Create your views here.
# consultations/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Consultation, ConsultationComment, ConsultationAttachment
from .forms import ConsultationForm
from django.db.models import Q
from django.core.paginator import Paginator

# 🚨 핵심: consultations 앱에 있는 데코레이터를 빌려옵니다!
from prescriptions.views import login_message_required 

# ==========================================
# 2. 복약 상담 게시판 (Consultation) CRUD
# ==========================================
def consultation_list(request):
    search_type = request.GET.get('search_type', '')
    q = request.GET.get('q', '')

    # 1. 공지사항과 일반글 정렬 쿼리
    notices = Consultation.objects.filter(tag='NOTICE').order_by('created_at')
    normal_posts = Consultation.objects.exclude(tag='NOTICE').order_by('-created_at')

    # 2. 검색어 필터링
    if q:
        if search_type == 'title':
            notices = notices.filter(title__icontains=q)
            normal_posts = normal_posts.filter(title__icontains=q)
        elif search_type == 'writer':
            notices = notices.filter(writer__username__icontains=q)
            normal_posts = normal_posts.filter(writer__username__icontains=q)
        else:
            notices = notices.filter(Q(title__icontains=q) | Q(writer__username__icontains=q))
            normal_posts = normal_posts.filter(Q(title__icontains=q) | Q(writer__username__icontains=q))

    # 두 묶음 병합
    combined_list = list(notices) + list(normal_posts)

    # 🚀 3. [핵심] 페이징 처리 추가
    # 한 페이지에 보여줄 글 개수 설정
    paginator = Paginator(combined_list, 10) 
    
    page_number = request.GET.get('page') # URL에서 ?page=2 같은 현재 페이지 번호 받기
    page_obj = paginator.get_page(page_number) # 해당 페이지의 글들만 쏙 뽑아오기

    return render(request, 'consultations/list.html', {
        'consultations': page_obj, # 👈 기존 combined_list 대신 잘라진 page_obj를 보냅니다!
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