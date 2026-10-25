from collections import Counter
from collections.abc import Iterable


class InvalidTicket(ValueError):
    """输入的工单不符合最小业务规则。"""


def clean_statuses(rows: Iterable[dict[str, object]]) -> list[str]:
    """读取工单状态，拒绝缺字段、空值和未知状态。"""
    allowed = {"open", "closed"}
    statuses: list[str] = []
    for index, row in enumerate(rows):
        status = row.get("status")
        if not isinstance(status, str) or status not in allowed:
            raise InvalidTicket(f"第 {index} 条工单的状态无效")
        statuses.append(status)
    return statuses


def count_statuses(rows: Iterable[dict[str, object]]) -> dict[str, int]:
    """统计合法工单中的 open 与 closed 数量。"""
    counts = Counter(clean_statuses(rows))
    return {"open": counts.get("open", 0), "closed": counts.get("closed", 0)}
