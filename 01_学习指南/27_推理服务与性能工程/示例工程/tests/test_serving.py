import io
import json
import socket
import struct
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from backend import GenerationCancelled, SyntheticBackend
from benchmark import run_benchmark
from client import percentile, read_events, stream_request, validate_address
from demo import cancel_request, running_server
from quantization import compare_task, symmetric_int4
from scheduler import page_allocation, simulate_schedule
from server import create_server, validate_request


def wait_idle(server):
    deadline = time.perf_counter() + 3
    while server.service_state.snapshot()["active"] and time.perf_counter() < deadline:
        time.sleep(0.01)
    assert server.service_state.snapshot()["active"] == 0


def post_raw(address, body):
    request = Request(
        address + "/generate",
        data=body,
        headers={"Content-Type": "application/json", "X-Demo-Session": "demo-a"},
    )
    with pytest.raises(HTTPError) as result:
        urlopen(request, timeout=3)
    with result.value as response:
        return response.code, json.loads(response.read())


def test_stream_counts_timing_and_release():
    server = create_server(SyntheticBackend(0.001, 0.001))
    with running_server(server) as address:
        result = stream_request(address, output_units=4)
        wait_idle(server)
        assert result["success"] and result["output_units"] == 4
        assert 0 <= result["ttft_seconds"] <= result["elapsed_seconds"]
        assert result["tpot_seconds"] >= 0
        assert server.service_state.snapshot()["counts"]["completed"] == 1


@pytest.mark.parametrize("body", [b"null", b"[]", b"{broken", b"true"])
def test_malformed_requests_have_controlled_errors_and_no_slot(body):
    server = create_server()
    with running_server(server) as address:
        assert post_raw(address, body)[0] == 400
        assert server.service_state.snapshot()["active"] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"output_units": True},
        {"output_units": 33},
        {"prompt": ""},
        {"request_id": "../x"},
        {"role": "admin"},
    ],
)
def test_request_model_rejects_boundaries(change):
    body = {"prompt": "x", "request_id": "id-a", "output_units": 4}
    body.update(change)
    with pytest.raises((ValueError, TypeError)):
        validate_request(body)


def test_admission_duplicate_overload_and_cancel_isolation():
    started = threading.Event()
    release = threading.Event()

    class HoldingBackend:
        name = "test_only_holding"

        def generate(self, _prompt, _units, cancelled):
            started.set()
            if not release.wait(2):
                raise RuntimeError("测试未释放后端")
            if cancelled.is_set():
                raise GenerationCancelled
            yield "x "

    server = create_server(HoldingBackend(), capacity=1)
    with running_server(server) as address, ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            stream_request, address, output_units=1, request_id="holding"
        )
        try:
            assert started.wait(2)
            duplicate = stream_request(address, output_units=1, request_id="holding")
            busy = stream_request(address, output_units=1, request_id="other")
            assert duplicate["http"] == 409 and busy["http"] == 429
            assert cancel_request(address, "holding", "demo-b")[0] == 403
            assert cancel_request(address, "holding", "demo-a")[0] == 202
        finally:
            release.set()
        assert future.result(timeout=3)["failure"] == "cancelled_or_incomplete"
        wait_idle(server)
        assert cancel_request(address, "holding")[0] == 404


def test_cancel_after_first_fragment_releases_slot():
    server = create_server(SyntheticBackend(0.001, 0.02), capacity=1)
    codes = []
    with running_server(server) as address:

        def cancel_first(body):
            if body["unit_index"] == 0:
                codes.append(cancel_request(address, "cancel-test")[0])

        result = stream_request(
            address, output_units=16, request_id="cancel-test", on_delta=cancel_first
        )
        wait_idle(server)
        assert codes == [202]
        assert not result["success"] and result["output_units"] < 16
        assert server.service_state.snapshot()["counts"]["cancelled"] == 1
        assert stream_request(address, output_units=1)["success"]


def test_disconnect_aborts_generation_and_releases_slot():
    server = create_server(SyntheticBackend(0.001, 0.02), capacity=1)
    with running_server(server):
        connection = socket.create_connection(
            ("127.0.0.1", server.server_port), timeout=3
        )
        body = json.dumps(
            {"prompt": "x", "output_units": 32, "request_id": "disconnect"}
        ).encode()
        headers = f"POST /generate HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\nX-Demo-Session: demo-a\r\nContent-Length: {len(body)}\r\n\r\n".encode()
        connection.sendall(headers + body)
        received = b""
        while b"event: delta" not in received:
            chunk = connection.recv(4096)
            if not chunk:
                raise RuntimeError("未收到首段即关闭连接")
            received += chunk
        linger = struct.pack("hh" if sys.platform == "win32" else "ii", 1, 0)
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
        connection.close()
        wait_idle(server)
        assert server.service_state.snapshot()["counts"]["disconnected"] == 1


def test_backend_failure_is_not_success_and_frees_slot(caplog):
    class BrokenBackend:
        name = "test_failure"

        def generate(self, *_args):
            raise RuntimeError("模拟测试故障")

    server = create_server(BrokenBackend())
    with running_server(server) as address:
        result = stream_request(address)
        wait_idle(server)
        assert result["failure"] == "backend_failed"
        assert "模拟测试故障" in caplog.text
        assert server.service_state.snapshot()["counts"]["backend_failed"] == 1


def test_sse_parser_multiline_and_incomplete_boundaries():
    events = list(
        read_events(io.BytesIO(b': ping\nevent: done\ndata: {"n":\ndata: 1}\n\n'))
    )
    assert events == [("done", {"n": 1})]
    with pytest.raises(ValueError):
        list(read_events(io.BytesIO(b'data: {"n":1}\n')))
    with pytest.raises(ValueError):
        list(read_events(io.BytesIO(b"data: " + b"x" * 8193)))


def test_missing_done_and_redirect_are_failures():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if body["prompt"] == "redirect":
                self.send_response(302)
                self.send_header("Location", "https://example.invalid/should-not-open")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            event = {"request_id": body["request_id"], "text": "x", "unit_index": 0}
            self.wfile.write(
                ("event: delta\ndata: " + json.dumps(event) + "\n\n").encode()
            )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    # 该测试是独立的缺陷服务，不带教学ServiceState。
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    address = f"http://127.0.0.1:{server.server_port}"
    try:
        assert stream_request(address, output_units=1)["failure"] == "missing_done"
        assert stream_request(address, prompt="redirect")["failure"] == "http_302"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_benchmark_denominators_and_single_unit_tpot():
    server = create_server(SyntheticBackend(0, 0))
    with running_server(server) as address:
        report = run_benchmark(address, requests=4, concurrency=1, output_units=1)
        assert report["summary"]["successes"] == 4
        assert report["summary"]["failure_rate"] == 0
        assert report["summary"]["tpot_p50_seconds"] is None
        assert report["conditions"]["input_units"] == 8
        with pytest.raises(ValueError):
            run_benchmark(address, requests=0)


def test_percentiles_use_documented_nearest_rank():
    assert percentile([4, 1, 3, 2], 0.5) == 2
    assert percentile([4, 1, 3, 2], 0.95) == 4
    with pytest.raises(ValueError):
        percentile([], 0.95)


@pytest.mark.parametrize(
    "address",
    [
        "https://127.0.0.1:8770",
        "http://example.invalid:8770",
        "http://127.0.0.1",
        "http://user@127.0.0.1:8770",
        "http://127.0.0.1:8770/x",
    ],
)
def test_external_or_ambiguous_address_is_rejected(address):
    with pytest.raises(ValueError):
        validate_address(address)


def test_scheduling_pages_and_quantized_task_regression():
    assert simulate_schedule(False)["completed_tick"] == {"A": 2, "B": 5, "C": 6}
    assert simulate_schedule(True)["completed_tick"] == {"A": 2, "C": 3, "B": 5}
    assert page_allocation([5, 2]) == {
        "blocks": [2, 1],
        "used_slots": 7,
        "allocated_slots": 12,
        "unused_slots": 5,
    }
    report = compare_task()
    assert report["fp_passed"] == 4 and report["int4_passed"] == 2
    with pytest.raises(ValueError):
        symmetric_int4([float("nan")])
