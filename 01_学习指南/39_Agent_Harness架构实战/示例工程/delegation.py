"""角色交接的确定性最小例子，不冒充多个大模型。"""

from contracts import POLICY


def researcher(task: dict) -> dict:
    if task != {"task_id": "refund-1", "topic": "refund"}:
        raise ValueError("unsupported delegated task")
    return {
        "task_id": task["task_id"],
        "worker": "researcher",
        "source": POLICY["source"],
        "days": 30,
    }


def reviewer(result: dict) -> dict:
    accepted = (
        result.get("task_id") == "refund-1"
        and result.get("source") == "policy-v1"
        and type(result.get("days")) is int
        and result["days"] == 30
    )
    return {"task_id": "refund-1", "accepted": accepted}


def main():
    result = researcher({"task_id": "refund-1", "topic": "refund"})
    print("正常交接：", reviewer(result))
    result["days"] = 300
    print("损坏结果：", reviewer(result))


if __name__ == "__main__":
    main()
