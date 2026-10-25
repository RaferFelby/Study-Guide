import copy
import json
import unittest
import uuid
from pathlib import Path

from contrast_lab import (
    BudgetConfig,
    Expense,
    evaluate_budget,
    execute_budget,
    run_comparison,
    save_report,
)


class ContrastLabTests(unittest.TestCase):
    def setUp(self):
        self.expenses = [Expense("a", 1200, "yuan"), Expense("b", 80000, "fen")]

    def test_four_configs_expose_two_independent_faults(self):
        runs = run_comparison()["runs"]
        for name, total, coverage_ok, total_ok in (
            ("reference", 8120000, False, False),
            ("process", 8150000, True, False),
            ("domain", 200000, False, False),
            ("composed", 230000, True, True),
        ):
            with self.subTest(name=name):
                self.assertEqual(runs[name]["execution"]["total_fen"], total)
                self.assertEqual(runs[name]["evaluation"]["coverage_ok"], coverage_ok)
                self.assertEqual(runs[name]["evaluation"]["total_ok"], total_ok)

    def test_trace_preserves_source_and_conversion(self):
        result = execute_budget(self.expenses, BudgetConfig(None, True))
        self.assertEqual(result["trace"][1]["source_amount"], 80000)
        self.assertEqual(result["trace"][1]["contribution_fen"], 80000)

    def test_execution_does_not_mutate_input_or_other_runs(self):
        before = copy.deepcopy(self.expenses)
        first = execute_budget(self.expenses, BudgetConfig(None, True))
        first["trace"].clear()
        second = execute_budget(self.expenses, BudgetConfig(None, True))
        self.assertEqual(self.expenses, before)
        self.assertEqual(len(second["trace"]), 2)

    def test_matching_total_does_not_hide_omitted_zero_item(self):
        self.expenses.append(Expense("zero", 0, "yuan"))
        result = execute_budget(self.expenses, BudgetConfig(2, True))
        report = evaluate_budget(result, ["a", "b", "zero"], 200000)
        self.assertTrue(report["total_ok"])
        self.assertFalse(report["coverage_ok"])
        self.assertFalse(report["accepted"])

    def test_regressed_config_is_rejected_by_known_answer_check(self):
        result = execute_budget(self.expenses, BudgetConfig(1, True))
        self.assertFalse(evaluate_budget(result, ["a", "b"], 200000)["accepted"])

    def test_duplicate_trace_does_not_pass_coverage(self):
        result = execute_budget(self.expenses, BudgetConfig(None, True))
        result["trace"].append(result["trace"][0].copy())
        self.assertFalse(evaluate_budget(result, ["a", "b"], 200000)["coverage_ok"])

    def test_empty_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "不能为空"):
            execute_budget([], BudgetConfig(None, True))

    def test_invalid_config_is_rejected(self):
        for config in (
            BudgetConfig(0, True),
            BudgetConfig(-1, True),
            BudgetConfig(True, True),
            BudgetConfig(1.5, True),
            BudgetConfig(None, "true"),
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                execute_budget(self.expenses, config)

    def test_invalid_amount_or_unit_is_rejected(self):
        for expense in (
            Expense("a", -1, "yuan"),
            Expense("a", True, "yuan"),
            Expense("a", 1.5, "yuan"),
            Expense("a", 1, "dollar"),
        ):
            with self.subTest(expense=expense), self.assertRaises(ValueError):
                execute_budget([expense], BudgetConfig(None, True))

    def test_empty_or_duplicate_id_is_rejected(self):
        for expenses in ([Expense("", 1, "yuan")], self.expenses + [self.expenses[0]]):
            with self.subTest(expenses=expenses), self.assertRaises(ValueError):
                execute_budget(expenses, BudgetConfig(None, True))

    def test_report_round_trip_and_refusal_to_overwrite(self):
        path = Path("results") / f"test-contrast-{uuid.uuid4().hex}" / "report.json"
        report = run_comparison()
        save_report(report, path)
        before = path.read_bytes()
        self.assertEqual(json.loads(before), report)
        with self.assertRaises(FileExistsError):
            save_report({"wrong": True}, path)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
