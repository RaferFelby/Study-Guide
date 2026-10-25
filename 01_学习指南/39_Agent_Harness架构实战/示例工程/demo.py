"""所有写操作仅进入指定的本地教学数据库。"""

import argparse
import json
from pathlib import Path

from backends import OllamaBackend, scripted_decide
from contracts import action_key
from runtime import cancel, step
from storage import create_session, inspect_session, load


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["start", "step", "show", "cancel"])
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--model", help="existing local Ollama model; start only")
    parser.add_argument("--max-calls", type=int, default=6)
    parser.add_argument("--approve", help="exact SHA256 displayed by show")
    parser.add_argument("--crash-after-tool", action="store_true")
    args = parser.parse_args()
    if args.command == "start":
        backend = "ollama:" + args.model if args.model else "scripted"
        create_session(args.db, backend, args.max_calls)
    elif args.command == "step":
        backend = load(args.db)["backend"]
        decide = (
            scripted_decide
            if backend == "scripted"
            else OllamaBackend(backend.removeprefix("ollama:"))
        )
        step(args.db, decide, args.approve, args.crash_after_tool)
    elif args.command == "cancel":
        cancel(args.db)
    report = inspect_session(args.db)
    pending = report["state"]["pending"]
    report["approval_key"] = action_key(pending) if pending else None
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
