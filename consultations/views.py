# Create your views here.
# consultations/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from functools import wraps 
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Consultation, ConsultationComment, ConsultationAttachment
from .forms import ConsultationForm

# ==========================================
# 2. 복약 상담 게시판 (Consultation) CRUD
# ==========================================
def login_message_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, '로그인 전엔 글 목록만 확인 가능합니다.')
            return redirect('consultations:list') 
                
        return view_func(request, *args, **kwargs)
    return wrapper


def consultation_list(request):
    search_type = request.GET.get('search_type', '')
    q = request.GET.get('q', '')
    # 선택된 태그가 있는지 GET 파라미터에서 꺼냄
    selected_tag = request.GET.get('tag', 'all') 

    # 공지글과 일반글 기본 쿼리셋 준비
    notices = Consultation.objects.filter(tag='NOTICE').order_by('created_at')
    normal_posts = Consultation.objects.exclude(tag='NOTICE').order_by('-created_at')

    # 사용자가 특정 태그를 선택했다면, 그 태그에 해당하는 글만 필터링
    if selected_tag and selected_tag != 'all':
        notices = notices.filter(tag=selected_tag)
        normal_posts = normal_posts.filter(tag=selected_tag)

    # 태그 필터링이 완료된 상태에서 '검색어' 필터링 진행 (태그 안에서 검색 가능)
    if q:
        if search_type == 'title':
            notices = notices.filter(title__icontains=q)
            normal_posts = normal_posts.filter(title__icontains=q)
        elif search_type == 'writer':
            notices = notices.filter(writer__username__icontains=q)
            normal_posts = normal_posts.filter(writer__username__icontains=q)
        else: # 전체 검색
            notices = notices.filter(Q(title__icontains=q) | Q(writer__username__icontains=q))
            normal_posts = normal_posts.filter(Q(title__icontains=q) | Q(writer__username__icontains=q))

    # 1. 페이징 처리
    paginator = Paginator(normal_posts, 10) # 한 페이지당 일반 게시글 표기 수
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # [핵심 추가] 5개 단위 블록 페이징 계산 로직
    block_size = 5 # 한 화면에 보여줄 페이지 번호 개수
    current_page = page_obj.number
    
    # 현재 블록의 시작 페이지와 끝 페이지 계산 (예: 13페이지면 11 ~ 15)
    start_page = ((current_page - 1) // block_size) * block_size + 1
    end_page = start_page + block_size - 1
    
    # 끝 페이지가 전체 페이지 수보다 크면 전체 페이지 수로 맞춤
    if end_page > paginator.num_pages:
        end_page = paginator.num_pages
        
    custom_page_range = range(start_page, end_page + 1)
    
    # 이전 블록, 다음 블록 존재 여부 및 이동할 페이지 번호 계산
    has_prev_block = start_page > 1
    prev_block_page = start_page - 1 # 이전 블록의 마지막 페이지로 이동
    
    has_next_block = end_page < paginator.num_pages
    next_block_page = end_page + 1 # 다음 블록의 첫 페이지로 이동

    return render(request, 'consultations/list.html', {
        'notices': notices,         
        'consultations': page_obj,  
        'q': q,
        'search_type': search_type,
        'selected_tag': selected_tag,
        
        # 계산된 블록 페이징 변수들을 HTML로 넘겨줌
        'custom_page_range': custom_page_range,
        'has_prev_block': has_prev_block,
        'prev_block_page': prev_block_page,
        'has_next_block': has_next_block,
        'next_block_page': next_block_page,
        'last_page': paginator.num_pages,
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
        form = ConsultationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.writer = request.user
            consultation.save()
            for f in request.FILES.getlist('attachments'):
                ConsultationAttachment.objects.create(consultation=consultation, file=f)
            return redirect('consultations:list')
    else:
        form = ConsultationForm(user=request.user)
    return render(request, 'consultations/create.html', {'form': form})

@login_message_required
def consultation_update(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.user != consultation.writer and not request.user.is_superuser:
        return redirect('consultations:detail', pk=pk)

    if request.method == 'POST':
        form = ConsultationForm(request.POST, request.FILES, instance=consultation, user=request.user)
        if form.is_valid():
            form.save()
            for f in request.FILES.getlist('attachments'):
                ConsultationAttachment.objects.create(consultation=consultation, file=f)
            return redirect('consultations:detail', pk=pk)
    else:
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
    
    # 권한 체크: 오직 작성자 본인만 수정 가능 (관리자도 남의 댓글 수정 불가)
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

@login_message_required
def my_post_list(request):
    # 현재 로그인한 사용자(request.user)가 작성한 글만 최신순으로 필터링
    my_posts = Consultation.objects.filter(writer=request.user).order_by('-created_at')

    # 페이징 처리 (아래 189줄 숫자만큼 페이징)
    paginator = Paginator(my_posts, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'consultations/mypost.html', {
        'consultations': page_obj,
    })