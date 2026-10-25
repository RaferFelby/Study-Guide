"""Small, readable data-structure and algorithm examples for Unit 04."""

from __future__ import annotations

import heapq
from collections import OrderedDict, deque


def two_sum(numbers: list[int], target: int) -> tuple[int, int] | None:
    seen: dict[int, int] = {}
    for index, value in enumerate(numbers):
        needed = target - value
        if needed in seen:
            return seen[needed], index
        seen[value] = index
    return None


def longest_unique_substring(text: str) -> int:
    left = 0
    last_seen: dict[str, int] = {}
    best = 0
    for right, char in enumerate(text):
        if char in last_seen and last_seen[char] >= left:
            left = last_seen[char] + 1
        last_seen[char] = right
        best = max(best, right - left + 1)
    return best


class ListNode:
    """A singly linked-list node."""

    def __init__(self, value: int, next_node: ListNode | None = None):
        self.value = value
        self.next = next_node


def reverse_list(head: ListNode | None) -> ListNode | None:
    previous = None
    current = head
    while current is not None:
        following = current.next
        current.next = previous
        previous = current
        current = following
    return previous


def is_valid_parentheses(text: str) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for char in text:
        if char in "([{":
            stack.append(char)
        elif char in pairs and (not stack or stack.pop() != pairs[char]):
            return False
    return not stack


def top_k_frequent(values: list[int], k: int) -> list[int]:
    if k < 0:
        raise ValueError("k must be non-negative")
    if k == 0 or not values:
        return []
    counts: dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    if k > len(counts):
        raise ValueError("k cannot exceed the number of distinct values")
    ranked = heapq.nlargest(k, [(count, value) for value, count in counts.items()])
    return [value for _, value in ranked]


class TreeNode:
    """A binary-tree node."""

    def __init__(
        self,
        value: int,
        left: TreeNode | None = None,
        right: TreeNode | None = None,
    ):
        self.value = value
        self.left = left
        self.right = right


def level_order(root: TreeNode | None) -> list[list[int]]:
    if root is None:
        return []
    levels: list[list[int]] = []
    queue = deque([root])
    while queue:
        current_level: list[int] = []
        for _ in range(len(queue)):
            node = queue.popleft()
            current_level.append(node.value)
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        levels.append(current_level)
    return levels


def shortest_steps(graph: dict[str, list[str]], start: str, target: str) -> int | None:
    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        node, distance = queue.popleft()
        if node == target:
            return distance
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))
    return None


def topological_order(graph: dict[str, list[str]]) -> list[str]:
    indegree = {node: 0 for node in graph}
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            indegree.setdefault(neighbor, 0)
            indegree[neighbor] += 1

    ready = deque(node for node, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while ready:
        node = ready.popleft()
        order.append(node)
        for neighbor in graph.get(node, []):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                ready.append(neighbor)
    if len(order) != len(indegree):
        raise ValueError("graph contains a cycle")
    return order


def binary_search(numbers: list[int], target: int) -> int:
    left, right = 0, len(numbers) - 1
    while left <= right:
        middle = left + (right - left) // 2
        if numbers[middle] == target:
            return middle
        if numbers[middle] < target:
            left = middle + 1
        else:
            right = middle - 1
    return -1


def subsets(values: list[int]) -> list[list[int]]:
    result: list[list[int]] = []
    path: list[int] = []

    def backtrack(index: int) -> None:
        if index == len(values):
            result.append(path.copy())
            return
        backtrack(index + 1)
        path.append(values[index])
        backtrack(index + 1)
        path.pop()

    backtrack(0)
    return result


def min_cost_climbing_stairs(cost: list[int]) -> int:
    if len(cost) < 2:
        return 0
    previous_two, previous_one = 0, 0
    for index in range(2, len(cost) + 1):
        current = min(
            previous_one + cost[index - 1],
            previous_two + cost[index - 2],
        )
        previous_two, previous_one = previous_one, current
    return previous_one


class LRUCache:
    """A small educational LRU cache with O(1)-average access."""

    def __init__(self, capacity: int):
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        self.capacity = capacity
        self._items: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> str | None:
        if key not in self._items:
            return None
        self._items.move_to_end(key)
        return self._items[key]

    def put(self, key: str, value: str) -> None:
        if self.capacity == 0:
            return
        self._items[key] = value
        self._items.move_to_end(key)
        if len(self._items) > self.capacity:
            self._items.popitem(last=False)
