"""第3讲的树遍历、可达性和工作流练习。"""

from collections import deque

from app.algorithms import TreeNode, topological_order


def preorder(root: TreeNode | None) -> list[int]:
    values: list[int] = []

    def visit(node: TreeNode | None) -> None:
        if node is None:
            return
        values.append(node.value)
        visit(node.left)
        visit(node.right)

    visit(root)
    return values


def max_depth(root: TreeNode | None) -> int:
    if root is None:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))


def has_path_dfs(graph: dict[str, list[str]], start: str, target: str) -> bool:
    """节点须列为字典键；不存在的起点或终点返回False。"""
    if start not in graph or target not in graph:
        return False
    stack = [start]
    visited = {start}
    while stack:
        node = stack.pop()
        if node == target:
            return True
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                stack.append(neighbor)
    return False


def has_path_bfs(graph: dict[str, list[str]], start: str, target: str) -> bool:
    """与DFS相同的输入契约，使用队列逐层访问。"""
    if start not in graph or target not in graph:
        return False
    queue = deque([start])
    visited = {start}
    while queue:
        node = queue.popleft()
        if node == target:
            return True
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return False


def plan_workflow(tasks: list[str], dependencies: list[tuple[str, str]]) -> list[str]:
    """(前置任务, 后续任务)表示有向边；只规划顺序，不执行工具。"""
    graph: dict[str, list[str]] = {}
    for task in tasks:
        if not task or task in graph:
            raise ValueError("任务名必须非空且唯一")
        graph[task] = []
    for prerequisite, following in dependencies:
        if prerequisite not in graph or following not in graph:
            raise ValueError("依赖中的任务必须先列在任务清单中")
        if following in graph[prerequisite]:
            raise ValueError("同一依赖不能重复列出")
        graph[prerequisite].append(following)
    return topological_order(graph)
