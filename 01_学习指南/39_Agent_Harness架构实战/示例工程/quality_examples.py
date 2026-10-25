"""用内存夹具观察执行与质量的区别；不读写数据库，不调用模型。"""

from contracts import POLICY, action_key, evaluate_final


def make_fixture(note_text: str) -> tuple[dict, dict[str, str]]:
    action = {"kind": "tool", "name": "save_note", "arguments": {"text": note_text}}
    key = action_key(action)
    state = {
        "observations": [
            {"name": "lookup_policy", "result": POLICY.copy()},
            {
                "name": "save_note",
                "action_key": key,
                "result": {"saved": True, "scope": "local_learning_note"},
            },
        ]
    }
    return state, {key: note_text}


def main() -> None:
    correct_text = "30 天内申请退款 [policy-v1]"
    cases = [
        ("正确", correct_text, correct_text),
        ("天数错误", "300 天内申请退款 [policy-v1]", correct_text),
        ("否定回答", "不是 30 天内申请退款 [policy-v1]", correct_text),
        ("来源错误", "30 天内申请退款 [policy-v2]", correct_text),
        ("笔记错误", correct_text, "300 天内申请退款 [policy-v1]"),
        ("同义改写待人工复核", "购买后30天内可申请退款，来源policy-v1", correct_text),
    ]
    for label, answer, note in cases:
        state, notes = make_fixture(note)
        report = evaluate_final(state, answer, notes)
        print(
            label,
            "执行=",
            report["execution_completed"],
            "答案=",
            report["answer_correct"],
            "笔记=",
            report["note_correct"],
            "接受=",
            report["accepted"],
        )
    state, notes = make_fixture(correct_text)
    report = evaluate_final(state, correct_text, {})
    print("只有回执没有笔记", report["accepted"], report["failed_checks"])


if __name__ == "__main__":
    main()
