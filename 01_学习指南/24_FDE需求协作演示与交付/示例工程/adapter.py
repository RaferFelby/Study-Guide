"""合成外部政策HTTP接口适配；本轮只允许回环地址。"""

import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_RESPONSE_BYTES = 16384


class SourceUnavailable(RuntimeError):
    pass


class SourceContractError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        raise HTTPError(request.full_url, code, "演示不跟随重定向", headers, file)


def validate_policies(records):
    if not isinstance(records, list) or len(records) > 100:
        raise SourceContractError("政策需为不超过100项的列表")
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            "id",
            "title",
            "text",
            "version",
            "url",
        }:
            raise SourceContractError("政策字段不符合接口契约")
        for field in ("id", "title", "text", "version", "url"):
            if (
                not isinstance(record[field], str)
                or not record[field].strip()
                or len(record[field]) > 1000
            ):
                raise SourceContractError("政策字段需为非空有限长度字符串")
        if record["id"] in seen:
            raise SourceContractError("政策ID重复")
        seen.add(record["id"])
        address = urlsplit(record["url"])
        if address.scheme != "https" or address.netloc != "policy.example.invalid":
            raise SourceContractError("模拟引用仅允许预设示例域名")
    return records


class HttpPolicySource:
    def __init__(self, source_url, timeout_seconds=2):
        address = urlsplit(source_url)
        if address.port is not None and not 1 <= address.port <= 65535:
            raise ValueError("演示端口需为1至65535")
        if (
            address.scheme != "http"
            or address.hostname != "127.0.0.1"
            or address.username
            or address.password
            or address.query
            or address.fragment
        ):
            raise ValueError("演示数据源仅允许无凭据的127.0.0.1 HTTP地址")
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("超时需大于0")
        self.source_url = source_url
        self.timeout_seconds = timeout_seconds

    def fetch(self):
        request = Request(self.source_url, headers={"Accept": "application/json"})
        try:
            opener = build_opener(ProxyHandler({}), NoRedirect())
            with opener.open(request, timeout=self.timeout_seconds) as response:
                content_type = response.headers.get_content_type()
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise SourceUnavailable("模拟外部数据源不可用") from error
        if content_type != "application/json" or len(raw) > MAX_RESPONSE_BYTES:
            raise SourceContractError("数据源格式或字节上限不符")
        try:
            records = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SourceContractError("数据源不是UTF-8 JSON") from error
        return validate_policies(records)
