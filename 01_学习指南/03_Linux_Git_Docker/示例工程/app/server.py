import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def build_payload(path: str) -> dict[str, Any]:
    """为健康检查和首页构造稳定的 JSON 响应。"""
    if path == "/health":
        return {"status": "ok", "service": "linux-git-docker-demo"}
    if path == "/":
        return {"status": "ok", "message": "service is running"}
    return {"status": "not_found", "path": path}


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        payload = build_payload(self.path)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        status_code = 200 if payload["status"] == "ok" else 404
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="启动示例 HTTP 服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopping")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
