"""独立本地mock数据服务；不是实际第三方业务接口。"""

import argparse
import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from adapter import validate_policies


class SourceHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, records, mode="normal", **kwargs):
        self.records = records
        self.mode = mode
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path != "/policies":
            self.send_error(404)
            return
        code = 503 if self.mode == "offline" else 200
        value = {"error": "synthetic outage"} if code == 503 else self.records
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


def create_source_server(records, port=0, mode="normal"):
    validate_policies(records)
    return ThreadingHTTPServer(
        ("127.0.0.1", port), partial(SourceHandler, records=records, mode=mode)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--mode", choices=["normal", "offline"], default="normal")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(__file__).parent / "fixtures" / "policies-v1.json",
    )
    options = parser.parse_args()
    records = json.loads(options.data.read_text(encoding="utf-8"))
    with create_source_server(records, options.port, options.mode) as server:
        print(
            f"合成政策源 http://127.0.0.1:{server.server_port}/policies，模式 {options.mode}",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("已停止合成政策源")


if __name__ == "__main__":
    main()
