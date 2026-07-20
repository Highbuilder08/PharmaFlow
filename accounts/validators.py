# ==================================================
# 파일 역할: 여러 폼과 모델에서 공통으로 사용하는 입력값 검증 함수
# ==================================================

import re

from django.core.exceptions import ValidationError


BUSINESS_NUMBER_PATTERN = re.compile(r"^(?:\d{10}|\d{3}-\d{2}-\d{5})$")


def normalize_business_number(value):
    """
    사업자등록번호를 000-00-00000 형식으로 통일한다.

    허용 입력:
    - 1234567890
    - 123-45-67890
    """
    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    if not BUSINESS_NUMBER_PATTERN.fullmatch(text):
        raise ValidationError(
            "사업자등록번호는 000-00-00000 형식의 숫자 10자리로 "
            "입력해 주세요."
        )

    digits = text.replace("-", "")

    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


def validate_business_number(value):
    """
    대한민국 사업자등록번호의 입력 형식을 검사한다.

    실제 국세청 등록 여부가 아니라 숫자 10자리와 하이픈 위치를
    검증한다.
    """
    if value in (None, ""):
        return

    normalize_business_number(value)
