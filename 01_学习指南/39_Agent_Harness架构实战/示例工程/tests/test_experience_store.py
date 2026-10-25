import sqlite3
import unittest
import uuid
from contextlib import closing
from pathlib import Path

from contrast_lab import BudgetConfig, Expense
from experience_store import (
    add_entry,
    connect_store,
    create_store,
    load_snapshot,
    revoke_entry,
)
from experience_transfer import TaskContext, UnitExperience, run_transfer


class ExperienceStoreTests(unittest.TestCase):
    def setUp(self):
        self.path = Path("results") / f"test-store-{uuid.uuid4().hex}" / "experience.db"
        create_store(self.path)
        self.entry = UnitExperience("task-a", 1, "cny-fen-v1")

    def add(self):
        add_entry(self.path, "units", self.entry, "人工检查单位转换轨迹")

    def test_creation_is_not_visible_until_next_task(self):
        self.add()
        self.assertEqual(load_snapshot(self.path, 1), [])
        self.assertEqual(
            load_snapshot(self.path, 2)[0]["experience"]["status"], "active"
        )

    def test_revocation_preserves_past_snapshot(self):
        self.add()
        before = load_snapshot(self.path, 2)
        revoke_entry(self.path, "units", 3, "需要补核对来源")
        self.assertEqual(load_snapshot(self.path, 2), before)
        self.assertEqual(load_snapshot(self.path, 3), before)
        self.assertEqual(
            load_snapshot(self.path, 4)[0]["experience"]["status"], "revoked"
        )

    def test_snapshot_does_not_modify_database_bytes(self):
        self.add()
        before = self.path.read_bytes()
        load_snapshot(self.path, 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_duplicate_init_and_add_do_not_overwrite(self):
        self.add()
        before = load_snapshot(self.path, 2)
        with self.assertRaises(FileExistsError):
            create_store(self.path)
        with self.assertRaises(ValueError):
            self.add()
        self.assertEqual(load_snapshot(self.path, 2), before)

    def test_cannot_backdate_after_later_event(self):
        self.add()
        revoke_entry(self.path, "units", 3, "暂时撤回")
        with self.assertRaises(ValueError):
            add_entry(self.path, "backdated", UnitExperience("b", 2, "v1"), "旧时间")
        self.assertEqual(len(load_snapshot(self.path, 4)), 1)

    def test_same_order_entries_are_supported_with_stable_order(self):
        self.add()
        add_entry(self.path, "another", self.entry, "同一任务结束时的另一条记录")
        self.assertEqual(
            [row["entry_id"] for row in load_snapshot(self.path, 2)],
            ["another", "units"],
        )

    def test_missing_entry_and_duplicate_revocation_are_rejected(self):
        with self.assertRaises(ValueError):
            revoke_entry(self.path, "missing", 1, "错误编号")
        self.add()
        revoke_entry(self.path, "units", 2, "撤回")
        with self.assertRaises(ValueError):
            revoke_entry(self.path, "units", 3, "重复撤回")

    def test_invalid_inputs_do_not_write_records(self):
        for entry_id, entry, note in (
            ("", self.entry, "说明"),
            ("one", self.entry, " "),
            ("one", UnitExperience("a", True, "v1"), "说明"),
            ("one", UnitExperience("a", 0, "v1"), "说明"),
            ("one", UnitExperience("a", 1, "v1", "revoked"), "说明"),
        ):
            with (
                self.subTest(entry_id=entry_id, entry=entry),
                self.assertRaises(ValueError),
            ):
                add_entry(self.path, entry_id, entry, note)
        self.assertEqual(load_snapshot(self.path, 5), [])
        for order in (0, -1, True, 1.5):
            with self.subTest(order=order), self.assertRaises(ValueError):
                load_snapshot(self.path, order)

    def test_missing_file_does_not_create_database(self):
        missing = self.path.parent / "missing.db"
        with self.assertRaises(ValueError):
            load_snapshot(missing, 2)
        self.assertFalse(missing.exists())

    def test_readonly_connection_refuses_writes(self):
        with (
            connect_store(self.path, readonly=True) as connection,
            self.assertRaises(sqlite3.OperationalError),
        ):
            connection.execute("DELETE FROM entries")

    def test_transaction_rolls_back_partial_write(self):
        with (
            self.assertRaisesRegex(RuntimeError, "故障"),
            connect_store(self.path, readonly=False) as connection,
        ):
            connection.execute("INSERT INTO entries VALUES ('one','a',1,'v1','证据')")
            raise RuntimeError("受控故障")
        self.assertEqual(load_snapshot(self.path, 2), [])

    def test_schema_version_mismatch_is_rejected(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("UPDATE store_meta SET version=2")
        with self.assertRaisesRegex(ValueError, "版本"):
            load_snapshot(self.path, 2)

    def test_loaded_entry_connects_to_existing_trial(self):
        self.add()
        record = load_snapshot(self.path, 2)[0]
        entry = UnitExperience(**record["experience"])
        report = run_transfer(
            entry,
            TaskContext("b", 2, "cny-fen-v1"),
            [Expense("one", 25000, "fen")],
            BudgetConfig(2, False),
            25000,
        )
        self.assertTrue(report["runs"]["candidate"]["evaluation"]["accepted"])
        revoke_entry(self.path, "units", 2, "撤回")
        entry = UnitExperience(**load_snapshot(self.path, 3)[0]["experience"])
        report = run_transfer(
            entry,
            TaskContext("c", 3, "cny-fen-v1"),
            [Expense("one", 25000, "fen")],
            BudgetConfig(2, False),
            25000,
        )
        self.assertEqual(report["skip_reasons"], ["inactive"])
        self.assertEqual(report["runs"], {})


if __name__ == "__main__":
    unittest.main()
