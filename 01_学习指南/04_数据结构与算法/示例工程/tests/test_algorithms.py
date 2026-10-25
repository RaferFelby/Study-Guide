import unittest

from app.algorithms import (
    ListNode,
    LRUCache,
    TreeNode,
    binary_search,
    is_valid_parentheses,
    level_order,
    longest_unique_substring,
    min_cost_climbing_stairs,
    reverse_list,
    shortest_steps,
    subsets,
    top_k_frequent,
    topological_order,
    two_sum,
)


class ArrayAndWindowTests(unittest.TestCase):
    def test_two_sum_handles_duplicates_and_no_solution(self):
        self.assertEqual(two_sum([3, 3], 6), (0, 1))
        self.assertIsNone(two_sum([], 4))

    def test_binary_search_and_longest_window(self):
        self.assertEqual(binary_search([-3, 0, 4, 9], 4), 2)
        self.assertEqual(binary_search([1, 2], 8), -1)
        self.assertEqual(longest_unique_substring("abca"), 3)
        self.assertEqual(longest_unique_substring(""), 0)


class LinkedStructureTests(unittest.TestCase):
    def test_reverse_list(self):
        head = ListNode(1, ListNode(2, ListNode(3)))
        reversed_head = reverse_list(head)
        values = []
        while reversed_head is not None:
            values.append(reversed_head.value)
            reversed_head = reversed_head.next
        self.assertEqual(values, [3, 2, 1])

    def test_parentheses_and_top_k(self):
        self.assertTrue(is_valid_parentheses("([{}])"))
        self.assertFalse(is_valid_parentheses("([)]"))
        self.assertEqual(set(top_k_frequent([1, 1, 1, 2, 2, 3], 2)), {1, 2})
        self.assertEqual(top_k_frequent([], 0), [])


class TreeGraphAndBacktrackingTests(unittest.TestCase):
    def test_level_order_and_shortest_steps(self):
        root = TreeNode(1, TreeNode(2), TreeNode(3, TreeNode(4)))
        self.assertEqual(level_order(root), [[1], [2, 3], [4]])
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(shortest_steps(graph, "A", "D"), 2)
        self.assertIsNone(shortest_steps(graph, "D", "A"))

    def test_topological_order_detects_cycle(self):
        order = topological_order({"A": ["B"], "B": ["C"], "C": []})
        self.assertEqual(order, ["A", "B", "C"])
        with self.assertRaisesRegex(ValueError, "cycle"):
            topological_order({"A": ["B"], "B": ["A"]})

    def test_subsets_and_dynamic_programming(self):
        self.assertEqual(len(subsets([1, 2, 3])), 8)
        self.assertEqual(min_cost_climbing_stairs([10, 15, 20]), 15)
        self.assertEqual(min_cost_climbing_stairs([]), 0)
        self.assertEqual(min_cost_climbing_stairs([7]), 0)


class CacheTests(unittest.TestCase):
    def test_lru_evicts_least_recently_used_item(self):
        cache = LRUCache(2)
        cache.put("a", "A")
        cache.put("b", "B")
        self.assertEqual(cache.get("a"), "A")
        cache.put("c", "C")
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("c"), "C")

    def test_zero_capacity_cache_is_usable(self):
        cache = LRUCache(0)
        cache.put("a", "A")
        self.assertIsNone(cache.get("a"))


if __name__ == "__main__":
    unittest.main()
