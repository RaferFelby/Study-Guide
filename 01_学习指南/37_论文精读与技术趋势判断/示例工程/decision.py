"""明确的教学决策规则；布尔输入须由实际证据支撑，不代替业务审批。"""

FIELDS = (
    "needed",
    "mechanism_passed",
    "business_pilot_passed",
    "backend_ready",
    "rollback_ready",
    "critical_failure",
)


def decide(facts):
    if set(facts) != set(FIELDS) or any(
        type(facts[field]) is not bool for field in FIELDS
    ):
        raise ValueError("决策输入需为六个明确布尔字段，未知项先保留在证据卡")
    if facts["critical_failure"]:
        return {"stance": "不采用", "reason": "当前关键失败未解决"}
    if not facts["needed"]:
        return {"stance": "不采用", "reason": "当前任务没有对应需求"}
    if not facts["backend_ready"] or not facts["rollback_ready"]:
        return {"stance": "观望", "reason": "执行或退出条件不满足"}
    if not facts["mechanism_passed"]:
        return {"stance": "观望", "reason": "关键机制尚未验证"}
    if facts["business_pilot_passed"]:
        return {"stance": "采用", "reason": "本教学规则要求的限定验收已通过"}
    return {"stance": "试点", "reason": "机制可用但业务收益尚未验证"}


def lora_demo_facts():
    """假设机制通过、业务尚未验收的教学情景，不自动获取真实业务事实。"""
    return {
        "needed": True,
        "mechanism_passed": True,
        "business_pilot_passed": False,
        "backend_ready": True,
        "rollback_ready": True,
        "critical_failure": False,
    }
