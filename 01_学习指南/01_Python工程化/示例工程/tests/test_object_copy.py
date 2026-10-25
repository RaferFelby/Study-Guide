"""检查复制课使用的对象关系与副作用边界。"""

import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, dataclass

from object_copy_demo import add_tag_to_copy


class ObjectCopyTests(unittest.TestCase):
    def test_assignment_shares_the_list(self):
        original = ["T001"]
        alias = original
        alias.append("T002")
        self.assertIs(alias, original)
        self.assertEqual(original, ["T001", "T002"])

    def test_rebinding_does_not_change_the_old_list(self):
        original = ["T001"]
        alias = original
        alias = ["T002"]
        self.assertEqual(original, ["T001"])
        self.assertIsNot(alias, original)

    def test_shallow_copy_shares_nested_objects(self):
        original = [{"tags": ["new"]}]
        copied = original[:]
        copied[0]["tags"].append("urgent")
        copied.append({"tags": []})
        self.assertIsNot(copied, original)
        self.assertIs(copied[0], original[0])
        self.assertEqual(original, [{"tags": ["new", "urgent"]}])
        self.assertEqual(len(copied), 2)

    def test_deep_copy_separates_original_but_preserves_internal_sharing(self):
        shared_tags = ["new"]
        original = [shared_tags, shared_tags]
        copied = deepcopy(original)
        copied[0].append("urgent")
        self.assertIs(copied[0], copied[1])
        self.assertIsNot(copied[0], shared_tags)
        self.assertEqual(shared_tags, ["new"])
        self.assertEqual(copied[1], ["new", "urgent"])

    def test_add_tag_does_not_change_original_or_other_nested_fields(self):
        original = {"id": "T001", "tags": [], "details": {"owner": "A"}}
        changed = add_tag_to_copy(original, "checked")
        changed["details"]["owner"] = "B"
        self.assertEqual(
            original, {"id": "T001", "tags": [], "details": {"owner": "A"}}
        )
        self.assertEqual(changed["tags"], ["checked"])

    def test_invalid_input_is_rejected_without_mutation(self):
        original = {"tags": ["new"]}
        for tag in ("", "  "):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                add_tag_to_copy(original, tag)
        self.assertEqual(original, {"tags": ["new"]})
        for tag in (1, None):
            with self.subTest(tag=tag), self.assertRaises(TypeError):
                add_tag_to_copy(original, tag)
        for ticket in ([], {}, {"tags": "new"}):
            with self.subTest(ticket=ticket), self.assertRaises(TypeError):
                add_tag_to_copy(ticket, "checked")

    def test_frozen_dataclass_does_not_freeze_nested_list(self):
        @dataclass(frozen=True)
        class Task:
            tags: list[str]

        task = Task(["new"])
        task.tags.append("urgent")
        self.assertEqual(task.tags, ["new", "urgent"])
        with self.assertRaises(FrozenInstanceError):
            task.tags = []

    def test_slices_use_exclusive_stop_and_allow_empty_result(self):
        values = [10, 20, 30, 40]
        self.assertEqual(values[1:3], [20, 30])
        self.assertEqual(values[-2:], [30, 40])
        self.assertEqual(values[9:], [])
        self.assertEqual(values[:], values)
        self.assertIsNot(values[:], values)


if __name__ == "__main__":
    unittest.main()
