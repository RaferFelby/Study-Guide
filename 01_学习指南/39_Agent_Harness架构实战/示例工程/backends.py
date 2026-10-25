"""规则后端与可选本机 Ollama JSON 后端，共用动作校验。"""

import json
from urllib.request import ProxyHandler, Request, build_opener


def scripted_decide(state: dict, messages: list[dict]) -> dict:
    names = [item["name"] for item in state["observations"]]
    if "lookup_policy" not in names:
        return {
            "kind": "tool",
            "name": "lookup_policy",
            "arguments": {"topic": "refund"},
        }
    if "save_note" not in names:
        return {
            "kind": "tool",
            "name": "save_note",
            "arguments": {"text": "30 天内申请退款 [policy-v1]"},
        }
    return {"kind": "final", "text": "30 天内申请退款 [policy-v1]"}


class OllamaBackend:
    def __init__(self, model: str):
        if not model or ":cloud" in model:
            raise ValueError("use an existing local model name")
        self.model = model

    def __call__(self, state: dict, messages: list[dict]) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "format": "json",
            "stream": False,
            "keep_alive": "1m",
            "options": {
                "temperature": 0,
                "seed": 42,
                "num_predict": 128,
                "num_ctx": 2048,
            },
        }
        request = Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # 本地请求不走环境代理；响应大小有界，socket timeout 不是总任务时限。
        with build_opener(ProxyHandler({})).open(request, timeout=120) as response:
            body = response.read(65537)
        if len(body) > 65536:
            raise ValueError("model response exceeds 64 KiB")
        reply = json.loads(body)
        if reply.get("done") is not True or reply.get("done_reason") == "length":
            raise ValueError("model response is incomplete")
        return json.loads(reply["message"]["content"])
