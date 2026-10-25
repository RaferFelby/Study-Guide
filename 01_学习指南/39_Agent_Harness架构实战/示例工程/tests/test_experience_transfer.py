import unittest
from dataclasses import replace

from contrast_lab import BudgetConfig, Expense
from experience_transfer import (
    TaskContext,
    UnitExperience,
    propose_unit_config,
    review_experience,
    run_examples,
    run_transfer,
)


class ExperienceTransferTests(unittest.TestCase):
    def setUp(self):
        self.entry = UnitExperience("a", 1, "v1")
        self.context = TaskContext("b", 2, "v1")
        self.expenses = [Expense("one", 600, "yuan"), Expense("two", 25000, "fen")]
        self.base = BudgetConfig(2, False)

    def test_earlier_matching_entry_can_be_tried(self):
        self.assertEqual(review_experience(self.entry, self.context, self.expenses), [])

    def test_new_answer_is_computed_from_current_data(self):
        report = run_transfer(self.entry, self.context, self.expenses, self.base, 85000)
        self.assertFalse(report["runs"]["base"]["evaluation"]["accepted"])
        self.assertEqual(report["runs"]["candidate"]["execution"]["total_fen"], 85000)
        self.assertTrue(report["runs"]["candidate"]["evaluation"]["accepted"])

    def test_config_patch_preserves_budget_and_base(self):
        candidate = propose_unit_config(
            self.entry, self.context, self.expenses, self.base
        )
        self.assertEqual(candidate, BudgetConfig(2, True))
        self.assertEqual(self.base, BudgetConfig(2, False))

    def test_matching_scope_does_not_guarantee_success(self):
        rows = self.expenses + [Expense("three", 50, "yuan")]
        report = run_transfer(self.entry, self.context, rows, self.base, 90000)
        self.assertEqual(report["skip_reasons"], [])
        self.assertFalse(report["runs"]["candidate"]["evaluation"]["accepted"])

    def test_equal_or_future_availability_is_rejected(self):
        for position in (2, 3):
            with self.subTest(position=position):
                entry = replace(self.entry, available_after=position)
                self.assertIn(
                    "not_available_yet",
                    review_experience(entry, self.context, self.expenses),
                )

    def test_same_task_is_rejected_even_with_claimed_early_time(self):
        entry = replace(self.entry, source_task_id="b")
        self.assertIn(
            "same_task", review_experience(entry, self.context, self.expenses)
        )

    def test_revoked_and_changed_rule_are_rejected(self):
        for entry, reason in (
            (replace(self.entry, status="revoked"), "inactive"),
            (replace(self.entry, rule_version="v0"), "rule_mismatch"),
        ):
            with self.subTest(reason=reason):
                self.assertIn(
                    reason, review_experience(entry, self.context, self.expenses)
                )

    def test_unsupported_unit_is_skipped_before_execution(self):
        rows = [Expense("one", 10, "dollar")]
        report = run_transfer(self.entry, self.context, rows, self.base, 0)
        self.assertEqual(report["skip_reasons"], ["unsupported_unit"])
        self.assertEqual(report["runs"], {})

    def test_rejected_entry_cannot_be_applied(self):
        with self.assertRaisesRegex(ValueError, "inactive"):
            propose_unit_config(
                replace(self.entry, status="revoked"),
                self.context,
                self.expenses,
                self.base,
            )

    def test_invalid_metadata_is_not_silently_accepted(self):
        for entry in (
            replace(self.entry, available_after=0),
            replace(self.entry, available_after=True),
            replace(self.entry, status="unknown"),
            replace(self.entry, rule_version=" "),
            replace(self.entry, source_task_id=""),
        ):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                review_experience(entry, self.context, self.expenses)
        with self.assertRaises(ValueError):
            review_experience(
                self.entry, replace(self.context, task_order=1.5), self.expenses
            )
        with self.assertRaises(ValueError):
            review_experience(self.entry, self.context, [])

    def test_expected_answer_does_not_change_candidate(self):
        first = run_transfer(self.entry, self.context, self.expenses, self.base, 85000)
        second = run_transfer(self.entry, self.context, self.expenses, self.base, 0)
        self.assertEqual(
            first["runs"]["candidate"]["execution"],
            second["runs"]["candidate"]["execution"],
        )
        self.assertFalse(second["runs"]["candidate"]["evaluation"]["accepted"])

    def test_seven_cases_are_independent(self):
        cases = run_examples()["cases"]
        self.assertEqual(len(cases), 7)
        self.assertEqual(
            cases["new_task"]["base_config"], cases["over_budget"]["base_config"]
        )
        for name in ("future", "same_task", "revoked", "changed_rule", "unknown_unit"):
            with self.subTest(name=name):
                self.assertEqual(cases[name]["runs"], {})


if __name__ == "__main__":
    unittest.main()
