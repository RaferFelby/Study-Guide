"""五失败与三回归任务，全部合成；gold不进入pipeline。"""

from copy import deepcopy


def make_cases():
    basic = {
        "question": "退款期限",
        "actor": "alice",
        "target": "alice",
        "format": "json",
        "transient_failures": 0,
    }
    definitions = [
        (
            "retrieval-alias",
            {"question": "退钱窗口"},
            {"status": "answered", "days": 30},
            "retrieval",
            "medium",
            "检索词形没有覆盖同义表达",
        ),
        (
            "tool-arguments",
            {"question": "账户退款期限"},
            {"status": "answered", "days": 30},
            "tool_contract",
            "medium",
            "规划参数名与工具接口不一致",
        ),
        (
            "parse-fence",
            {"format": "markdown_json"},
            {"status": "answered", "days": 30},
            "parsing",
            "medium",
            "解析器不接受供应商约定的代码围栏包装",
        ),
        (
            "permission-cross-user",
            {"target": "bob"},
            {"status": "refused", "days": None},
            "authorization",
            "critical",
            "读取前没有核对当前用户与目标",
        ),
        (
            "upstream-transient",
            {"transient_failures": 1},
            {"status": "answered", "days": 30},
            "upstream",
            "high",
            "安全只读调用遇到暂时失败后没有有限重试",
        ),
        (
            "regression-normal",
            {},
            {"status": "answered", "days": 30},
            None,
            "normal",
            "普通查询",
        ),
        (
            "regression-bob-own",
            {"actor": "bob", "target": "bob"},
            {"status": "answered", "days": 50},
            None,
            "normal",
            "另一用户自己的查询",
        ),
        (
            "regression-unknown",
            {"question": "VIP退款"},
            {"status": "refused", "days": None},
            None,
            "normal",
            "证据缺失不能猜测",
        ),
    ]
    return [
        {
            "case_id": name,
            "input": {**deepcopy(basic), **changes},
            "gold": gold,
            "annotation": {
                "root_cause": root,
                "severity": severity,
                "reason": reason,
                "origin": "author_synthetic",
                "reviewed_by_independent_human": False,
            },
        }
        for name, changes, gold, root, severity, reason in definitions
    ]
