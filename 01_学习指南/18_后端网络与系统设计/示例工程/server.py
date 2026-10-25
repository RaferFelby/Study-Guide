"""只监听回环地址的教学HTTP服务；不用于公开部署。"""

import argparse
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from service import QueryService, ServiceError, public_job
from storage import ConflictError, JobStore

DEMO_TOKENS = {"demo-alice": "alice", "demo-bob": "bob"}
MAX_BODY_BYTES = 4096
LOGGER = logging.getLogger(__name__)


class ApiServer(ThreadingHTTPServer):
    def __init__(self, address, service):
        if address[0] != "127.0.0.1":
            raise ValueError("教学服务只允许127.0.0.1")
        self.service = service
        self.disconnect_count = 0
        self.disconnect_lock = threading.Lock()
        super().__init__(address, ApiHandler)


class ApiHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(2)

    def do_GET(self):
        self.handle_api("GET")

    def do_POST(self):
        self.handle_api("POST")

    def handle_api(self, method):
        self.request_id = uuid4().hex
        self.body_read = False
        path = urlsplit(self.path).path
        try:
            if method == "GET" and path == "/health":
                return self.reply(200, {"status": "ok"})
            owner = DEMO_TOKENS.get(
                self.headers.get("Authorization", "").removeprefix("Bearer ")
            )
            if owner is None or not self.headers.get("Authorization", "").startswith(
                "Bearer "
            ):
                raise ServiceError(401, "unauthorized", "请使用本机演示Bearer令牌")
            if method == "POST" and path in ("/query", "/jobs"):
                body = self.read_json()
                expected = (
                    {"question"} if path == "/query" else {"question", "request_key"}
                )
                if set(body) != expected:
                    raise ServiceError(
                        400, "invalid_fields", "JSON字段必须与接口约定完全一致"
                    )
                if path == "/query":
                    return self.reply(
                        200, self.server.service.query(owner, body["question"])
                    )
                job, created = self.server.service.submit(
                    owner, body["request_key"], body["question"]
                )
                return self.reply(202 if created else 200, public_job(job))
            parts = path.strip("/").split("/")
            if len(parts) in (2, 3) and parts[0] == "jobs":
                if method == "GET" and len(parts) == 2:
                    job = self.server.service.store.get(owner, parts[1])
                elif method == "POST" and len(parts) == 3 and parts[2] == "cancel":
                    job = self.server.service.store.cancel(owner, parts[1])
                else:
                    raise ServiceError(404, "not_found", "接口不存在")
                if job is None:
                    raise ServiceError(404, "not_found", "任务不存在或无权查看")
                return self.reply(200, public_job(job))
            raise ServiceError(404, "not_found", "接口不存在")
        except ConflictError as error:
            self.reply(
                409, {"error": {"code": "idempotency_conflict", "message": str(error)}}
            )
        except ServiceError as error:
            self.reply(
                error.status, {"error": {"code": error.code, "message": str(error)}}
            )
        except TimeoutError:
            self.reply(
                408, {"error": {"code": "request_timeout", "message": "读取请求超时"}}
            )
        except Exception:
            # HTTP边界保留完整作者日志，给客户端稳定错误，不泄漏堆栈。
            LOGGER.exception("未处理异常 request_id=%s", self.request_id)
            self.reply(
                500, {"error": {"code": "internal_error", "message": "服务内部错误"}}
            )

    def read_json(self):
        if self.headers.get("Transfer-Encoding") is not None:
            raise ServiceError(400, "unsupported_encoding", "教学接口不接收分块请求")
        if (
            self.headers.get("Content-Type", "").split(";")[0].strip()
            != "application/json"
        ):
            raise ServiceError(415, "unsupported_media", "需要application/json")
        try:
            size = int(self.headers.get("Content-Length", ""))
        except ValueError as error:
            raise ServiceError(
                400, "invalid_length", "需要合法Content-Length"
            ) from error
        if not 0 < size <= MAX_BODY_BYTES:
            raise ServiceError(413, "body_too_large", "请求体须为1到4096字节")
        raw = self.rfile.read(size)
        self.body_read = True
        if len(raw) != size:
            raise ServiceError(400, "incomplete_body", "请求体长度不足")
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ServiceError(400, "invalid_json", "需要UTF-8 JSON对象") from error
        if not isinstance(body, dict):
            raise ServiceError(400, "invalid_json", "顶层需要JSON对象")
        return body

    def reply(self, status, data):
        # 小型已知长度的拒绝请求仍读走正文，避免关闭时RST丢失错误响应。
        # 不解析、不执行该正文；超大或分块请求不做无界清空。
        if self.command == "POST" and not self.body_read:
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if 0 < size <= MAX_BODY_BYTES * 2:
                    self.rfile.read(size)
            except (ValueError, OSError):
                LOGGER.info("拒绝请求正文未完整读取 request_id=%s", self.request_id)
            self.body_read = True
        content = json.dumps(
            {"request_id": self.request_id, **data}, ensure_ascii=False
        ).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Request-ID", self.request_id)
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            with self.server.disconnect_lock:
                self.server.disconnect_count += 1
            LOGGER.info("客户端断开 request_id=%s", self.request_id)
        finally:
            self.close_connection = True

    def log_message(self, format, *args):
        LOGGER.info(
            "http request_id=%s %s", getattr(self, "request_id", "-"), format % args
        )


def main():
    parser = argparse.ArgumentParser(description="本机工单查询教学服务")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--database", type=Path, default=Path(__file__).parent / "jobs.sqlite"
    )
    options = parser.parse_args()
    if not 0 <= options.port <= 65535:
        parser.error("port须在0到65535之间")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    service = QueryService(JobStore(options.database))
    server = ApiServer(("127.0.0.1", options.port), service)
    service.start_worker()
    print(f"http://127.0.0.1:{server.server_port}；Ctrl+C退出", flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.close()


if __name__ == "__main__":
    main()
