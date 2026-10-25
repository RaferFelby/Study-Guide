"""第 4 讲练习：原地去重、正整数最短窗口和离线日志窗口。"""


def deduplicate_sorted(numbers: list[int]) -> int:
    """原地保留升序整数列表的不同值，返回有效前缀长度，不缩短列表。"""
    for index, value in enumerate(numbers):
        if type(value) is not int:
            raise ValueError("列表元素必须是整数")
        if index > 0 and value < numbers[index - 1]:
            raise ValueError("列表必须按非降序排列")
    if not numbers:
        return 0
    slow = 1
    for fast in range(1, len(numbers)):
        if numbers[fast] != numbers[slow - 1]:
            numbers[slow] = numbers[fast]
            slow += 1
    return slow


def min_positive_subarray_length(numbers: list[int], target: int) -> int:
    """连续子数组元素和至少为 target 的最短长度；无解返回 0。"""
    if type(target) is not int or target <= 0:
        raise ValueError("target 必须是正整数")
    for value in numbers:
        if type(value) is not int or value <= 0:
            raise ValueError("本练习只接受正整数元素")
    left = 0
    window_sum = 0
    best = len(numbers) + 1
    for right, value in enumerate(numbers):
        window_sum += value
        while window_sum >= target:
            best = min(best, right - left + 1)
            window_sum -= numbers[left]
            left += 1
    return 0 if best > len(numbers) else best


def busiest_window(
    timestamps_seconds: list[int], window_seconds: int = 60
) -> tuple[int, int] | None:
    """返回最密集 (结束时刻-window, 结束时刻] 内事件的 [start, stop) 索引。"""
    if type(window_seconds) is not int or window_seconds <= 0:
        raise ValueError("窗口秒数必须是正整数")
    for index, timestamp in enumerate(timestamps_seconds):
        if type(timestamp) is not int or timestamp < 0:
            raise ValueError("时间戳必须是同一时间基准下的非负整数秒")
        if index > 0 and timestamp < timestamps_seconds[index - 1]:
            raise ValueError("日志必须按时间非降序排列")
    if not timestamps_seconds:
        return None
    left = 0
    best_start = 0
    best_stop = 0
    for right, timestamp in enumerate(timestamps_seconds):
        while timestamp - timestamps_seconds[left] >= window_seconds:
            left += 1
        if right - left + 1 > best_stop - best_start:
            best_start = left
            best_stop = right + 1
    return best_start, best_stop
