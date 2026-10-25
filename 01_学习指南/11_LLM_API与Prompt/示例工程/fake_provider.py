"""本地假 API：用于无密钥、无外网地练习 HTTP 请求和临时错误处理。"""

from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from json import dumps, loads
from threading import Thread
from typing import ClassVar


class _FakeProviderHandler(BaseHTTPRequestHandler):
    request_counts: ClassVar[dict[str, int]] = {}

    def do_POST(self) -> None:
        if self.path != "/v1/responses":
            self._send_json(404, {"error": "unknown endpoint"})
            return

        body_length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = loads(self.rfile.read(body_length))
        except (ValueError, TypeError):
            self._send_json(400, {"error": "invalid JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "body must be a JSON object"})
            return

        idempotency_key = self.headers.get("Idempotency-Key", "missing-key")
        _FakeProviderHandler.request_counts[idempotency_key] = (
            _FakeProviderHandler.request_counts.get(idempotency_key, 0) + 1
        )
        request_count = _FakeProviderHandler.request_counts[idempotency_key]
        user_text = _extract_user_text(payload.get("input"))

        if "always-rate-limit" in user_text:
            self._send_json(
                429, {"error": "simulated rate limit"}, {"Retry-After": "0"}
            )
            return
        if "retry-once" in user_text and request_count == 1:
            self._send_json(
                429, {"error": "simulated temporary rate limit"}, {"Retry-After": "0"}
            )
            return
        if "bad-request" in user_text:
            self._send_json(400, {"error": "simulated invalid request"})
            return

        if "申请退款" in user_text:
            output_text = '{"category":"refund","priority":2,"evidence":"申请退款"}'
        else:
            output_text = '{"category":"other","priority":2,"evidence":"用户请求"}'

        response_data = {
            "id": "resp_local_demo",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": output_text}],
                }
            ],
            "usage": {"input_tokens": 24, "output_tokens": 15},
        }
        self._send_json(200, response_data)

    def _send_json(
        self,
        status_code: int,
        response_data: dict[str, object],
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        response_body = dumps(response_data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        for header_name, header_value in (extra_headers or {}).items():
            self.send_header(header_name, header_value)
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format_string: str, *args: object) -> None:
        """隐藏本地 HTTP 访问日志，避免演示输出被日志淹没。"""


def _extract_user_text(api_input: object) -> str:
    if isinstance(api_input, str):
        return api_input
    if not isinstance(api_input, list):
        return ""

    text_parts = []
    for message in api_input:
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                text_parts.append(content)
    return "\n".join(text_parts)


@contextmanager
def run_fake_provider() -> Iterator[str]:
    """在本机随机端口启动假服务，离开 with 块时关闭线程和端口。"""
    _FakeProviderHandler.request_counts = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeProviderHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
