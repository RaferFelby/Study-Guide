"""本机可信子进程的串行stdio客户端；不接入外部应用或模型。"""

import json
import math
import queue
import subprocess
import sys
import threading
from pathlib import Path

from protocol import MAX_MESSAGE_BYTES, build_request


class RemoteError(RuntimeError):
    def __init__(self, value):
        super().__init__(value["message"])
        self.code = value["code"]
        self.data = value.get("data")


class StdioClient:
    def __init__(
        self, audience="reader", mode="normal", timeout_seconds=3, server_path=None
    ):
        if audience not in {"reader", "guest"} or mode not in {"normal", "unavailable"}:
            raise ValueError("演示启动配置不合法")
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 10
        ):
            raise ValueError("超时需大于0且不超过10秒")
        self.timeout_seconds = timeout_seconds
        self.server_path = Path(
            server_path or Path(__file__).with_name("server.py")
        ).resolve()
        self.audience = audience
        self.mode = mode
        self.process = None
        self.messages = queue.Queue(maxsize=8)
        self.reader = None
        self.next_id = 1

    def __enter__(self):
        if self.process is not None:
            raise RuntimeError("客户端不可重复进入")
        command = [
            sys.executable,
            "-u",
            str(self.server_path),
            "--audience",
            self.audience,
            "--mode",
            self.mode,
        ]
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # stderr继承终端，不占stdout，也没有无人读取的stderr管道。
            cwd=self.server_path.parent,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.reader = threading.Thread(target=self._read_messages, daemon=True)
        self.reader.start()
        return self

    def _read_messages(self):
        while True:
            raw = self.process.stdout.readline(MAX_MESSAGE_BYTES + 1)
            try:
                if not raw:
                    self.messages.put_nowait(None)
                    return
                self.messages.put_nowait(raw)
            except queue.Full:
                # 本客户端只允许一个在途请求；泛洪不能无限积累到内存。
                return
            if len(raw) > MAX_MESSAGE_BYTES or not raw.endswith(b"\n"):
                return

    def request(self, method, params=None):
        if (
            self.process is None
            or self.process.poll() is not None
            or self.process.stdin.closed
        ):
            raise ConnectionError("客户端尚未打开或子进程已关闭")
        if not isinstance(method, str) or (
            params is not None and not isinstance(params, dict)
        ):
            raise ValueError("方法应为字符串，参数应为字典")
        request_id = self.next_id
        self.next_id += 1
        message = build_request(request_id, method, params)
        payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        if len(payload) > MAX_MESSAGE_BYTES:
            raise ValueError("请求超出教学字节上限")
        try:
            self.process.stdin.write(payload)
            self.process.stdin.flush()
            raw = self.messages.get(timeout=self.timeout_seconds)
            if raw is None:
                raise ConnectionError("子进程关闭输出，未收到响应")
            if len(raw) > MAX_MESSAGE_BYTES or not raw.endswith(b"\n"):
                raise ConnectionError("响应超限或缺少行结束符")
            response = json.loads(raw.decode("utf-8"))
            if (
                not isinstance(response, dict)
                or response.get("jsonrpc") != "2.0"
                or type(response.get("id")) is not int
                or response["id"] != request_id
            ):
                raise ConnectionError("响应结构或ID不匹配")
            if ("result" in response) == ("error" in response):
                raise ConnectionError("响应需且仅需result或error")
            if "error" in response:
                error = response["error"]
                if (
                    not isinstance(error, dict)
                    or type(error.get("code")) is not int
                    or not isinstance(error.get("message"), str)
                ):
                    raise ConnectionError("错误响应结构不合法")
                raise RemoteError(error)
            result = response["result"]
            if not isinstance(result, dict) or result.get("resultType") != "complete":
                raise ConnectionError("本客户端仅支持complete结果")
            return result
        except queue.Empty as error:
            self.close()
            raise TimeoutError("等待stdio响应超时，连接已关闭") from error
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            OSError,
            ConnectionError,
        ) as error:
            self.close()
            raise ConnectionError("stdio传输或响应异常，连接已关闭") from error

    def close(self):
        if self.process is None:
            return
        if not self.process.stdin.closed:
            try:
                self.process.stdin.close()
            except OSError:
                pass  # 只在关闭自己已失效的管道时处理；仍继续回收子进程。
        try:
            self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=1)
        if self.reader is not None:
            self.reader.join(timeout=1)
        self.process.stdout.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def main():
    with StdioClient() as client:
        print(client.request("server/discover")["supportedVersions"])
        result = client.request(
            "tools/call", {"name": "get_policy", "arguments": {"topic": "refund"}}
        )
        print(result["structuredContent"]["text"])


if __name__ == "__main__":
    main()
