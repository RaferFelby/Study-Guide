"""仅127.0.0.1的SSE兼容教学服务，模拟身份，非生产部署。"""

import argparse
import json
import logging
import re
import threading
import time
from collections import Counter, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend import GenerationCancelled, SyntheticBackend

LOGGER = logging.getLogger(__name__)


def validate_request(body):
    if not isinstance(body, dict):
        raise TypeError("请求需为JSON对象")
    if set(body) != {"prompt", "output_units", "request_id"}:
        raise ValueError("仅接受prompt/output_units/request_id")
    if (
        not isinstance(body["prompt"], str)
        or not 1 <= len(body["prompt"].strip()) <= 512
    ):
        raise ValueError("prompt需为1至512字符")
    if type(body["output_units"]) is not int or not 1 <= body["output_units"] <= 32:
        raise ValueError("output_units需为1至32整数")
    if not isinstance(body["request_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9-]{1,64}", body["request_id"]
    ):
        raise ValueError("request_id需为1至64位字母数字或连字符")
    return body


class ServiceState:
    def __init__(self, capacity):
        if type(capacity) is not int or not 1 <= capacity <= 8:
            raise ValueError("capacity需为1至8整数")
        self.capacity = capacity
        self.slots = threading.BoundedSemaphore(capacity)
        self.lock = threading.Lock()
        self.active = {}
        self.counts = Counter()
        self.recent = deque(maxlen=100)

    def reserve(self, request_id, session):
        with self.lock:
            if request_id in self.active:
                return "duplicate", None
            if not self.slots.acquire(blocking=False):
                self.counts["busy"] += 1
                return "busy", None
            cancelled = threading.Event()
            self.active[request_id] = (session, cancelled)
            return "accepted", cancelled

    def cancel(self, request_id, session):
        with self.lock:
            item = self.active.get(request_id)
            if item is None:
                return "not_found"
            if item[0] != session:
                return "denied"
            item[1].set()
            return "cancel_requested"

    def finish(self, request_id, status, generated, seconds):
        with self.lock:
            self.active.pop(request_id)
            self.slots.release()
            self.counts[status] += 1
            self.recent.append(
                {
                    "request_id": request_id,
                    "status": status,
                    "output_units": generated,
                    "seconds": seconds,
                }
            )

    def snapshot(self):
        with self.lock:
            return {
                "capacity": self.capacity,
                "active": len(self.active),
                "counts": dict(self.counts),
                "recent": list(self.recent),
            }

    def cancel_all(self):
        with self.lock:
            for _session, cancelled in self.active.values():
                cancelled.set()


def create_server(backend=None, capacity=2, port=0):
    backend = backend if backend is not None else SyntheticBackend()
    state = ServiceState(capacity)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(3)

        def log_message(self, *_args):
            pass

        def json_response(self, code, body):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            if code == 429:
                self.send_header("Retry-After", "1")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                self.json_response(
                    200,
                    {
                        "status": "ready",
                        "backend": backend.name,
                        "capacity": state.capacity,
                        "prefill_per_unit_seconds": getattr(
                            backend, "prefill_per_unit", None
                        ),
                        "decode_seconds": getattr(backend, "decode_seconds", None),
                        "scope": "local_demo_simulated_sessions",
                    },
                )
            elif self.path == "/stats":
                self.json_response(200, state.snapshot())
            else:
                self.json_response(404, {"error": "not_found"})

        def read_body(self):
            if self.headers.get_content_type() != "application/json":
                self.json_response(415, {"error": "content_type"})
                return None
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.json_response(400, {"error": "content_length"})
                return None
            if not 1 <= length <= 4096:
                self.json_response(413, {"error": "body_size"})
                return None
            try:
                body = json.loads(self.rfile.read(length))
                if body is None:
                    self.json_response(400, {"error": "object_required"})
                return body
            except (ValueError, UnicodeError):
                self.json_response(400, {"error": "invalid_json"})
                return None

        def do_POST(self):
            if self.path not in {"/generate", "/cancel"}:
                self.json_response(404, {"error": "not_found"})
                return
            session = self.headers.get("X-Demo-Session", "")
            if not re.fullmatch(r"[A-Za-z0-9-]{1,32}", session):
                self.json_response(400, {"error": "demo_session_required"})
                return
            body = self.read_body()
            if body is None:
                return
            if self.path == "/cancel":
                if (
                    not isinstance(body, dict)
                    or set(body) != {"request_id"}
                    or not isinstance(body["request_id"], str)
                ):
                    self.json_response(400, {"error": "invalid_cancel"})
                    return
                result = state.cancel(body["request_id"], session)
                self.json_response(
                    {"not_found": 404, "denied": 403, "cancel_requested": 202}[result],
                    {"status": result},
                )
                return
            try:
                body = validate_request(body)
            except (ValueError, TypeError) as error:
                self.json_response(400, {"error": str(error)})
                return
            request_id = body["request_id"]
            admission, cancelled = state.reserve(request_id, session)
            if admission != "accepted":
                self.json_response(
                    409 if admission == "duplicate" else 429, {"error": admission}
                )
                return
            started = time.perf_counter()
            generated = 0
            status = "completed"
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                for text in backend.generate(
                    body["prompt"], body["output_units"], cancelled
                ):
                    self.event(
                        "delta",
                        {
                            "request_id": request_id,
                            "text": text,
                            "unit_index": generated,
                        },
                    )
                    generated += 1
                self.event(
                    "done",
                    {
                        "request_id": request_id,
                        "finish_reason": "stop",
                        "output_units": generated,
                        "backend": backend.name,
                    },
                )
            except GenerationCancelled:
                status = "cancelled"
                try:
                    self.event(
                        "done",
                        {
                            "request_id": request_id,
                            "finish_reason": "cancelled",
                            "output_units": generated,
                        },
                    )
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                status = "disconnected"
                cancelled.set()
            except Exception:
                # 仅此请求边界收束后端故障，明确记失败并向客户端报告，不伪装成功。
                status = "backend_failed"
                LOGGER.exception("本机教学后端失败，request_id=%s", request_id)
                try:
                    self.event(
                        "error", {"request_id": request_id, "error": "backend_failed"}
                    )
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass
            finally:
                self.close_connection = True
                state.finish(
                    request_id, status, generated, time.perf_counter() - started
                )

        def event(self, name, body):
            data = json.dumps(body, ensure_ascii=False)
            self.wfile.write(f"event: {name}\ndata: {data}\n\n".encode())
            self.wfile.flush()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.service_state = state
    return server


def main():
    parser = argparse.ArgumentParser(description="仅本机模拟SSE推理服务")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--capacity", type=int, default=2)
    args = parser.parse_args()
    server = create_server(capacity=args.capacity, port=args.port)
    print(f"本机模拟服务 http://127.0.0.1:{server.server_port}，Ctrl+C停止", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.service_state.cancel_all()
        server.server_close()


if __name__ == "__main__":
    main()
