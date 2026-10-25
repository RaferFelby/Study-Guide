import unittest

from contracts import (
    POLICY,
    action_key,
    evaluate_final,
    parse_refund_claim,
    verify_final,
)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.answer = "30 天内申请退款 [policy-v1]"
        self.note_action = {
            "kind": "tool",
            "name": "save_note",
            "arguments": {"text": self.answer},
        }
        self.key = action_key(self.note_action)
        self.state = {
            "observations": [
                {"name": "lookup_policy", "result": POLICY.copy()},
                {
                    "name": "save_note",
                    "action_key": self.key,
                    "result": {"saved": True, "scope": "local_learning_note"},
                },
            ]
        }
        self.notes = {self.key: self.answer}

    def test_exact_claim_parses_to_fields(self):
        self.assertEqual(
            parse_refund_claim(self.answer), {"days": 30, "source": "policy-v1"}
        )

    def test_unsupported_text_is_not_guessed(self):
        for text in (
            None,
            "",
            "不是 " + self.answer,
            self.answer + " 但实际300天",
            "030 天内申请退款 [policy-v1]",
            "购买后30天内退款",
        ):
            with self.subTest(text=text):
                self.assertIsNone(parse_refund_claim(text))

    def test_all_evidence_accepts(self):
        report = evaluate_final(self.state, self.answer, self.notes)
        self.assertTrue(report["accepted"])
        self.assertEqual(report["failed_checks"], [])

    def test_wrong_days_source_or_negation_rejected_after_execution(self):
        for text in (
            "300 天内申请退款 [policy-v1]",
            "不是 " + self.answer,
            "30 天内申请退款 [policy-v2]",
            self.answer + " 或者300天",
        ):
            with self.subTest(text=text):
                report = evaluate_final(self.state, text, self.notes)
                self.assertTrue(report["execution_completed"])
                self.assertFalse(report["answer_correct"])
                self.assertFalse(report["accepted"])

    def test_correct_answer_with_wrong_committed_note_rejected(self):
        self.note_action["arguments"]["text"] = "300 天内申请退款 [policy-v1]"
        key = action_key(self.note_action)
        self.state["observations"][1]["action_key"] = key
        report = evaluate_final(
            self.state, self.answer, {key: self.note_action["arguments"]["text"]}
        )
        self.assertTrue(report["execution_completed"])
        self.assertTrue(report["answer_correct"])
        self.assertFalse(report["note_correct"])
        self.assertFalse(report["accepted"])

    def test_receipt_without_database_row_rejected(self):
        report = evaluate_final(self.state, self.answer, {})
        self.assertFalse(report["execution_completed"])
        self.assertIn("note_committed", report["failed_checks"])

    def test_database_row_without_receipt_rejected(self):
        self.state["observations"].pop()
        self.assertFalse(
            evaluate_final(self.state, self.answer, self.notes)["accepted"]
        )

    def test_false_save_receipt_rejected(self):
        self.state["observations"][1]["result"]["saved"] = False
        self.assertFalse(
            evaluate_final(self.state, self.answer, self.notes)["accepted"]
        )

    def test_note_changed_after_approval_rejected(self):
        self.notes[self.key] = "300 天内申请退款 [policy-v1]"
        report = evaluate_final(self.state, self.answer, self.notes)
        self.assertIn("note_matches_approval", report["failed_checks"])

    def test_missing_or_changed_source_evidence_rejected(self):
        for observations in (
            [],
            [
                {
                    "name": "lookup_policy",
                    "result": {"source": "policy-v1", "text": "300天"},
                }
            ],
        ):
            state = {"observations": observations + self.state["observations"][1:]}
            self.assertFalse(evaluate_final(state, self.answer, self.notes)["accepted"])

    def test_extra_note_is_not_ignored(self):
        self.notes["unrelated"] = self.answer
        self.assertFalse(
            evaluate_final(self.state, self.answer, self.notes)["accepted"]
        )

    def test_boolean_entry_requires_real_note_evidence(self):
        self.assertFalse(verify_final(self.state, self.answer))
        self.assertTrue(verify_final(self.state, self.answer, self.notes))


if __name__ == "__main__":
    unittest.main()
