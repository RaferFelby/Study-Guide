"""抽取规则先固定；格式失败不悄悄丢出分母。"""

import re
from decimal import Decimal, InvalidOperation

NUMBER = r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?"
NUMERIC_POLICY = "final_line_hash_or_A_v1_decimal_exact"
CHOICE_POLICY = "single_letter_or_final_answer_line_v1"


def extract_number(text):
    if not isinstance(text, str) or not text.strip():
        return None
    line = text.strip().splitlines()[-1].strip()
    match = re.fullmatch(rf"(?:####|A:)\s*({NUMBER})", line)
    if not match:
        return None
    try:
        value = Decimal(match[1].replace(",", ""))
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def extract_choice(text):
    if not isinstance(text, str) or not text.strip():
        return None
    line = text.strip().splitlines()[-1].strip()
    match = re.fullmatch(r"(?:答案[:：]\s*)?([ABCD])", line)
    return match[1] if match else None


def grade_numeric(response, reference):
    expected = extract_number(reference)
    if expected is None:
        raise ValueError("参考答案格式不符，不能当作模型答错")
    answer = extract_number(response)
    return {
        "extracted": str(answer) if answer is not None else None,
        "expected": str(expected),
        "format_valid": answer is not None,
        "correct": answer is not None and answer == expected,
    }
