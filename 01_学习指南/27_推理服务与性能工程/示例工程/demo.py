"""自己启动临时端口服务，运行实际HTTP、取消与有限压测。"""

import json
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from benchmark import run_benchmark
from client import stream_request
from quantization import compare_task
from scheduler import page_allocation, simulate_schedule
from server import create_server


@contextmanager
def running_server(server):
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.service_state.cancel_all()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
        if worker.is_alive():
            raise RuntimeError("服务线程未结束")
        deadline = time.perf_counter() + 3
        while (
            server.service_state.snapshot()["active"] and time.perf_counter() < deadline
        ):
            time.sleep(0.01)
        if server.service_state.snapshot()["active"]:
            raise RuntimeError("请求取消后仍未释放")


def cancel_request(address, request_id, session="demo-a"):
    request = Request(
        address + "/cancel",
        data=json.dumps({"request_id": request_id}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Demo-Session": session},
    )
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        with error:
            return error.code, json.loads(error.read())


def run_demo():
    server = create_server(capacity=2)
    with running_server(server) as address:
        reports = [
            run_benchmark(address, requests=20, concurrency=concurrency)
            for concurrency in (1, 2, 4)
        ]
        codes = []
        result = stream_request(
            address,
            request_id="cancel-demo",
            output_units=16,
            on_delta=lambda body: (
                codes.append(cancel_request(address, "cancel-demo"))
                if body["unit_index"] == 0
                else None
            ),
        )
        for _ in range(100):
            if server.service_state.snapshot()["active"] == 0:
                break
            time.sleep(0.01)
        stats = server.service_state.snapshot()
    return {
        "benchmarks": reports,
        "cancel": {
            "responses": codes,
            "result": result,
            "active_after": stats["active"],
        },
        "stats": stats,
        "static": simulate_schedule(False),
        "continuous": simulate_schedule(True),
        "pages": page_allocation([5, 2]),
        "quantization": compare_task(),
    }


def main():
    report = run_demo()
    path = Path("report-demo-01.json")
    with path.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "benchmarks": [item["summary"] for item in report["benchmarks"]],
                "cancel": report["cancel"],
                "quantization": report["quantization"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
