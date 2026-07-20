# ==================================================
# 파일 역할: ASGI 서버가 Django 애플리케이션을 실행할 때 사용하는 진입점
# 주석은 코드의 처리 목적과 흐름을 이해하기 쉽도록 기능 단위로 작성했다.
# ==================================================

"""
ASGI config for mysite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

application = get_asgi_application()
