from django.urls import path
from . import views

# 이 앱의 이름표. {% url 'consultations:list' %} 처럼 템플릿에서 주소를 부를 때 사용
app_name = 'consultations'

# urlpatterns: "이런 주소로 들어오면 이 함수를 실행해라"를 정리한 목록
urlpatterns = [
    path('', views.consultation_list, name='list'),  # 게시판 첫 화면 (글 목록)
    path('mypost/', views.my_post_list, name='mypost'),  # 내가 쓴 글 목록
    path('create/', views.consultation_create, name='create'),  # 글 작성
    path('<int:pk>/', views.consultation_detail, name='detail'),  # 글 상세보기 (pk번 글)
    path('<int:pk>/update/', views.consultation_update, name='update'),  # 글 수정
    path('<int:pk>/delete/', views.consultation_delete, name='delete'),  # 글 삭제
    path('comment/<int:pk>/update/', views.comment_update, name='comment_update'),  # 댓글 수정
    path('comment/<int:pk>/delete/', views.comment_delete, name='comment_delete'),  # 댓글 삭제
    path('attachment/<int:pk>/download/', views.attachment_download, name='attachment_download'),  # 첨부파일 다운로드
    path('attachment/<int:pk>/delete/', views.attachment_delete, name='attachment_delete'),  # 첨부파일 삭제
    path('logs/', views.audit_log_list, name='audit_logs'),  # 관리자용 작업 기록 목록
]