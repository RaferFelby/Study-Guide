"""岗位快照、证据完整性与模拟复盘；不判断录用概率或发送申请。"""

from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

STAGES = {"pending", "screen", "technical", "offer", "rejected"}
FEEDBACK_CATEGORIES = {
    "project_explanation",
    "coding",
    "qualification",
    "communication",
    "system_design",
}


def validate_jobs(jobs):
    if not isinstance(jobs, list) or not 5 <= len(jobs) <= 10:
        raise ValueError("岗位练习需5～10条快照")
    ids = set()
    for job in jobs:
        if job["id"] in ids:
            raise ValueError("岗位ID不能重复")
        ids.add(job["id"])
        address = urlsplit(job["url"])
        if address.scheme != "https" or address.hostname not in {
            "openai.com",
            "job-boards.greenhouse.io",
        }:
            raise ValueError("当前夹具仅允许已核对的官方来源域名")
        date.fromisoformat(job["checked"])
        if not job["title"].strip() or not job["tasks"] or not job["qualifications"]:
            raise ValueError("岗位要含标题、任务与资格，不只关键词")
        if job["learner_fit"] != "not_assessed":
            raise ValueError("作者样例不能推断学习者满足资格")
    return jobs


def audit_evidence(evidence, project_root):
    root = Path(project_root).resolve()
    workspace = root.parents[2]
    artifact = (root / evidence["artifact"]).resolve()
    if not artifact.is_relative_to(workspace) or not artifact.is_file():
        raise ValueError("证据源码需存在且位于工作区")
    for field in ("before_successes", "after_successes", "n"):
        if type(evidence[field]) is not int or evidence[field] < 0:
            raise ValueError("计数需非负整数")
    if (
        evidence["n"] == 0
        or max(evidence["before_successes"], evidence["after_successes"])
        > evidence["n"]
    ):
        raise ValueError("成功数与分母不一致")
    for field in ("origin", "dataset", "configuration", "limits", "status"):
        if not isinstance(evidence[field], str) or not evidence[field].strip():
            raise ValueError("证据来源、条件与限制不可为空")
    if evidence["authorship"] != "learner_not_verified":
        raise ValueError("示例证据不能代替学习者个人贡献验证")
    return {
        "id": evidence["id"],
        "before": f"{evidence['before_successes']}/{evidence['n']}",
        "after": f"{evidence['after_successes']}/{evidence['n']}",
        "artifact_exists": True,
        "semantic_claim_verified": False,
    }


def describe_evidence(evidence):
    return (
        f"作者教学工程：在{evidence['n']}条固定合成任务上，组合机制修复的契约通过数"
        f"由{evidence['before_successes']}增至{evidence['after_successes']}；"
        "学习者个人贡献与独立复现未验证；" + evidence["limits"]
    )


def summarize_applications(rows, as_of):
    day = date.fromisoformat(as_of)
    ids = set()
    stages = Counter()
    feedback = Counter()
    pending_days = {}
    for row in rows:
        if (
            row["id"] in ids
            or row["stage"] not in STAGES
            or row["origin"] != "simulated"
        ):
            raise ValueError("本练习需唯一ID、合法阶段与明确模拟来源")
        ids.add(row["id"])
        sent = date.fromisoformat(row["sent"])
        if sent > day:
            raise ValueError("发送日期不能晚于观察日期")
        if any(category not in FEEDBACK_CATEGORIES for category in row["feedback"]):
            raise ValueError("反馈类别不在约定范围")
        stages[row["stage"]] += 1
        feedback.update(set(row["feedback"]))
        if row["stage"] == "pending":
            pending_days[row["id"]] = (day - sent).days
    if not rows:
        return {
            "n": 0,
            "stages": {},
            "priorities": [],
            "pending_days": {},
            "status": "no_data",
        }
    priorities = sorted(feedback, key=lambda name: (-feedback[name], name))[:2]
    return {
        "n": len(rows),
        "stages": dict(stages),
        "feedback_counts": dict(feedback),
        "priorities": priorities,
        "pending_days": pending_days,
        "status": "simulated_snapshot_not_hiring_probability",
    }
