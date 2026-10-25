import itertools
import unittest

from app.algorithms import TreeNode, is_valid_parentheses, shortest_steps
from app.dynamic_programming import (
    best_tool_value_table,
    choose_tools_exhaustive,
    count_stairs_rolling,
    count_stairs_table,
    generate_parentheses,
)
from app.graph_practice import (
    has_path_bfs,
    has_path_dfs,
    max_depth,
    plan_workflow,
    preorder,
)


class GraphPracticeTests(unittest.TestCase):
    def test_tree_order_and_depth_include_empty_tree(self):
        root = TreeNode(1, TreeNode(2, TreeNode(4)), TreeNode(3))
        self.assertEqual(preorder(root), [1, 2, 4, 3])
        self.assertEqual(max_depth(root), 3)
        self.assertEqual(preorder(None), [])
        self.assertEqual(max_depth(None), 0)

    def test_search_reaches_nodes_without_looping_on_cycles(self):
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": ["A"], "E": []}
        for search in (has_path_dfs, has_path_bfs):
            with self.subTest(search=search.__name__):
                self.assertTrue(search(graph, "A", "D"))
                self.assertTrue(search(graph, "A", "A"))
                self.assertFalse(search(graph, "A", "E"))
                self.assertFalse(search(graph, "missing", "A"))
                self.assertFalse(search({}, "A", "A"))

    def test_search_matches_shortest_steps_on_all_three_node_graphs(self):
        nodes = ["A", "B", "C"]
        edges = list(itertools.product(nodes, repeat=2))
        for present in itertools.product((False, True), repeat=len(edges)):
            graph = {node: [] for node in nodes}
            for (left, right), include in zip(edges, present):
                if include:
                    graph[left].append(right)
            for start, target in itertools.product(nodes, repeat=2):
                expected = shortest_steps(graph, start, target) is not None
                self.assertEqual(has_path_dfs(graph, start, target), expected)
                self.assertEqual(has_path_bfs(graph, start, target), expected)

    def test_workflow_order_respects_every_dependency(self):
        tasks = ["read", "search", "summarize", "save"]
        dependencies = [
            ("read", "search"),
            ("search", "summarize"),
            ("summarize", "save"),
        ]
        order = plan_workflow(tasks, dependencies)
        self.assertEqual(set(order), set(tasks))
        for before, after in dependencies:
            self.assertLess(order.index(before), order.index(after))
        self.assertEqual(plan_workflow([], []), [])
        self.assertEqual(set(plan_workflow(["A", "B"], [])), {"A", "B"})

    def test_workflow_rejects_bad_dependencies_and_cycles(self):
        cases = [
            (["A", "A"], []),
            ([""], []),
            (["A"], [("A", "B")]),
            (["A", "B"], [("A", "B"), ("A", "B")]),
            (["A", "B"], [("A", "B"), ("B", "A")]),
            (["A"], [("A", "A")]),
        ]
        for tasks, dependencies in cases:
            with (
                self.subTest(tasks=tasks, dependencies=dependencies),
                self.assertRaises(ValueError),
            ):
                plan_workflow(tasks, dependencies)


class DynamicProgrammingTests(unittest.TestCase):
    def test_parentheses_match_exhaustive_filter_for_small_sizes(self):
        for pair_count in range(5):
            expected = set()
            for chars in itertools.product("()", repeat=2 * pair_count):
                candidate = "".join(chars)
                if is_valid_parentheses(candidate):
                    expected.add(candidate)
            actual = generate_parentheses(pair_count)
            self.assertEqual(set(actual), expected)
            self.assertEqual(len(actual), len(set(actual)))
        for invalid in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                generate_parentheses(invalid)

    def test_stair_counts_match_direct_enumeration(self):
        def enumerate_paths(steps):
            if steps == 0:
                return 1
            if steps < 0:
                return 0
            return enumerate_paths(steps - 1) + enumerate_paths(steps - 2)

        for steps in range(11):
            expected = enumerate_paths(steps)
            self.assertEqual(count_stairs_table(steps), expected)
            self.assertEqual(count_stairs_rolling(steps), expected)
        for count in (count_stairs_table, count_stairs_rolling):
            for invalid in (-1, 1.5, True):
                with self.assertRaises(ValueError):
                    count(invalid)

    def test_knapsack_table_matches_independent_subset_enumeration(self):
        for costs in itertools.product(range(3), repeat=3):
            tools = [(str(index), cost, index + 1) for index, cost in enumerate(costs)]
            for budget in range(5):
                expected = 0
                for selected in itertools.product((False, True), repeat=3):
                    cost = sum(tool[1] for tool, take in zip(tools, selected) if take)
                    value = sum(tool[2] for tool, take in zip(tools, selected) if take)
                    if cost <= budget:
                        expected = max(expected, value)
                names, value = choose_tools_exhaustive(tools, budget)
                self.assertEqual(value, expected)
                self.assertEqual(best_tool_value_table(tools, budget), expected)
                self.assertLessEqual(
                    sum(tool[1] for tool in tools if tool[0] in names), budget
                )

    def test_budget_examples_and_invalid_inputs(self):
        tools = [("A", 6, 12), ("B", 5, 9), ("C", 5, 9)]
        self.assertEqual(choose_tools_exhaustive(tools, 10), (["B", "C"], 18))
        self.assertEqual(best_tool_value_table([], 0), 0)
        self.assertEqual(best_tool_value_table([("free", 0, 3)], 0), 3)
        for invalid_tools, budget in [
            ([], -1),
            ([], 1.5),
            ([("A", 1.5, 2)], 3),
            ([("A", 1, True)], 3),
            ([("A", -1, 2)], 3),
            ([("A", 1, -2)], 3),
            ([("A", 1, 1), ("A", 2, 3)], 3),
        ]:
            for solve in (choose_tools_exhaustive, best_tool_value_table):
                with self.assertRaises(ValueError):
                    solve(invalid_tools, budget)


if __name__ == "__main__":
    unittest.main()
