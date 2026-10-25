"""离散轮次模拟，不测GPU；展示完成后是否补入新请求。"""

import math


def simulate_schedule(continuous=True):
    jobs = [
        {"id": "A", "arrival": 0, "length": 2},
        {"id": "B", "arrival": 0, "length": 5},
        {"id": "C", "arrival": 1, "length": 1},
    ]
    pending = list(jobs)
    active = []
    remaining = {job["id"]: job["length"] for job in jobs}
    completed = {}
    trace = []
    for tick in range(20):
        if continuous or not active:
            ready = [job for job in pending if job["arrival"] <= tick]
            for job in ready[: 2 - len(active)]:
                active.append(job)
                pending.remove(job)
        trace.append({"tick": tick, "active": [job["id"] for job in active]})
        for job in list(active):
            if remaining[job["id"]] == 0:
                continue
            remaining[job["id"]] -= 1
            if remaining[job["id"]] == 0:
                completed[job["id"]] = tick + 1
                if continuous:
                    active.remove(job)
        if (
            not continuous
            and active
            and all(remaining[job["id"]] <= 0 for job in active)
        ):
            active.clear()
        if not active and not pending:
            break
    return {
        "mode": "continuous" if continuous else "static",
        "completed_tick": completed,
        "trace": trace,
        "scope": "discrete_simulation_not_model_throughput",
    }


def page_allocation(lengths, block_size=4):
    if (
        type(block_size) is not int
        or block_size < 1
        or not lengths
        or any(type(length) is not int or length < 1 for length in lengths)
    ):
        raise ValueError("长度与块大小需正整数")
    blocks = [math.ceil(length / block_size) for length in lengths]
    allocated = sum(blocks) * block_size
    return {
        "blocks": blocks,
        "used_slots": sum(lengths),
        "allocated_slots": allocated,
        "unused_slots": allocated - sum(lengths),
    }
