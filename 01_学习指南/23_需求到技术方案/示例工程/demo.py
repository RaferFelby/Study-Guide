import json
from pathlib import Path

from planning import projected_value, validate_plan


def main():
    path = Path(__file__).parent / "fixtures" / "plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    print("方案检查", validate_plan(plan))
    print("模拟价值", projected_value(1000, 0.7, 0.9, 90, 45, 10, 3, 20))
    print("低成功率敏感性", projected_value(1000, 0.7, 0.5, 90, 45, 10, 3, 20))
    print(
        "待证假设",
        [
            assumption["id"]
            for assumption in plan["assumptions"]
            if assumption["status"] == "unverified"
        ],
    )


if __name__ == "__main__":
    main()
