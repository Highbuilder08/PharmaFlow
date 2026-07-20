# Create your views here.
# consultations/views.py

# mimetypes: 파일 이름을 보고 "이 파일이 이미지인지, 문서인지" 종류를 추측할 때 사용
import mimetypes
# os: 파일 경로에서 확장자(.jpg 등) 같은 걸 뽑아낼 때 사용
import os

# PIL(Pillow): 업로드된 이미지가 진짜 이미지 파일인지 열어서 확인할 때 사용
from PIL import Image, UnidentifiedImageError

# render: 화면(HTML)을 그려서 응답으로 보내줌
# redirect: 다른 페이지 주소로 이동시킴
# get_object_or_404: DB에서 데이터를 찾고, 없으면 "404 없음" 에러 페이지를 보여줌
from django.shortcuts import render, redirect, get_object_or_404
# messages: 사용자에게 "성공했어요", "실패했어요" 같은 알림 메시지를 보여줄 때 사용
from django.contrib import messages
# wraps: 아래에서 만드는 로그인 체크 함수(데코레이터)가 원래 함수 이름을 잃지 않게 도와줌
from functools import wraps
# Paginator: 게시글이 많을 때 페이지 단위(1페이지, 2페이지...)로 나눠줌
from django.core.paginator import Paginator
# transaction: 여러 DB 작업을 묶어서, 중간에 하나라도 실패하면 전부 되돌리기 위해 사용
from django.db import transaction
# Count: 댓글 개수 세기 / F: DB 값(조회수 등)을 안전하게 증가시키기 / Q: 검색 조건을 OR로 묶기
from django.db.models import Count, F, Q
# require_POST: 이 함수는 POST 방식 요청으로만 호출 가능하게 제한
from django.views.decorators.http import require_POST

from .models import Consultation, ConsultationComment, ConsultationAttachment, AuditLog
from .forms import ConsultationForm

# ==========================================
# 2. 복약 상담 게시판 (Consultation) CRUD
# ==========================================
# login_message_required: 로그인 여부, 승인 여부를 미리 확인해주는 공용 검사 함수
# 아래에서 @login_message_required 라고 붙이면, 그 함수를 실행하기 전에 이 검사를 먼저 함
def login_message_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 로그인 안 한 사용자는 글 목록 화면으로 돌려보냄
        if not request.user.is_authenticated:
            messages.warning(request, '로그인 전엔 글 목록만 확인 가능합니다.')
            return redirect('consultations:list')
        # 관리자가 아니고, 아직 승인되지 않은 사용자도 목록 화면으로 돌려보냄
        if not request.user.is_superuser and not request.user.is_approved:
            messages.warning(request, '승인된 사용자만 게시판 기능을 이용할 수 있습니다.')
            return redirect('consultations:list')

        # 검사를 통과하면 원래 실행하려던 함수를 실행
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
    # errors: 문제가 발견될 때마다 메시지를 담아두는 리스트. 비어있으면 문제 없음.
    errors = []

    # 기존 첨부파일 개수 + 새로 올리는 개수가 최대 개수를 넘으면 에러 메시지 추가
    if existing_count + len(files) > MAX_ATTACHMENT_COUNT:
        errors.append(
            f'첨부파일은 게시글당 최대 {MAX_ATTACHMENT_COUNT}개까지 등록할 수 있습니다.'
        )

    # 업로드된 파일을 하나씩 꺼내서 검사
    for f in files:
        # 파일 이름에서 확장자만 뽑아서 소문자로 변경 (예: "사진.JPG" -> ".jpg")
        extension = os.path.splitext(f.name)[1].lower()

        # 허용된 확장자 목록에 없으면 에러 메시지 추가
        if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
            errors.append(
                f'"{f.name}"은(는) 등록할 수 없는 형식입니다. '
                f'({", ".join(ALLOWED_ATTACHMENT_EXTENSIONS)} 만 가능합니다.)'
            )

        # 파일 용량이 최대 크기보다 크면 에러 메시지 추가
        if f.size > MAX_ATTACHMENT_SIZE:
            errors.append(
                f'"{f.name}"의 용량이 너무 큽니다. '
                f'파일당 {MAX_ATTACHMENT_SIZE // (1024 * 1024)}MB 이하만 등록할 수 있습니다.'
            )

        # 파일 이름으로 추측한 형식과, 브라우저가 알려준 형식이 서로 다르면 의심스러운 파일로 취급
        guessed_type, _ = mimetypes.guess_type(f.name)
        supplied_type = getattr(f, "content_type", "") or ""
        if guessed_type and supplied_type and guessed_type.split("/")[0] != supplied_type.split("/")[0]:
            errors.append(f'"{f.name}"의 파일 형식 정보가 일치하지 않습니다.')

        # 이미지 확장자인 경우, 실제로 이미지 파일을 열어서 깨진 파일이 아닌지 확인
        if extension in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            try:
                image = Image.open(f)
                image.verify()
            except (UnidentifiedImageError, OSError):
                errors.append(f'"{f.name}"은 올바른 이미지 파일이 아닙니다.')
            finally:
                # 검사를 위해 읽었던 파일 포인터를 다시 처음으로 되돌림 (안 하면 실제 저장 시 파일이 비어버림)
                f.seek(0)

    return errors


# consultation_list: 게시판 첫 화면. 글 목록을 보여주는 함수
def consultation_list(request):
    # 주소창 뒤에 붙는 ?search_type=title 같은 값을 꺼내옴 (없으면 빈 문자열)
    search_type = request.GET.get('search_type', '')
    q = request.GET.get('q', '')  # 검색어
    # 선택된 태그가 있는지 GET 파라미터에서 꺼냄
    selected_tag = request.GET.get('tag', 'all')

    # 공지글과 일반글 기본 쿼리셋 준비
    # 목록에서 작성자와 댓글 수를 쓰므로 select_related/annotate로 미리 가져온다.
    base_queryset = Consultation.objects.select_related('writer').annotate(
        comment_count=Count('comments')
    )

    notices = base_queryset.filter(tag='NOTICE').order_by('created_at')  # 공지 글만, 오래된 순
    normal_posts = base_queryset.exclude(tag='NOTICE').order_by('-created_at')  # 공지 제외 나머지 글, 최신순

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

# consultation_detail: 글 하나를 자세히 보는 화면. 댓글 작성도 이 함수에서 처리
# pk: 몇 번째 글인지를 나타내는 번호 (primary key)
@login_message_required
def consultation_detail(request, pk):
    # POST 요청이면 "댓글 작성 버튼을 눌렀다"는 뜻
    if request.method == 'POST':
        comment_content = request.POST.get('content')
        if comment_content:
            consultation = get_object_or_404(Consultation, pk=pk)
            # 댓글을 새로 만들어서 저장
            ConsultationComment.objects.create(consultation=consultation, writer=request.user, content=comment_content)
            # 같은 페이지로 다시 이동 (새로고침 시 댓글이 중복 등록되는 것을 방지)
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

# consultation_create: 새 글 작성 화면 + 글 저장 처리
@login_message_required
def consultation_create(request):
    # POST 요청이면 "작성 완료 버튼을 눌렀다"는 뜻
    if request.method == 'POST':
        form = ConsultationForm(request.POST, request.FILES, user=request.user)
        files = request.FILES.getlist('attachments')  # 함께 업로드된 첨부파일 목록
        attachment_errors = validate_attachments(files)  # 첨부파일 검사

        # 첨부파일에 문제가 있으면 화면에 에러 메시지로 보여줌
        for error in attachment_errors:
            messages.error(request, error)

        # 입력 내용도 정상이고, 첨부파일도 문제없을 때만 실제로 저장
        if form.is_valid() and not attachment_errors:
            # 글 저장 + 첨부파일 저장을 하나로 묶어서, 중간에 오류가 나면 전부 취소되게 함
            with transaction.atomic():
                consultation = form.save(commit=False)  # 아직 DB에 저장하지 않고 객체만 만듦
                consultation.writer = request.user  # 작성자를 현재 로그인한 사용자로 지정
                consultation.save()  # 이제 실제로 DB에 저장
                for f in files:
                    ConsultationAttachment.objects.create(consultation=consultation, file=f)
            return redirect('consultations:list')
    else:
        # GET 요청이면 아직 아무것도 안 쓴 빈 작성 폼을 보여줌
        form = ConsultationForm(user=request.user)
    return render(request, 'consultations/create.html', {'form': form})

# consultation_update: 기존 글 수정 화면 + 수정 내용 저장 처리
@login_message_required
def consultation_update(request, pk):
    # 템플릿에서 기존 첨부파일 목록을 여러 번 순회하므로 미리 가져온다.
    consultation = get_object_or_404(
        Consultation.objects.prefetch_related('attachments'),
        pk=pk,
    )
    # 글쓴이 본인도 아니고 관리자도 아니면 수정 못하게 막고 상세 페이지로 돌려보냄
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

# consultation_delete: 글 삭제. 삭제 전에 누가 삭제했는지 AuditLog(작업 기록)에 남김
@login_message_required
@require_POST
def consultation_delete(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    # 글쓴이 본인이거나 관리자만 삭제 가능
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

# comment_delete: 댓글 삭제 + 작업 기록 남기기
@login_message_required
@require_POST
def comment_delete(request, pk):
    comment = get_object_or_404(ConsultationComment, pk=pk)
    consultation_pk = comment.consultation_id
    # 댓글 작성자 본인이거나 관리자만 삭제 가능
    if request.user == comment.writer or request.user.is_superuser:
        AuditLog.objects.create(
            user=request.user,
            action="댓글 삭제",
            target=f"Comment #{comment.pk}",
            detail=comment.content[:200],
        )
        comment.delete()
    return redirect('consultations:detail', pk=consultation_pk)

# attachment_delete: 첨부파일 삭제 + 작업 기록 남기기
@login_message_required
@require_POST
def attachment_delete(request, pk):
    attachment = get_object_or_404(
        ConsultationAttachment.objects.select_related('consultation__writer'),
        pk=pk,
    )
    consultation_pk = attachment.consultation_id

    # 그 글의 작성자 본인이거나 관리자만 첨부파일을 삭제할 수 있음
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

# my_post_list: "내가 쓴 글" 화면. 로그인한 사용자가 쓴 글만 모아서 보여줌
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

# audit_log_list: 관리자 전용 작업 기록(AuditLog) 목록 화면
@login_message_required
def audit_log_list(request):
    # 관리자가 아니면 못 들어오게 막음
    if not request.user.is_superuser:
        messages.warning(request, "관리자만 접근 가능한 페이지입니다.")
        return redirect('core:index') # 메인 화면으로 튕겨냄

    logs = AuditLog.objects.select_related('user').all()

    # 주소 뒤에 붙는 ?action=...&user=... 값을 꺼내서 필터링에 사용
    selected_action = request.GET.get('action', '')
    username_query = request.GET.get('user', '').strip()

    if selected_action:
        logs = logs.filter(action=selected_action)
    if username_query:
        logs = logs.filter(user__username__icontains=username_query)

    # 지금까지 실제로 기록된 작업 종류들을 뽑아서 필터 드롭다운 선택지로 사용
    action_choices = (
        AuditLog.objects.order_by('action')
        .values_list('action', flat=True)
        .distinct()
    )

    # 페이지당 20건씩만 보여줌
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'consultations/audit_logs.html', {
        'logs': page_obj,
        'action_choices': action_choices,
        'selected_action': selected_action,
        'username_query': username_query,
    })
