"""授权由可信上下文执行；没有shell、网络或任意路径接口。"""

import json
from dataclasses import dataclass
from pathlib import Path

from audit import AuditLog, fingerprint


@dataclass(frozen=True)
class TrustedContext:
    owner: str
    role: str = "reader"
    approved_actions: frozenset[str] = frozenset()


class SecurityError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class ToolRuntime:
    def __init__(self, root: Path, max_calls=6, max_total_bytes=8192):
        if (
            type(max_calls) is not int
            or max_calls < 1
            or type(max_total_bytes) is not int
            or max_total_bytes < 1
        ):
            raise ValueError("调用与字节预算须为正整数")
        self.root = root.resolve(strict=True)
        self.documents = {
            "policy": {"file": "policy.txt", "owner": None},
            "alice-account": {"file": "alice.json", "owner": "alice"},
            "bob-account": {"file": "bob.json", "owner": "bob"},
        }
        self.max_calls = max_calls
        self.max_total_bytes = max_total_bytes
        self.calls = 0
        self.total_bytes = 0
        self.tickets = {}
        self.audit = AuditLog()

    def execute(self, tool: str, arguments: dict, context: TrustedContext):
        self.calls += 1
        try:
            if self.calls > self.max_calls:
                raise SecurityError("call_budget", "本次会话调用次数已达上限")
            if not isinstance(arguments, dict):
                raise SecurityError("invalid_arguments", "参数必须为对象")
            if tool == "read_document":
                result = self.read_document(arguments, context)
            elif tool == "create_ticket":
                result = self.create_ticket(arguments, context)
            else:
                raise SecurityError("unknown_tool", "工具不在受信注册表")
        except SecurityError as error:
            self.audit.append(context.owner, tool, arguments, "deny", error.code)
            return {"ok": False, "error": {"code": error.code, "message": str(error)}}
        self.audit.append(context.owner, tool, arguments, "allow", "ok")
        return {"ok": True, "data": result}

    def read_document(self, arguments, context):
        if set(arguments) != {"document_id"} or not isinstance(
            arguments["document_id"], str
        ):
            raise SecurityError(
                "invalid_arguments", "只接受document_id文本，不接受路径/owner"
            )
        document = self.documents.get(arguments["document_id"])
        if document is None:
            raise SecurityError("not_found", "文档不存在或无权读取")
        if document["owner"] is not None and document["owner"] != context.owner:
            raise SecurityError("not_found", "文档不存在或无权读取")
        try:
            path = (self.root / document["file"]).resolve(strict=True)
            if not path.is_relative_to(self.root):
                raise SecurityError("path_denied", "解析后的路径超出文档根目录")
            with path.open("rb") as stream:
                content = stream.read(4097)
        except OSError as error:
            raise SecurityError("resource_unavailable", "文档当前不可读取") from error
        if len(content) > 4096:
            raise SecurityError("document_too_large", "单文档超过4096字节")
        if self.total_bytes + len(content) > self.max_total_bytes:
            raise SecurityError("output_budget", "本次会话累计输出已达上限")
        self.total_bytes += len(content)
        try:
            text = content.decode("utf-8")
        except UnicodeError as error:
            raise SecurityError("invalid_encoding", "文档不是UTF-8") from error
        return {
            "document_id": arguments["document_id"],
            "text": text,
            "trust": "untrusted_data",
            "may_instruct_tools": False,
        }

    def create_ticket(self, arguments, context):
        if set(arguments) != {"subject", "request_key"}:
            raise SecurityError("invalid_arguments", "只接受subject和request_key")
        if any(
            not isinstance(value, str) or not 1 <= len(value.strip()) <= 80
            for value in arguments.values()
        ):
            raise SecurityError("invalid_arguments", "字段须为1到80字符非空文本")
        if context.role != "operator":
            raise SecurityError("permission_denied", "当前角色没有创建工单权限")
        action = fingerprint(context.owner, "create_ticket", arguments)
        if action not in context.approved_actions:
            raise SecurityError(
                "needs_confirmation", "写入前需要可信渠道确认该完整动作"
            )
        key = (context.owner, arguments["request_key"])
        if key in self.tickets:
            existing = self.tickets[key]
            if existing["action"] != action:
                raise SecurityError("idempotency_conflict", "相同键对应不同动作")
            return {"ticket_id": existing["ticket_id"], "replayed": True}
        ticket_id = f"ticket-{len(self.tickets) + 1}"
        self.tickets[key] = {"ticket_id": ticket_id, "action": action}
        return {"ticket_id": ticket_id, "replayed": False}


def load_context_demo(owner="alice", role="reader"):
    # 演示只由应用代码构造；不从文档/模型工具参数获得身份或权限。
    return TrustedContext(owner=owner, role=role)


def parse_proposal(text: str):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise SecurityError("invalid_proposal", "重复JSON字段")
            result[key] = value
        return result

    def reject_constant(value):
        raise SecurityError("invalid_proposal", "不接受非有限JSON数值")

    if not isinstance(text, str) or len(text.encode("utf-8")) > 4096:
        raise SecurityError("invalid_proposal", "提议必须为不超过4096字节文本")
    try:
        proposal = json.loads(
            text, object_pairs_hook=unique_object, parse_constant=reject_constant
        )
    except json.JSONDecodeError as error:
        raise SecurityError("invalid_proposal", "提议不是合法JSON") from error
    if (
        not isinstance(proposal, dict)
        or set(proposal) != {"tool", "arguments"}
        or not isinstance(proposal["tool"], str)
        or not isinstance(proposal["arguments"], dict)
    ):
        raise SecurityError("invalid_proposal", "提议须只含tool文本和arguments对象")
    return proposal
