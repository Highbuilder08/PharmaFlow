# Create your views here.
# consultations/views.py

import mimetypes
import os

from PIL import Image, UnidentifiedImageError

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from functools import wraps
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.views.decorators.http import require_POST

from .models import Consultation, ConsultationComment, ConsultationAttachment, AuditLog
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
        if not request.user.is_superuser and not request.user.is_approved:
            messages.warning(request, '승인된 사용자만 게시판 기능을 이용할 수 있습니다.')
            return redirect('consultations:list')

        return view_func(request, *args, **kwargs)
    return wrapper


# ==========================================
# 첨부파일 검증
# ==========================================

# 브라우저가 실행할 수 있는 형식(.html, .svg 등)은 허용하지 않는다.
# MEDIA_ROOT는 nginx가 사이트와 같은 오리진으로 서빙하므로
# 해당 형식을 허용하면 저장형 XSS 벡터가 된다.
ALLOWED_ATTACHMENT_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.pdf', '.txt', '.csv',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.hwp', '.hwpx',
)

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 파일당 10MB
MAX_ATTACHMENT_COUNT = 5                # 게시글당 5개


def validate_attachments(files, existing_count=0):
    """업로드된 첨부파일의 개수·확장자·크기를 검사하고 오류 메시지 목록을 반환한다."""
    errors = []

    if existing_count + len(files) > MAX_ATTACHMENT_COUNT:
        errors.append(
            f'첨부파일은 게시글당 최대 {MAX_ATTACHMENT_COUNT}개까지 등록할 수 있습니다.'
        )

    for f in files:
        extension = os.path.splitext(f.name)[1].lower()

        if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
            errors.append(
                f'"{f.name}"은(는) 등록할 수 없는 형식입니다. '
                f'({", ".join(ALLOWED_ATTACHMENT_EXTENSIONS)} 만 가능합니다.)'
            )

        if f.size > MAX_ATTACHMENT_SIZE:
            errors.append(
                f'"{f.name}"의 용량이 너무 큽니다. '
                f'파일당 {MAX_ATTACHMENT_SIZE // (1024 * 1024)}MB 이하만 등록할 수 있습니다.'
            )

        guessed_type, _ = mimetypes.guess_type(f.name)
        supplied_type = getattr(f, "content_type", "") or ""
        if guessed_type and supplied_type and guessed_type.split("/")[0] != supplied_type.split("/")[0]:
            errors.append(f'"{f.name}"의 파일 형식 정보가 일치하지 않습니다.')

        if extension in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            try:
                image = Image.open(f)
                image.verify()
            except (UnidentifiedImageError, OSError):
                errors.append(f'"{f.name}"은 올바른 이미지 파일이 아닙니다.')
            finally:
                f.seek(0)

    return errors


def consultation_list(request):
    search_type = request.GET.get('search_type', '')
    q = request.GET.get('q', '')
    # 선택된 태그가 있는지 GET 파라미터에서 꺼냄
    selected_tag = request.GET.get('tag', 'all')

    # 공지글과 일반글 기본 쿼리셋 준비
    # 목록에서 작성자와 댓글 수를 쓰므로 select_related/annotate로 미리 가져온다.
    base_queryset = Consultation.objects.select_related('writer').annotate(
        comment_count=Count('comments')
    )

    notices = base_queryset.filter(tag='NOTICE').order_by('created_at')
    normal_posts = base_queryset.exclude(tag='NOTICE').order_by('-created_at')

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
    if request.method == 'POST':
        comment_content = request.POST.get('content')
        if comment_content:
            consultation = get_object_or_404(Consultation, pk=pk)
            ConsultationComment.objects.create(consultation=consultation, writer=request.user, content=comment_content)
            return redirect('consultations:detail', pk=pk)
    else:
        # 조회수는 F()로 원자적으로 증가시킨다.
        # save()를 쓰면 auto_now인 updated_at까지 갱신되어
        # 글을 열어보기만 해도 '수정됨' 표시가 붙고, 동시 조회 시 조회수가 유실된다.
        Consultation.objects.filter(pk=pk).update(views=F('views') + 1)

    consultation = get_object_or_404(
        Consultation.objects.select_related('writer').prefetch_related(
            'comments__writer',
            'attachments',
        ),
        pk=pk,
    )
    return render(request, 'consultations/detail.html', {'consultation': consultation})

@login_message_required
def consultation_create(request):
    if request.method == 'POST':
        form = ConsultationForm(request.POST, request.FILES, user=request.user)
        files = request.FILES.getlist('attachments')
        attachment_errors = validate_attachments(files)

        for error in attachment_errors:
            messages.error(request, error)

        if form.is_valid() and not attachment_errors:
            with transaction.atomic():
                consultation = form.save(commit=False)
                consultation.writer = request.user
                consultation.save()
                for f in files:
                    ConsultationAttachment.objects.create(consultation=consultation, file=f)
            return redirect('consultations:list')
    else:
        form = ConsultationForm(user=request.user)
    return render(request, 'consultations/create.html', {'form': form})

@login_message_required
def consultation_update(request, pk):
    # 템플릿에서 기존 첨부파일 목록을 여러 번 순회하므로 미리 가져온다.
    consultation = get_object_or_404(
        Consultation.objects.prefetch_related('attachments'),
        pk=pk,
    )
    if request.user != consultation.writer and not request.user.is_superuser:
        return redirect('consultations:detail', pk=pk)

    if request.method == 'POST':
        form = ConsultationForm(request.POST, request.FILES, instance=consultation, user=request.user)
        files = request.FILES.getlist('attachments')
        attachment_errors = validate_attachments(
            files,
            existing_count=consultation.attachments.count(),
        )

        for error in attachment_errors:
            messages.error(request, error)

        if form.is_valid() and not attachment_errors:
            with transaction.atomic():
                form.save()
                for f in files:
                    ConsultationAttachment.objects.create(consultation=consultation, file=f)
            return redirect('consultations:detail', pk=pk)
    else:
        form = ConsultationForm(instance=consultation, user=request.user)
    return render(request, 'consultations/update.html', {'form': form, 'consultation': consultation})

@login_message_required
@require_POST
def consultation_delete(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.user == consultation.writer or request.user.is_superuser:
        AuditLog.objects.create(
            user=request.user,
            action="게시글 삭제",
            target=f"Consultation #{consultation.pk}",
            detail=consultation.title,
        )
        consultation.delete()
        return redirect('consultations:list')
    return redirect('consultations:detail', pk=pk)

@login_message_required
@require_POST
def comment_delete(request, pk):
    comment = get_object_or_404(ConsultationComment, pk=pk)
    consultation_pk = comment.consultation_id
    if request.user == comment.writer or request.user.is_superuser:
        AuditLog.objects.create(
            user=request.user,
            action="댓글 삭제",
            target=f"Comment #{comment.pk}",
            detail=comment.content[:200],
        )
        comment.delete()
    return redirect('consultations:detail', pk=consultation_pk)

@login_message_required
@require_POST
def attachment_delete(request, pk):
    attachment = get_object_or_404(
        ConsultationAttachment.objects.select_related('consultation__writer'),
        pk=pk,
    )
    consultation_pk = attachment.consultation_id

    if request.user == attachment.consultation.writer or request.user.is_superuser:
        AuditLog.objects.create(
            user=request.user,
            action="첨부파일 삭제",
            target=f"Attachment #{attachment.pk}",
            detail=attachment.filename,
        )
        attachment.delete()

    return redirect('consultations:detail', pk=consultation_pk)

@login_message_required
@require_POST
def comment_update(request, pk):
    comment = get_object_or_404(ConsultationComment, pk=pk)
    consultation_pk = comment.consultation_id

    # 권한 체크: 오직 작성자 본인만 수정 가능 (관리자도 남의 댓글 수정 불가)
    if request.user != comment.writer:
        messages.warning(request, "본인의 댓글만 수정할 수 있습니다.")
        return redirect('consultations:detail', pk=consultation_pk)

    updated_content = request.POST.get('content', '').strip()
    if updated_content:
        comment.content = updated_content
        comment.save() # 수정일(updated_at) 자동 갱신됨

    # 작업이 끝나면 무조건 원래 있던 상세 페이지로 새로고침(이동)
    return redirect('consultations:detail', pk=consultation_pk)

@login_message_required
def my_post_list(request):
    # 현재 로그인한 사용자(request.user)가 작성한 글만 최신순으로 필터링
    my_posts = (
        Consultation.objects
        .filter(writer=request.user)
        .annotate(comment_count=Count('comments'))
        .order_by('-created_at')
    )

    # 페이징 처리 (아래 189줄 숫자만큼 페이징)
    paginator = Paginator(my_posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'consultations/mypost.html', {
        'consultations': page_obj,
    })

@login_message_required
def audit_log_list(request):
    if not request.user.is_superuser:
        messages.warning(request, "관리자만 접근 가능한 페이지입니다.")
        return redirect('core:index') # 메인 화면으로 튕겨냄

    logs = AuditLog.objects.all()
    return render(request, 'consultations/audit_logs.html', {'logs': logs})
