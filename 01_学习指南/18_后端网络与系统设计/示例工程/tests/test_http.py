import socket
import struct
import threading
import time
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from client import request
from server import ApiServer
from service import QueryService
from storage import JobStore


@pytest.fixture
def api(tmp_path):
    service = QueryService(JobStore(tmp_path / "jobs.sqlite"))
    server = ApiServer(("127.0.0.1", 0), service)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}
    )
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", server, service
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()
    service.close()


def test_health_auth_validation_timeout_and_request_ids(api):
    base, _, _ = api
    status, health = request(base, "GET", "/health", token="wrong")
    assert status == 200 and health["status"] == "ok"
    assert request(base, "POST", "/query", {"question": "refund"}, "wrong")[0] == 401
    assert (
        request(base, "POST", "/query", {"question": "refund", "owner": "bob"})[0]
        == 400
    )
    status, result = request(base, "POST", "/query", {"question": "simulate_timeout"})
    assert status == 504 and result["error"]["code"] == "upstream_timeout"
    assert health["request_id"] != result["request_id"]
    assert request(base, "GET", "/unknown")[0] == 404


def test_submit_poll_cancel_and_other_user(api):
    base, _, service = api
    body = {"question": "refund", "request_key": "key"}
    status, job = request(base, "POST", "/jobs", body)
    assert status == 202
    repeated_status, repeated = request(base, "POST", "/jobs", body)
    assert repeated_status == 200 and repeated["job_id"] == job["job_id"]
    path = "/jobs/" + job["job_id"]
    assert request(base, "GET", path, token="demo-bob")[0] == 404
    assert request(base, "POST", "/jobs", {**body, "question": "support"})[0] == 409
    assert service.run_one()
    assert request(base, "GET", path)[1]["status"] == "completed"
    assert request(base, "POST", path + "/cancel")[1]["status"] == "completed"


@pytest.mark.parametrize(
    "content, content_type, expected",
    [
        (b"{", "application/json", 400),
        (b"[]", "application/json", 400),
        (b"{}", "text/plain", 415),
        (b"x" * 4097, "application/json", 413),
    ],
)
def test_bad_json_and_body_limit(api, content, content_type, expected):
    base, _, _ = api
    message = Request(
        base + "/query",
        data=content,
        headers={"Content-Type": content_type, "Authorization": "Bearer demo-alice"},
    )
    with pytest.raises(HTTPError) as error:
        build_opener(ProxyHandler({})).open(message, timeout=3)
    assert error.value.code == expected
    error.value.close()


def test_client_disconnect_does_not_delete_submitted_job(api, monkeypatch):
    base, server, service = api
    entered = threading.Event()
    release = threading.Event()
    original = service.submit

    def delayed_submit(*args):
        result = original(*args)
        entered.set()
        assert release.wait(2)
        return result

    monkeypatch.setattr(service, "submit", delayed_submit)
    content = b'{"question":"refund","request_key":"disconnect"}'
    message = (
        f"POST /jobs HTTP/1.0\r\nAuthorization: Bearer demo-alice\r\n"
        f"Content-Type: application/json\r\nContent-Length: {len(content)}\r\n\r\n"
    ).encode() + content
    connection = socket.create_connection(("127.0.0.1", server.server_port), timeout=2)
    connection.sendall(message)
    assert entered.wait(2)
    # RST让服务写响应时看见连接已关闭；只作用于本次本机测试连接。
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("hh", 1, 0))
    connection.close()
    release.set()
    for _ in range(100):
        if server.disconnect_count:
            break
        time.sleep(0.01)
    assert server.disconnect_count == 1
    job, created = service.submit("alice", "disconnect", "refund")
    assert not created and job["status"] == "pending"
    assert request(base, "GET", "/health")[0] == 200
