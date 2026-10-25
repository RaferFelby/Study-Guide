"""只读复核已有会话；不更改历史状态，也不调用模型。"""

import argparse
import json
from pathlib import Path

from contracts import evaluate_final
from storage import connect, load


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    arguments = parser.parse_args()
    state = load(arguments.db)
    with connect(arguments.db) as connection:
        notes = dict(connection.execute("SELECT action_key, body FROM notes"))
    report = evaluate_final(state, state.get("answer"), notes)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
