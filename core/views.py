from django.shortcuts import render


def index(request):
    return render(request, "core/index.html") 
# core 앱에서 사용하는 템플릿이지만, 실제로는 templates/core/index.html을 찾음
