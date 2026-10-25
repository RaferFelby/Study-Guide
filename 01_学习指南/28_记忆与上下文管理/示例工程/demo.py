"""合成时间/用户/对话，临时SQLite，不调用LLM或记录真实个人信息。"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from context import compile_context
from memory import MemoryStore


def make_history():
    history = []
    for index in range(12):
        history.append(
            {
                "id": f"u-{index}",
                "role": "user",
                "text": "goal: learn python step by step"
                if index % 3 == 0
                else "Please explain the previous exercise with a small example.",
            }
        )
        history.append(
            {
                "id": f"a-{index}",
                "role": "assistant",
                "text": "This is synthetic practice text; check source code and expected results.",
            }
        )
    return history


def run_demo():
    fixture = json.loads(
        (Path(__file__).parent / "fixtures/confirmations.json").read_text(
            encoding="utf-8"
        )
    )
    messages = fixture["messages"]
    now = datetime(2026, 10, 11, 0, 0, tzinfo=timezone.utc)
    with TemporaryDirectory(prefix="memory-demo-", dir=Path.cwd()) as folder:
        store = MemoryStore(Path(folder) / "memory.sqlite3")
        first = store.write(
            "demo-alice",
            "preferred_language",
            "Chinese",
            "conversation-1/message-1",
            now,
            now,
            confirmed=True,
        )
        duplicate = store.write(
            "demo-alice",
            "preferred_language",
            "Chinese",
            "conversation-1/message-1",
            now,
            now,
            confirmed=True,
        )
        later = now + timedelta(minutes=1)
        correction = store.write(
            "demo-alice",
            "preferred_language",
            "English",
            "conversation-1/message-2",
            later,
            later,
            confirmed=True,
        )
        store.write(
            "demo-bob",
            "preferred_language",
            "Spanish",
            "conversation-b/message-1",
            now,
            now,
            confirmed=True,
        )
        memories = store.retrieve("demo-alice", later)
        compiled = compile_context(
            memories, make_history(), "What should I study next?", "demo-alice"
        )
        expired = store.retrieve("demo-alice", later + timedelta(days=31))
        deleted = store.delete("demo-alice")
        report = {
            "origin": "synthetic_users_times_dialogue_no_llm",
            "confirmation_origin": fixture["origin"],
            "wrong_memory_case": {
                "source_id": messages[0]["id"],
                "source_expected": messages[0]["expected_value"],
                "mistaken_value": "Chinese",
                "error_detected_by": "fixed_fixture_review_not_model",
                "corrected_value": memories[0]["value"],
            },
            "first": first,
            "duplicate": duplicate,
            "correction": correction,
            "hit": memories,
            "context": compiled,
            "expired_hits": len(expired),
            "deleted": deleted,
            "alice_hits_after": store.retrieve("demo-alice", later),
            "alice_events_after": store.event_count("demo-alice"),
            "bob_hits_after": store.retrieve("demo-bob", later),
        }
    return report


def main():
    report = run_demo()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
