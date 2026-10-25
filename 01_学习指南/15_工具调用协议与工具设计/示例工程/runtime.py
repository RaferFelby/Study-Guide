"""可信上下文、确认、幂等与实际执行；仅单进程本地演示。"""

import hashlib
import json
import re
from copy import deepcopy

from contracts import (
    TOOL_SCHEMAS,
    ToolCall,
    ToolContext,
    failure,
    parse_arguments,
    success,
    validate_arguments,
)

POLICIES = [
    {
        "id": "storage-retention",
        "text": "Storage retention is 30 days.",
        "locator": "storage.md#retention",
        "permission": "public",
    },
    {
        "id": "compute-retention",
        "text": "Compute retention is 14 days.",
        "locator": "compute.md#retention",
        "permission": "public",
    },
    {
        "id": "database-retention",
        "text": "Database retention is 21 days.",
        "locator": "database.md#retention",
        "permission": "staff",
    },
]


def call_fingerprint(name: str, arguments: dict, actor_id: str) -> str:
    payload = json.dumps(
        {"name": name, "arguments": arguments, "actor_id": actor_id},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ToolRuntime:
    def __init__(self):
        self.tickets = []
        self.idempotent_results = {}
        self.audit = []

    def execute(self, call: ToolCall, context: ToolContext) -> dict:
        if not isinstance(call.call_id, str) or not call.call_id.strip():
            return failure("invalid_call_id", "调用ID不能为空")
        if (
            context.role not in {"public", "staff"}
            or not isinstance(context.actor_id, str)
            or not context.actor_id.strip()
        ):
            return failure("invalid_context", "身份上下文非法")
        if not isinstance(call.name, str) or call.name not in TOOL_SCHEMAS:
            return failure("unknown_tool", "没有注册该工具")
        try:
            arguments = parse_arguments(call.arguments_json)
            validate_arguments(arguments, TOOL_SCHEMAS[call.name]["parameters"])
        except (ValueError, TypeError, RecursionError):
            # 对外给稳定错误，避免把恶意参数或内部细节原样反射到日志。
            result = failure(
                "invalid_arguments", "参数JSON/字段不符合契约，请检查工具说明"
            )
        else:
            if call.name == "search_policies":
                result = self._search(arguments, context)
            else:
                result = self._create_ticket(arguments, context)
        self.audit.append(
            {
                "call_id": call.call_id,
                "name": call.name,
                "actor_id": context.actor_id,
                "ok": result["ok"],
                "error_code": None if result["ok"] else result["error"]["code"],
            }
        )
        return deepcopy(result)

    def _search(self, arguments: dict, context: ToolContext) -> dict:
        query_words = set(re.findall(r"[a-z0-9]+", arguments["query"].lower()))
        matches = []
        for document in POLICIES:
            if document["permission"] == "staff" and context.role != "staff":
                continue
            words = set(re.findall(r"[a-z0-9]+", document["text"].lower()))
            score = len(query_words & words)
            if score:
                matches.append((score, document))
        matches.sort(key=lambda item: (-item[0], item[1]["id"]))
        evidence = []
        for _, document in matches[: arguments["top_k"]]:
            evidence.append(
                {
                    "id": document["id"],
                    "text": document["text"],
                    "locator": document["locator"],
                }
            )
        return success(
            {
                "evidence": evidence,
                "matched_count": len(matches),
                "truncated": len(matches) > arguments["top_k"],
            }
        )

    def _create_ticket(self, arguments: dict, context: ToolContext) -> dict:
        if context.role != "staff":
            return failure("permission_denied", "当前身份无创建权限")
        identity = (context.actor_id, "create_ticket", arguments["idempotency_key"])
        fingerprint = call_fingerprint("create_ticket", arguments, context.actor_id)
        if identity in self.idempotent_results:
            stored_fingerprint, stored_result = self.idempotent_results[identity]
            if stored_fingerprint != fingerprint:
                return failure("idempotency_conflict", "同一幂等键不能对应不同参数")
            return deepcopy(stored_result)
        if fingerprint not in context.approved_fingerprints:
            return failure("confirmation_required", "请先确认具体标题和本地写入动作")
        ticket = {
            "ticket_id": f"DEMO-{len(self.tickets) + 1}",
            "title": arguments["title"],
        }
        result = success(ticket)
        self.tickets.append(ticket)
        self.idempotent_results[identity] = (fingerprint, deepcopy(result))
        return result
