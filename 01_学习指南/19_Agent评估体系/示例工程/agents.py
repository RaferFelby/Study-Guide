"""对照规则系统；不使用case.gold，不冒充真实LLM。"""

from copy import deepcopy


def run_agent(input_data: dict, variant: str):
    if variant not in {"baseline", "guarded"}:
        raise ValueError("未知系统版本")
    request = input_data["request"]
    environment = input_data["environment"]
    is_write = "创建" in request
    tool = "create_ticket" if is_write else "search_policy"
    result = {
        "status": None,
        "days": None,
        "evidence_ids": [],
        "selected_tool": tool,
        "arguments": {"service": environment["service"]},
        "trace": [],
        "unsafe_write": False,
    }
    if variant == "guarded" and is_write and not environment["approved"]:
        result["status"] = "awaiting_approval"
        return result
    if variant == "guarded" and "VIP" in request:
        result["status"] = "refused"
        return result
    if is_write:
        result["trace"].append({"tool": tool, "ok": True})
        result["status"] = "created"
        result["unsafe_write"] = not environment["approved"]
        return result
    result["trace"].append({"tool": tool, "ok": not environment["upstream_timeout"]})
    if environment["upstream_timeout"]:
        result["status"] = "failed"
        return result
    documents = deepcopy(environment["documents"])
    result["retrieved_ids"] = [document["id"] for document in documents]
    if variant == "guarded" and len({document["days"] for document in documents}) > 1:
        result["status"] = "needs_review"
        return result
    if variant == "baseline" and any("untrusted_text" in doc for doc in documents):
        result["trace"].append({"tool": "create_ticket", "ok": True})
        result["unsafe_write"] = True
    result["status"] = "answered"
    result["days"] = documents[0]["days"]
    result["evidence_ids"] = [documents[0]["id"]]
    return result
