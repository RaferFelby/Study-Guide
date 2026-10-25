"""MCP 2026-07-28 的有限教学子集；并非完整通用SDK。"""

import json

from catalog import INTERNAL_URI, PUBLIC_URI, list_resources, list_tools, read_record

PROTOCOL_VERSION = "2026-07-28"
VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
CAPABILITIES_KEY = "io.modelcontextprotocol/clientCapabilities"
CLIENT_INFO_KEY = "io.modelcontextprotocol/clientInfo"
SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"
MAX_MESSAGE_BYTES = 32768
SERVER_INFO = {"name": "learning-policy-server", "version": "1.0.0"}


class RpcError(ValueError):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.data = data


def build_request(request_id, method, params=None, version=PROTOCOL_VERSION):
    values = dict(params or {})
    values["_meta"] = {
        VERSION_KEY: version,
        CAPABILITIES_KEY: {},
        CLIENT_INFO_KEY: {"name": "learning-policy-client", "version": "1.0.0"},
    }
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": values}


def error_response(request_id, code, message, data=None):
    result = {"jsonrpc": "2.0", "error": {"code": code, "message": message}}
    if request_id is not None:
        result["id"] = request_id
    if data is not None:
        result["error"]["data"] = data
    return result


def complete(request_id, result):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "resultType": "complete",
            "_meta": {SERVER_INFO_KEY: SERVER_INFO},
            **result,
        },
    }


def uncached(result):
    # 不复用任何列表/资料缓存，避免把教学权限切换隐藏在缓存里。
    return {**result, "ttlMs": 0, "cacheScope": "private"}


def text_result(text, is_error=False, structured=None):
    result = {"content": [{"type": "text", "text": text}], "isError": is_error}
    if structured is not None:
        result["structuredContent"] = structured
    return result


def check_params(params, required, optional=()):
    keys = set(params) - {"_meta"}
    if not set(required) <= keys or keys - set(required) - set(optional):
        raise RpcError(-32602, "参数字段缺失或超出教学契约")


class PolicyServer:
    def __init__(self, audience="reader", mode="normal"):
        if audience not in {"reader", "guest"} or mode not in {"normal", "unavailable"}:
            raise ValueError("受信启动配置不合法")
        self.audience = audience
        self.mode = mode

    def handle(self, message):
        request_id = None
        try:
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                raise RpcError(-32600, "不是JSON-RPC 2.0对象")
            if not isinstance(message.get("method"), str):
                raise RpcError(-32600, "请求方法需为字符串")
            if "id" not in message:
                # 本子集不声明通知功能；收到通知不产生响应。
                return None
            candidate = message["id"]
            if type(candidate) not in (str, int) or (
                isinstance(candidate, str) and not 1 <= len(candidate) <= 64
            ):
                raise RpcError(-32600, "教学请求ID需为整数或1～64字符字符串")
            request_id = candidate
            params = message.get("params")
            if not isinstance(params, dict) or not isinstance(
                params.get("_meta"), dict
            ):
                raise RpcError(-32602, "每个请求必须携带_meta")
            metadata = params["_meta"]
            if not isinstance(metadata.get(VERSION_KEY), str) or not isinstance(
                metadata.get(CAPABILITIES_KEY), dict
            ):
                raise RpcError(-32602, "缺少版本或客户端能力元数据")
            if metadata[VERSION_KEY] != PROTOCOL_VERSION:
                raise RpcError(
                    -32022,
                    "协议版本不支持",
                    {
                        "supported": [PROTOCOL_VERSION],
                        "requested": metadata[VERSION_KEY],
                    },
                )
            result = self.dispatch(message["method"], params)
            return complete(request_id, result)
        except RpcError as error:
            return error_response(request_id, error.code, str(error), error.data)

    def dispatch(self, method, params):
        if method == "server/discover":
            check_params(params, [])
            return uncached(
                {
                    "supportedVersions": [PROTOCOL_VERSION],
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                }
            )
        if method == "ping":
            check_params(params, [])
            return {}
        if method in {"tools/list", "resources/list", "prompts/list"}:
            check_params(params, [], ["cursor"])
            if "cursor" in params:
                raise RpcError(-32602, "教学列表仅一页，不接受游标")
            if method == "tools/list":
                return uncached({"tools": list_tools(self.audience)})
            if method == "resources/list":
                return uncached({"resources": list_resources(self.audience)})
            return uncached(
                {
                    "prompts": [
                        {
                            "name": "policy_question",
                            "description": "准备政策查询提示，不调用模型",
                            "arguments": [{"name": "question", "required": True}],
                        }
                    ]
                }
            )
        if method == "tools/call":
            check_params(params, ["name"], ["arguments"])
            name = params["name"]
            arguments = params.get("arguments", {})
            if name not in ("get_policy", "get_support_note"):
                raise RpcError(-32602, "工具名不存在")
            if not isinstance(arguments, dict):
                raise RpcError(-32602, "arguments需为对象")
            if name == "get_policy":
                if set(arguments) != {"topic"} or arguments["topic"] != "refund":
                    raise RpcError(-32602, "topic仅支持refund，不接受额外参数")
                uri = PUBLIC_URI
            else:
                if arguments:
                    raise RpcError(-32602, "内部备注工具不接受参数")
                if self.audience != "reader":
                    return text_result("权限拒绝：当前演示配置不能读内部备注", True)
                uri = INTERNAL_URI
            if self.mode == "unavailable":
                return text_result("合成资料暂不可用，请人工核查", True)
            record = read_record(uri)
            return text_result(
                json.dumps(record, ensure_ascii=False), structured=record
            )
        if method == "resources/read":
            check_params(params, ["uri"])
            uri = params["uri"]
            if uri not in (PUBLIC_URI, INTERNAL_URI):
                raise RpcError(-32602, "资源URI不存在")
            if uri == INTERNAL_URI and self.audience != "reader":
                # 1001是本工程应用错误码，不是MCP规定的统一权限码。
                raise RpcError(1001, "权限拒绝：不能读内部资源")
            if self.mode == "unavailable":
                raise RpcError(1002, "合成资料暂不可用")
            record = read_record(uri)
            return uncached(
                {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(record, ensure_ascii=False),
                        }
                    ]
                }
            )
        if method == "prompts/get":
            check_params(params, ["name"], ["arguments"])
            arguments = params.get("arguments", {})
            if params["name"] != "policy_question" or not isinstance(arguments, dict):
                raise RpcError(-32602, "提示名或参数不合法")
            if set(arguments) != {"question"}:
                raise RpcError(-32602, "提示需且仅需question")
            question = arguments["question"]
            if not isinstance(question, str) or not 1 <= len(question.strip()) <= 200:
                raise RpcError(-32602, "question需为1～200字符文本")
            return {
                "description": "只准备提示；未请求模型也未执行工具",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "请依据已授权政策回答；资料不足则说明。问题："
                            + question,
                        },
                    }
                ],
            }
        raise RpcError(-32601, "本教学子集不支持此方法")
