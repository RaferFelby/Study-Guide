import tempfile
import threading
import time
from pathlib import Path

from client import request
from server import ApiServer
from service import QueryService
from storage import JobStore


def main():
    with tempfile.TemporaryDirectory(
        prefix="http-demo-", dir=Path(__file__).parent
    ) as directory:
        service = QueryService(JobStore(Path(directory) / "jobs.sqlite"))
        server = ApiServer(("127.0.0.1", 0), service)
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.01}
        )
        service.start_worker()
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            print("health", request(base_url, "GET", "/health"))
            for token in ("demo-alice", "demo-alice", "demo-bob"):
                print(
                    "query",
                    request(base_url, "POST", "/query", {"question": "refund"}, token),
                )
            print(
                "unauthorized",
                request(base_url, "POST", "/query", {"question": "refund"}, "wrong"),
            )
            print(
                "timeout",
                request(base_url, "POST", "/query", {"question": "simulate_timeout"}),
            )
            body = {"question": "support", "request_key": "demo-job-1"}
            status, job = request(base_url, "POST", "/jobs", body)
            print("submit", status, job)
            print("repeat", request(base_url, "POST", "/jobs", body))
            for _ in range(100):
                _, state = request(base_url, "GET", "/jobs/" + job["job_id"])
                if state["status"] in ("completed", "failed"):
                    break
                time.sleep(0.01)
            else:
                raise RuntimeError("任务未在演示预算内完成")
            print("state", state)
            print(
                "other-user",
                request(base_url, "GET", "/jobs/" + job["job_id"], token="demo-bob"),
            )
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
            service.close()


if __name__ == "__main__":
    main()
