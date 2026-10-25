"""只读取本工程两份固定合成资料；URI不是任意磁盘路径。"""

import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
PUBLIC_URI = "knowledge://public/refund-v1"
INTERNAL_URI = "knowledge://internal/support-v1"
RESOURCE_FILES = {PUBLIC_URI: "refund.json", INTERNAL_URI: "support.json"}


def read_record(uri):
    if uri not in RESOURCE_FILES:
        raise ValueError("资源不在固定目录中")
    raw = (FIXTURES / RESOURCE_FILES[uri]).read_bytes()
    if len(raw) > 4096:
        raise ValueError("合成资料超过教学字节上限")
    record = json.loads(raw.decode("utf-8"))
    if not isinstance(record, dict) or set(record) != {"text", "version"}:
        raise ValueError("合成资料字段不符")
    if any(
        not isinstance(value, str) or not value.strip() for value in record.values()
    ):
        raise ValueError("合成资料应为非空文本")
    return {"uri": uri, **record}


def list_resources(audience):
    resources = [
        {"uri": PUBLIC_URI, "name": "refund_policy", "mimeType": "application/json"}
    ]
    if audience == "reader":
        resources.append(
            {
                "uri": INTERNAL_URI,
                "name": "support_note",
                "mimeType": "application/json",
            }
        )
    return resources


def list_tools(audience):
    tools = [
        {
            "name": "get_policy",
            "description": "读取一份合成公开政策，不代表真实业务规定",
            "inputSchema": {
                "type": "object",
                "properties": {"topic": {"type": "string", "enum": ["refund"]}},
                "required": ["topic"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True},
        }
    ]
    if audience == "reader":
        tools.append(
            {
                "name": "get_support_note",
                "description": "读取合成内部支持备注，需服务端允许",
                "inputSchema": {"type": "object", "additionalProperties": False},
                "annotations": {"readOnlyHint": True},
            }
        )
    return tools
