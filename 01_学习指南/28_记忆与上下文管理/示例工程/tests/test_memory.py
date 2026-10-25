import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from context import BudgetExceeded, ByteTokenizer, compile_context
from demo import make_history, run_demo
from memory import MemoryStore

NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path):
    return MemoryStore(tmp_path / "memory.sqlite3")


def write(store, owner="alice", value="Chinese", **kwargs):
    return store.write(
        owner,
        "preferred_language",
        value,
        kwargs.pop("source", "conversation-1/message-1"),
        kwargs.pop("source_time", NOW),
        kwargs.pop("now", NOW),
        **kwargs,
    )


def test_confirmation_source_and_metadata(store):
    with pytest.raises(ValueError, match="确认"):
        write(store)
    assert write(store, confirmed=True) == {"status": "created", "version": 1}
    row = store.retrieve("alice", NOW)[0]
    assert row["source"] == "conversation-1/message-1"
    assert row["source_time"] == NOW.isoformat()
    assert row["owner"] == "alice" and row["confidence"] == 0.95


def test_dedupe_correction_and_stale_write(store):
    write(store, confirmed=True)
    assert write(store, confirmed=True)["version"] == 1
    later = NOW + timedelta(minutes=1)
    assert (
        write(
            store,
            value="English",
            source="message-2",
            source_time=later,
            now=later,
            confirmed=True,
        )["version"]
        == 2
    )
    assert store.retrieve("alice", later)[0]["value"] == "English"
    with pytest.raises(ValueError, match="旧时间"):
        write(store, confirmed=True, now=later)
    assert store.event_count("alice") == 2


def test_same_value_new_confirmation_refreshes_source_and_confidence(store):
    write(store, confidence=0.5, confirmed=True)
    assert store.retrieve("alice", NOW) == []
    later = NOW + timedelta(minutes=1)
    assert (
        write(
            store,
            source="new-message",
            source_time=later,
            now=later,
            confidence=0.95,
            confirmed=True,
        )["version"]
        == 2
    )
    assert store.retrieve("alice", later)[0]["source"] == "new-message"


def test_expiry_boundary_and_no_future_reads(store):
    write(store, confirmed=True, ttl_days=1)
    assert store.retrieve("alice", NOW + timedelta(hours=23))
    assert store.retrieve("alice", NOW + timedelta(days=1)) == []
    assert store.retrieve("alice", NOW - timedelta(seconds=1)) == []


def test_user_scope_delete_and_event_cleanup(store):
    write(store, confirmed=True)
    write(store, owner="bob", value="Spanish", confirmed=True)
    assert len(store.retrieve("alice", NOW)) == 1
    assert store.delete("alice") == 1
    assert store.retrieve("alice", NOW) == [] and store.event_count("alice") == 0
    assert store.retrieve("bob", NOW)[0]["value"] == "Spanish"
    assert store.delete("alice") == 0
    context = compile_context(store.retrieve("alice", NOW), [], "next", "alice")
    assert "Chinese" not in context["prompt"]


def test_delete_one_key_preserves_other_key(store):
    write(store, confirmed=True)
    store.write(
        "alice", "answer_style", "step by step", "message-2", NOW, NOW, confirmed=True
    )
    assert store.delete("alice", "preferred_language") == 1
    assert [row["key"] for row in store.retrieve("alice", NOW)] == ["answer_style"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"confidence": float("nan")},
        {"confidence": True},
        {"confidence": 1.1},
        {"ttl_days": 0},
        {"ttl_days": True},
        {"owner": ""},
        {"value": ""},
        {"source_time": NOW + timedelta(days=1)},
        {"now": NOW.replace(tzinfo=None)},
    ],
)
def test_invalid_writes_fail_before_mutating(store, kwargs):
    with pytest.raises(ValueError):
        write(store, confirmed=True, **kwargs)
    assert store.event_count("alice") == 0


def test_policy_and_privilege_are_not_personal_memory_keys(store):
    for key in ("refund_policy", "system_role", "password"):
        with pytest.raises(ValueError, match="个人偏好"):
            store.write("alice", key, "x", "message", NOW, NOW, confirmed=True)


def test_concurrent_updates_have_serial_versions(store):
    def update(index):
        return write(
            store, value=f"value-{index}", source=f"message-{index}", confirmed=True
        )["version"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        versions = list(pool.map(update, range(4)))
    assert sorted(versions) == [1, 2, 3, 4]
    assert store.retrieve("alice", NOW)[0]["version"] == 4


def test_connections_close_before_file_removal(tmp_path):
    path = tmp_path / "closed.sqlite3"
    store = MemoryStore(path)
    write(store, confirmed=True)
    store.retrieve("alice", NOW)
    store.delete("alice")
    path.unlink()
    assert not path.exists()


def test_context_compresses_before_window_and_preserves_current(store):
    write(store, confirmed=True)
    result = compile_context(
        store.retrieve("alice", NOW), make_history(), "current question", "alice"
    )
    assert result["before_tokens"] > result["input_capacity"]
    assert result["input_tokens"] <= 640
    assert (
        result["input_tokens"] + result["output_reserve"] + result["margin"]
        <= result["window"]
    )
    prompt = json.loads(result["prompt"])
    assert prompt["current_user"] == "current question"
    assert len(prompt["recent_history"]) % 2 == 0
    assert result["summary"]["goals"][0]["source_id"] in result["removed_turn_ids"]


def test_tokenizer_utf8_byte_scope():
    assert len(ByteTokenizer().encode("hi")) == 2
    assert len(ByteTokenizer().encode("你好")) == 6


def test_cross_user_memory_and_bad_history_are_rejected(store):
    write(store, owner="bob", confirmed=True)
    with pytest.raises(ValueError, match="其他用户"):
        compile_context(store.retrieve("bob", NOW), [], "x", "alice")
    with pytest.raises(ValueError, match="完整"):
        compile_context([], make_history()[:1], "x", "alice")
    with pytest.raises(ValueError, match="历史"):
        compile_context([], [{"role": "user"}], "x", "alice")


def test_oversized_current_is_rejected_not_truncated():
    with pytest.raises(BudgetExceeded, match="当前输入"):
        compile_context([], [], "x" * 1000, "alice")


def test_summary_and_memory_omissions_are_visible(store):
    write(store, value="x" * 200, confirmed=True)
    result = compile_context(
        store.retrieve("alice", NOW),
        make_history(),
        "x",
        "alice",
        window=300,
        output_reserve=40,
        margin=20,
    )
    assert result["history_summary_dropped"]
    assert result["dropped_memory_keys"] == ["preferred_language"]
    assert result["input_tokens"] <= 240


def test_demo_is_synthetic_and_deleted_owner_has_no_hits():
    report = run_demo()
    assert report["origin"].startswith("synthetic")
    assert report["wrong_memory_case"]["source_expected"] == "English"
    assert report["wrong_memory_case"]["mistaken_value"] == "Chinese"
    assert report["wrong_memory_case"]["corrected_value"] == "English"
    assert report["duplicate"]["version"] == 1 and report["correction"]["version"] == 2
    assert report["expired_hits"] == 0
    assert report["alice_hits_after"] == [] and report["alice_events_after"] == 0
    assert len(report["bob_hits_after"]) == 1
