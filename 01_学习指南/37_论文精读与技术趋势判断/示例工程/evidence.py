"""记录结构检查不是自动事实核验，也不给论文打总分。"""

from urllib.parse import urlparse

QUESTIONS = ("problem", "method", "evidence", "limitations")
EVIDENCE_KINDS = {"paper_report", "local_mechanism", "business_test", "unknown"}


def validate_note(note):
    if not isinstance(note, dict):
        raise TypeError("笔记需为字典")
    for field in ("id", "title", "locator", "reading_depth", *QUESTIONS):
        if not isinstance(note.get(field), str) or not note[field].strip():
            raise ValueError(f"缺少非空字段：{field}")
    url = urlparse(note.get("source", ""))
    if url.scheme != "https" or not url.netloc:
        raise ValueError("来源需为完整HTTPS链接")
    return note


def validate_claim(claim):
    if not isinstance(claim, dict) or claim.get("kind") not in EVIDENCE_KINDS:
        raise ValueError("证据类别不符")
    for field in ("statement", "scope", "locator"):
        if not isinstance(claim.get(field), str) or not claim[field].strip():
            raise ValueError(f"主张必须说明{field}")
    if claim["kind"] == "unknown" and claim.get("verified") is True:
        raise ValueError("未知证据不能写为已验证")
    return claim


def compare_conditions(before, after):
    fields = (
        "model",
        "dataset",
        "split",
        "prompt",
        "trainable_parameters",
        "updates",
        "generation_budget",
        "metric",
    )
    differences = []
    for field in fields:
        left, right = before.get(field), after.get(field)
        status = (
            "unknown"
            if left is None or right is None
            else "same"
            if left == right
            else "different"
        )
        differences.append(
            {"field": field, "before": left, "after": right, "status": status}
        )
    return differences
