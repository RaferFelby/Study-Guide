import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from backends import OllamaBackend, scripted_decide
from contracts import action_key, build_context, validate_action
from delegation import researcher, reviewer
from runtime import cancel, step
from storage import commit, connect, create_session, inspect_session, load


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path("results") / ("test-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True)
        self.path = self.directory / "session.db"
        create_session(self.path, "scripted")

    def reach_approval(self):
        step(self.path, scripted_decide)
        return step(self.path, scripted_decide)

    def test_end_to_end_and_terminal_noop(self):
        state = self.reach_approval()
        self.assertEqual(state["status"], "waiting_approval")
        step(self.path, scripted_decide, action_key(state["pending"]))
        final = step(self.path, scripted_decide)
        self.assertEqual(final["status"], "completed")
        self.assertEqual(final["calls"], 3)
        self.assertEqual(len(inspect_session(self.path)["notes"]), 1)
        self.assertEqual(step(self.path, lambda *_: self.fail()), final)

    def test_wrong_approval_never_writes(self):
        self.reach_approval()
        state = step(self.path, scripted_decide, "wrong-key")
        self.assertEqual(state["status"], "waiting_approval")
        self.assertEqual(inspect_session(self.path)["notes"], [])
        self.assertEqual(state["calls"], 2)

    def test_wrong_final_keeps_committed_note_but_fails_quality(self):
        state = self.reach_approval()
        step(self.path, scripted_decide, action_key(state["pending"]))
        final = step(
            self.path,
            lambda *_: {"kind": "final", "text": "300 天内申请退款 [policy-v1]"},
        )
        self.assertEqual(final["status"], "failed")
        self.assertTrue(final["evaluation"]["execution_completed"])
        self.assertFalse(final["evaluation"]["answer_correct"])
        self.assertEqual(len(inspect_session(self.path)["notes"]), 1)
        self.assertEqual(step(self.path, lambda *_: self.fail()), final)

    def test_missing_database_note_rejects_apparent_success(self):
        state = self.reach_approval()
        step(self.path, scripted_decide, action_key(state["pending"]))
        # 只故意损坏本测试创建的独立数据库。
        with connect(self.path) as connection:
            connection.execute("DELETE FROM notes")
        final = step(self.path, scripted_decide)
        self.assertEqual(final["status"], "failed")
        self.assertFalse(final["evaluation"]["execution_completed"])

    def test_key_binds_full_arguments(self):
        state = self.reach_approval()
        old_key = action_key(state["pending"])
        state["pending"]["arguments"]["text"] = "changed"
        self.assertNotEqual(old_key, action_key(state["pending"]))

    def test_crash_after_commit_does_not_duplicate_note(self):
        state = self.reach_approval()
        with self.assertRaisesRegex(RuntimeError, "injected crash"):
            step(self.path, scripted_decide, action_key(state["pending"]), True)
        self.assertIsNone(load(self.path)["pending"])
        self.assertEqual(step(self.path, scripted_decide)["status"], "completed")
        self.assertEqual(len(inspect_session(self.path)["notes"]), 1)

    def test_failure_inside_transaction_rolls_back_note(self):
        state = self.reach_approval()
        with (
            patch("runtime.save", side_effect=RuntimeError("before commit")),
            self.assertRaises(RuntimeError),
        ):
            step(self.path, scripted_decide, action_key(state["pending"]))
        self.assertEqual(inspect_session(self.path)["notes"], [])
        self.assertIsNotNone(load(self.path)["pending"])

    def test_cancel_discards_pending_without_execution(self):
        state = self.reach_approval()
        key = action_key(state["pending"])
        cancel(self.path)
        self.assertEqual(step(self.path, scripted_decide, key)["status"], "cancelled")
        self.assertEqual(inspect_session(self.path)["notes"], [])

    def test_repeated_action_stops(self):
        decide = lambda *_: {
            "kind": "tool",
            "name": "lookup_policy",
            "arguments": {"topic": "refund"},
        }
        step(self.path, decide)
        self.assertEqual(step(self.path, decide)["status"], "failed")

    def test_premature_final_rejected(self):
        state = step(
            self.path, lambda *_: {"kind": "final", "text": "30 days policy-v1"}
        )
        self.assertEqual(state["status"], "failed")

    def test_premature_save_rejected(self):
        state = step(
            self.path,
            lambda *_: {
                "kind": "tool",
                "name": "save_note",
                "arguments": {"text": "x"},
            },
        )
        self.assertEqual(state["status"], "failed")
        self.assertEqual(inspect_session(self.path)["notes"], [])

    def test_bad_action_is_recorded_as_failure(self):
        state = step(
            self.path, lambda *_: {"kind": "tool", "name": "shell", "arguments": {}}
        )
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["calls"], 1)

    def test_budget_survives_reopen(self):
        state = load(self.path)
        state["max_calls"] = 1
        commit(self.path, state, "test_budget", {})
        step(self.path, scripted_decide)
        self.assertEqual(step(self.path, scripted_decide)["status"], "budget_exhausted")

    def test_interrupted_request_is_not_resent(self):
        state = load(self.path)
        state["status"] = "requesting"
        state["calls"] = 1
        commit(self.path, state, "test_interruption", {})
        self.assertEqual(step(self.path, lambda *_: self.fail())["status"], "failed")
        self.assertEqual(load(self.path)["calls"], 1)

    def test_context_preserves_goal_and_observations(self):
        state = step(self.path, scripted_decide)
        messages = build_context(state)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["content"], state["goal"])
        self.assertIn("policy-v1", messages[2]["content"])
        self.assertNotIn("events", messages[2]["content"])

    def test_no_overwrite_or_bad_budget(self):
        with self.assertRaises(FileExistsError):
            create_session(self.path, "scripted")
        with self.assertRaises(ValueError):
            create_session(self.directory / "other.db", "scripted", 0)

    def test_action_contract_boundaries(self):
        for action in (
            [],
            {"kind": "final", "text": ""},
            {"kind": "final", "text": "x", "approved": True},
            {"kind": "tool", "name": "save_note", "arguments": {"text": "x" * 501}},
            {
                "kind": "tool",
                "name": "lookup_policy",
                "arguments": {"topic": "private"},
            },
        ):
            with (
                self.subTest(action=action),
                self.assertRaises((ValueError, TypeError)),
            ):
                validate_action(action)

    def test_cloud_name_rejected(self):
        with self.assertRaises(ValueError):
            OllamaBackend("example:cloud")

    def test_backend_failure_consumes_budget_and_stops(self):
        def unavailable(*_):
            raise OSError("local service unavailable")

        state = step(self.path, unavailable)
        self.assertEqual((state["status"], state["calls"]), ("failed", 1))
        self.assertIn(
            "unavailable", inspect_session(self.path)["events"][-1]["details"]["reason"]
        )

    def test_role_handoff_valid_and_corrupt(self):
        result = researcher({"task_id": "refund-1", "topic": "refund"})
        self.assertTrue(reviewer(result)["accepted"])
        result["days"] = 300
        self.assertFalse(reviewer(result)["accepted"])
        result["days"] = 30
        result["task_id"] = "another"
        self.assertFalse(reviewer(result)["accepted"])

    def test_local_adapter_serialization_without_network(self):
        reply = {
            "done": True,
            "done_reason": "stop",
            "message": {"content": '{"kind":"final","text":"answer"}'},
        }
        with patch("backends.build_opener") as factory:
            factory.return_value.open.return_value.__enter__.return_value.read.return_value = json.dumps(
                reply
            ).encode()
            result = OllamaBackend("existing-local")(
                load(self.path), [{"role": "user", "content": "example"}]
            )
            request = factory.return_value.open.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
            self.assertFalse(payload["stream"])
            self.assertEqual(result, {"kind": "final", "text": "answer"})

    def test_local_adapter_rejects_incomplete_and_oversized(self):
        bodies = [
            json.dumps({"done": True, "done_reason": "length"}).encode(),
            b"x" * 65537,
        ]
        for body in bodies:
            with patch("backends.build_opener") as factory:
                factory.return_value.open.return_value.__enter__.return_value.read.return_value = body
                with self.assertRaises(ValueError):
                    OllamaBackend("existing-local")(load(self.path), [])


if __name__ == "__main__":
    unittest.main()
