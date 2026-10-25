"""第5讲：从枚举到状态表，保留直观的执行顺序。"""

from app.algorithms import subsets


def generate_parentheses(pair_count: int) -> list[str]:
    if type(pair_count) is not int or pair_count < 0:
        raise ValueError("括号对数必须为非负整数")
    results: list[str] = []
    path: list[str] = []

    def visit(left: int, right: int) -> None:
        if left == pair_count and right == pair_count:
            results.append("".join(path))
            return
        if left < pair_count:
            path.append("(")
            visit(left + 1, right)
            path.pop()
        if right < left:
            path.append(")")
            visit(left, right + 1)
            path.pop()

    visit(0, 0)
    return results


def count_stairs_table(step_count: int) -> int:
    if type(step_count) is not int or step_count < 0:
        raise ValueError("阶数必须为非负整数")
    ways = [0] * (step_count + 1)
    ways[0] = 1
    if step_count >= 1:
        ways[1] = 1
    for step in range(2, step_count + 1):
        ways[step] = ways[step - 1] + ways[step - 2]
    return ways[step_count]


def count_stairs_rolling(step_count: int) -> int:
    if type(step_count) is not int or step_count < 0:
        raise ValueError("阶数必须为非负整数")
    if step_count <= 1:
        return 1
    previous_two = 1
    previous_one = 1
    for step in range(2, step_count + 1):
        current = previous_one + previous_two
        previous_two = previous_one
        previous_one = current
    return previous_one


def _validate_tools(tools: list[tuple[str, int, int]], budget: int) -> None:
    if type(budget) is not int or budget < 0:
        raise ValueError("预算必须为非负整数")
    names: set[str] = set()
    for name, cost, value in tools:
        if not name or name in names:
            raise ValueError("工具名必须非空且唯一")
        if type(cost) is not int or type(value) is not int or cost < 0 or value < 0:
            raise ValueError("成本与收益必须为非负整数")
        names.add(name)


def choose_tools_exhaustive(
    tools: list[tuple[str, int, int]], budget: int
) -> tuple[list[str], int]:
    """独立工具，每个最多选一次；返回一个最优组合及其收益。"""
    _validate_tools(tools, budget)
    best_names: list[str] = []
    best_value = 0
    for indices in subsets(list(range(len(tools)))):
        total_cost = 0
        total_value = 0
        names: list[str] = []
        for index in indices:
            name, cost, value = tools[index]
            names.append(name)
            total_cost += cost
            total_value += value
        if total_cost <= budget and total_value > best_value:
            best_names = names
            best_value = total_value
    return best_names, best_value


def best_tool_value_table(tools: list[tuple[str, int, int]], budget: int) -> int:
    """二维0/1背包表，只返回最优收益，不恢复组合。"""
    _validate_tools(tools, budget)
    best = []
    for _ in range(len(tools) + 1):
        best.append([0] * (budget + 1))
    for item in range(1, len(tools) + 1):
        _name, cost, value = tools[item - 1]
        for capacity in range(budget + 1):
            best[item][capacity] = best[item - 1][capacity]
            if cost <= capacity:
                take_value = best[item - 1][capacity - cost] + value
                best[item][capacity] = max(best[item][capacity], take_value)
    return best[len(tools)][budget]
