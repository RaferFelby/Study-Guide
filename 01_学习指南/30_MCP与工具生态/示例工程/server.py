"""一行UTF-8 JSON一个消息；stdout仅放协议，日志进入stderr。"""

import argparse
import json
import sys

from protocol import MAX_MESSAGE_BYTES, PolicyServer, error_response


def serve(input_stream, output_stream, server):
    while True:
        raw = input_stream.readline(MAX_MESSAGE_BYTES + 1)
        if not raw:
            return
        if len(raw) > MAX_MESSAGE_BYTES or not raw.endswith(b"\n"):
            response = error_response(None, -32600, "消息超限或缺少行结束符")
            should_close = True
        else:
            should_close = False
            try:
                message = json.loads(raw.decode("utf-8"))
                response = server.handle(message)
            except (UnicodeDecodeError, json.JSONDecodeError):
                response = error_response(None, -32700, "不是UTF-8 JSON")
            except (OSError, ValueError) as error:
                print(
                    f"固定合成资料读取失败：{type(error).__name__}",
                    file=sys.stderr,
                    flush=True,
                )
                request_id = message.get("id") if isinstance(message, dict) else None
                response = error_response(request_id, -32603, "服务器内部资料异常")
        if response is not None:
            payload = (json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8")
            output_stream.write(payload)
            output_stream.flush()
        if should_close:
            return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audience", choices=["reader", "guest"], default="reader")
    parser.add_argument("--mode", choices=["normal", "unavailable"], default="normal")
    args = parser.parse_args()
    print("合成MCP服务已启动；stdout仅传协议", file=sys.stderr, flush=True)
    serve(sys.stdin.buffer, sys.stdout.buffer, PolicyServer(args.audience, args.mode))


if __name__ == "__main__":
    main()
