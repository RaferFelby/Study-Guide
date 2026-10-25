from pathlib import Path

from audit import fingerprint, verify_chain
from redteam import attacks
from runtime import ToolRuntime, TrustedContext


def main():
    root = Path(__file__).parent / "fixtures"
    for attack in attacks():
        runtime = ToolRuntime(root)
        context = TrustedContext("alice", role="operator")
        result = runtime.execute(attack["tool"], attack["arguments"], context)
        code = result["error"]["code"] if not result["ok"] else "unexpected_allow"
        print(attack["name"], code, "符合夹具", code == attack["expected"])
        assert verify_chain(runtime.audit.snapshot())
    runtime = ToolRuntime(root)
    arguments = {"subject": "退款工单", "request_key": "approved-1"}
    action = fingerprint("alice", "create_ticket", arguments)
    approved = TrustedContext(
        "alice", role="operator", approved_actions=frozenset({action})
    )
    print(
        "合法读取",
        runtime.execute("read_document", {"document_id": "alice-account"}, approved),
    )
    print("批准写", runtime.execute("create_ticket", arguments, approved))
    print("同键重试", runtime.execute("create_ticket", arguments, approved))
    print(
        "参数被改",
        runtime.execute(
            "create_ticket", {**arguments, "subject": "不同工单"}, approved
        ),
    )
    print(
        "审计链",
        verify_chain(runtime.audit.snapshot()),
        "内存工单数",
        len(runtime.tickets),
    )


if __name__ == "__main__":
    main()
