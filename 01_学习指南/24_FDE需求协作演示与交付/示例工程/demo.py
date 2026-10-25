"""实际回环HTTP端到端UAT；业务场景与身份均为合成。"""

import json
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from adapter import HttpPolicySource
from mock_source import create_source_server
from server import create_app_server
from service import PolicyService


@contextmanager
def running_server(server):
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
        if worker.is_alive():
            raise RuntimeError("本地演示线程未结束")


def submit_query(address, question, token="demo-reader"):
    payload = json.dumps({"question": question}, ensure_ascii=False).encode("utf-8")
    request = Request(
        address + "/api/query",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": token},
    )
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        with error:
            return error.code, json.loads(error.read())


def run_uat():
    records = json.loads(
        (Path(__file__).parent / "fixtures" / "policies-v1.json").read_text(
            encoding="utf-8"
        )
    )
    cases = [
        ("正常政策", "退款期限是多少", "demo-reader", "answered"),
        ("资料不足", "VIP退款期限", "demo-reader", "refused"),
        ("权限拒绝", "退款期限是多少", "demo-guest", "denied"),
    ]
    results = []
    for mode in ("normal", "offline"):
        with running_server(create_source_server(records, mode=mode)) as source_address:
            service = PolicyService(HttpPolicySource(source_address + "/policies"))
            with running_server(create_app_server(service)) as app_address:
                current = (
                    cases
                    if mode == "normal"
                    else [
                        ("数据源故障", "退款期限是多少", "demo-reader", "unavailable")
                    ]
                )
                for name, question, token, expected in current:
                    code, output = submit_query(app_address, question, token)
                    results.append(
                        {
                            "case": name,
                            "http": code,
                            "expected": expected,
                            "actual": output["status"],
                            "passed": output["status"] == expected,
                            "answer": output["answer"],
                            "citations": output["citations"],
                        }
                    )
    return {
        "source": "simulated",
        "transport": "actual_loopback_http",
        "cases": results,
        "passed": all(row["passed"] for row in results),
    }


def main():
    report = run_uat()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
