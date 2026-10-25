"""按SSE事件边界读取，计时始于发请求之前；仅读取本机教学服务。"""

import argparse
import json
import math
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "本机教学客户端拒绝重定向", headers, fp)


def validate_address(address):
    parsed = urlsplit(address)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("地址需为http://127.0.0.1:端口且无其他部分")
    if parsed.port is None:
        raise ValueError("明确指定本机端口")
    return address


def read_events(response):
    name = "message"
    data = []
    total_bytes = 0
    while True:
        raw = response.readline(8193)
        total_bytes += len(raw)
        if len(raw) > 8192 or total_bytes > 65536:
            raise ValueError("SSE响应超过教学上限")
        if not raw:
            if data:
                raise ValueError("SSE最后事件缺少空行")
            return
        line = raw.decode("utf-8").rstrip("\r\n")
        if not line:
            if data:
                yield name, json.loads("\n".join(data))
            name, data = "message", []
        elif line.startswith("event:"):
            name = line[6:].lstrip(" ")
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
        # 其他字段/注释在本例不作业务输出，也不算首token。


def stream_request(
    address,
    prompt="eight input units for a fixed toy workload",
    output_units=8,
    session="demo-a",
    request_id=None,
    on_delta=None,
):
    address = validate_address(address)
    request_id = request_id if request_id is not None else str(uuid.uuid4())
    payload = {"prompt": prompt, "output_units": output_units, "request_id": request_id}
    request = Request(
        address + "/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Demo-Session": session},
    )
    opener = build_opener(ProxyHandler({}), NoRedirect())
    started = time.perf_counter()
    arrivals = []
    texts = []
    done = None
    failure = None
    code = None
    try:
        with opener.open(request, timeout=3) as response:
            code = response.status
            if response.headers.get_content_type() != "text/event-stream":
                raise ValueError("响应不是SSE")
            for event, body in read_events(response):
                if not isinstance(body, dict) or body.get("request_id") != request_id:
                    raise ValueError("事件请求ID不匹配")
                if event == "delta":
                    if (
                        body.get("unit_index") != len(texts)
                        or not isinstance(body.get("text"), str)
                        or not body["text"]
                    ):
                        raise ValueError("输出片段次序或内容无效")
                    arrivals.append(time.perf_counter())
                    texts.append(body["text"])
                    if on_delta is not None:
                        on_delta(body)
                elif event == "done":
                    done = body
                    break
                elif event == "error":
                    failure = body.get("error", "stream_error")
                    break
            if done is None and failure is None:
                failure = "missing_done"
            elif done is not None and (
                done.get("finish_reason") != "stop"
                or done.get("output_units") != len(texts)
                or len(texts) != output_units
            ):
                failure = "cancelled_or_incomplete"
    except HTTPError as error:
        with error:
            code = error.code
            failure = f"http_{code}"
    except (URLError, OSError, ValueError) as error:
        failure = type(error).__name__
    elapsed = time.perf_counter() - started
    return {
        "request_id": request_id,
        "http": code,
        "success": failure is None,
        "failure": failure,
        "output_units": len(texts),
        "text": "".join(texts),
        "ttft_seconds": arrivals[0] - started if arrivals else None,
        "tpot_seconds": (arrivals[-1] - arrivals[0]) / (len(arrivals) - 1)
        if len(arrivals) > 1
        else None,
        "elapsed_seconds": elapsed,
    }


def percentile(values, fraction):
    if (
        not values
        or not 0 < fraction <= 1
        or any(not math.isfinite(value) or value < 0 for value in values)
    ):
        raise ValueError("分位数需非空有限非负数据与(0,1]比例")
    ordered = sorted(values)
    return ordered[math.ceil(fraction * len(ordered)) - 1]


def main():
    parser = argparse.ArgumentParser(description="本机SSE模拟推理客户端")
    parser.add_argument("--address", default="http://127.0.0.1:8770")
    parser.add_argument("--output-units", type=int, default=8)
    args = parser.parse_args()
    result = stream_request(
        args.address,
        output_units=args.output_units,
        on_delta=lambda body: print(body["text"], end="", flush=True),
    )
    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
