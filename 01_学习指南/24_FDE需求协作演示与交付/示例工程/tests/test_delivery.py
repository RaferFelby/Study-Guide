import json
import time
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from adapter import (
    MAX_RESPONSE_BYTES,
    HttpPolicySource,
    SourceContractError,
    SourceUnavailable,
    validate_policies,
)
from demo import run_uat, running_server, submit_query
from mock_source import create_source_server
from server import create_app_server
from service import PolicyService

RECORDS = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "policies-v1.json").read_text(
        encoding="utf-8"
    )
)


class CountingSource:
    def __init__(self):
        self.calls = 0

    def fetch(self):
        self.calls += 1
        return RECORDS


def test_denied_and_invalid_input_never_fetch_source():
    source = CountingSource()
    service = PolicyService(source)
    assert service.answer("退款期限", "guest")["status"] == "denied"
    for question in (None, "", "x" * 501):
        assert service.answer(question, "reader")["status"] == "invalid"
    assert source.calls == 0


def test_normal_has_version_citation_and_unknown_refuses():
    service = PolicyService(CountingSource())
    output = service.answer("退款期限", "reader")
    assert output["status"] == "answered" and "30天" in output["answer"]
    assert output["citations"][0]["version"] == "v1"
    for question in ("VIP退款期限", "新的优惠政策"):
        assert service.answer(question, "reader")["status"] == "refused"


@pytest.mark.parametrize(
    "mutation", ["not_list", "duplicate", "missing", "empty", "long", "unsafe_url"]
)
def test_invalid_external_contract_rejected(mutation):
    data = deepcopy(RECORDS)
    if mutation == "not_list":
        data = {"items": data}
    elif mutation == "duplicate":
        data.append(data[0])
    elif mutation == "missing":
        del data[0]["version"]
    elif mutation == "empty":
        data[0]["text"] = ""
    elif mutation == "long":
        data[0]["text"] = "x" * 1001
    else:
        data[0]["url"] = "javascript:alert(1)"
    with pytest.raises(SourceContractError):
        validate_policies(data)


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1/policies",
        "http://example.com/policies",
        "http://user:password@127.0.0.1/policies",
    ],
)
def test_source_config_rejects_nonlocal_or_embedded_credentials(url):
    with pytest.raises(ValueError):
        HttpPolicySource(url)


def test_timeout_requires_finite_positive_number():
    for value in (True, 0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            HttpPolicySource("http://127.0.0.1/policies", value)


def test_actual_mock_source_adapter_normal_and_outage():
    with running_server(create_source_server(RECORDS)) as address:
        assert HttpPolicySource(address + "/policies").fetch() == RECORDS
    with (
        running_server(create_source_server(RECORDS, mode="offline")) as address,
        pytest.raises(SourceUnavailable),
    ):
        HttpPolicySource(address + "/policies").fetch()


def test_http_contract_disallows_role_in_body_and_handles_invalid_json():
    source = CountingSource()
    with running_server(create_app_server(PolicyService(source))) as address:
        for payload in (b'{"question":"refund","role":"reader"}', b"not-json"):
            request = Request(
                address + "/api/query",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with pytest.raises(HTTPError) as error:
                urlopen(request, timeout=3)
            with error.value:
                assert error.value.code == 400
        code, result = submit_query(address, "退款期限", "unknown")
        assert code == 403 and result["status"] == "denied"
    assert source.calls == 0


def test_four_end_to_end_uat_cases():
    report = run_uat()
    assert report["passed"] and len(report["cases"]) == 4
    assert [row["http"] for row in report["cases"]] == [200, 200, 403, 503]


def test_page_uses_plain_text_for_untrusted_results():
    page = (Path(__file__).parents[1] / "page.html").read_text(encoding="utf-8")
    assert "textContent" in page and "innerHTML" not in page
    assert "合成资料与模拟身份" in page


def test_version_fixture_can_backup_update_and_restore(tmp_path):
    active = tmp_path / "active.json"
    backup = tmp_path / "backup.json"
    v1 = json.dumps(RECORDS, ensure_ascii=False)
    active.write_text(v1, encoding="utf-8")
    backup.write_bytes(active.read_bytes())
    v2 = (Path(__file__).parents[1] / "fixtures" / "policies-v2.json").read_text(
        encoding="utf-8"
    )
    active.write_text(v2, encoding="utf-8")
    assert json.loads(active.read_text(encoding="utf-8"))[0]["version"] == "v2"
    active.write_bytes(backup.read_bytes())
    assert active.read_text(encoding="utf-8") == v1


@pytest.mark.parametrize(
    "mode", ["type", "size", "json", "utf8", "redirect", "timeout"]
)
def test_actual_http_failure_contracts_and_redirect_rejection(mode):
    paths = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            paths.append(self.path)
            if mode == "timeout":
                time.sleep(0.06)
            if mode == "redirect":
                self.send_response(302)
                self.send_header(
                    "Location", f"http://127.0.0.1:{self.server.server_port}/unexpected"
                )
                self.end_headers()
                return
            body = json.dumps(RECORDS).encode()
            if mode == "size":
                body = b" " * (MAX_RESPONSE_BYTES + 1)
            elif mode == "json":
                body = b"not-json"
            elif mode == "utf8":
                body = b"\xff"
            self.send_response(200)
            self.send_header(
                "Content-Type", "text/plain" if mode == "type" else "application/json"
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                # 超时客户端已退出，服务器只完成自身测试收尾。
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    expected = (
        SourceUnavailable if mode in {"redirect", "timeout"} else SourceContractError
    )
    with running_server(server) as address, pytest.raises(expected):
        HttpPolicySource(
            address + "/policies", 0.01 if mode == "timeout" else 2
        ).fetch()
    assert paths == ["/policies"]
