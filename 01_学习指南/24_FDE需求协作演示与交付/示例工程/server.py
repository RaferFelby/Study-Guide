"""本地演示页面与普通JSON输出；身份令牌全部是假值。"""

import argparse
import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from adapter import HttpPolicySource
from service import PolicyService

MAX_REQUEST_BYTES = 4096
DEMO_ROLES = {"demo-reader": "reader", "demo-guest": "guest"}


class AppHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, service, page, **kwargs):
        self.service = service
        self.page = page
        super().__init__(*args, **kwargs)

    def send_payload(self, code, value):
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path != "/":
            self.send_payload(404, {"error": "not_found"})
            return
        payload = self.page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path != "/api/query":
            self.send_payload(404, {"error": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_payload(400, {"error": "invalid_length"})
            return
        if not 0 < size <= MAX_REQUEST_BYTES:
            self.send_payload(413, {"error": "request_too_large_or_empty"})
            return
        if self.headers.get_content_type() != "application/json":
            self.send_payload(415, {"error": "expected_json"})
            return
        try:
            value = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_payload(400, {"error": "invalid_json"})
            return
        if not isinstance(value, dict) or set(value) != {"question"}:
            self.send_payload(400, {"error": "invalid_fields"})
            return
        role = DEMO_ROLES.get(self.headers.get("Authorization"), "guest")
        result = self.service.answer(value["question"], role)
        code = {"invalid": 400, "denied": 403, "unavailable": 503}.get(
            result["status"], 200
        )
        self.send_payload(code, result)

    def log_message(self, format, *args):
        return


def create_app_server(service, port=0):
    page = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")
    return ThreadingHTTPServer(
        ("127.0.0.1", port), partial(AppHandler, service=service, page=page)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--source-url", default="http://127.0.0.1:8766/policies")
    options = parser.parse_args()
    service = PolicyService(HttpPolicySource(options.source_url))
    with create_app_server(service, options.port) as server:
        print(
            f"本地模拟演示 http://127.0.0.1:{server.server_port}/，非生产认证",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("已停止本地演示")


if __name__ == "__main__":
    main()
