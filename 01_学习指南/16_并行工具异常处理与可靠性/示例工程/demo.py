import asyncio
from time import perf_counter

from replanning import plan_next_actions
from scheduler import Request, Scheduler, ToolSpec, merge_facts


async def read_fact(arguments: dict) -> dict:
    await asyncio.sleep(arguments.get("delay_seconds", 0.04))
    return {
        "field": arguments["field"],
        "value": arguments["value"],
        "source": arguments.get("source", "synthetic"),
        "version": 1,
    }


async def long_result(arguments: dict) -> dict:
    return {"text": "这是完整演示资料。" * 100}


async def main() -> None:
    tools = {
        "read_fact": ToolSpec(read_fact, is_read_only=True),
        "long_result": ToolSpec(long_result, is_read_only=True),
    }
    requests = [
        Request("a", "read_fact", {"field": "retention", "value": "30 days"}),
        Request("b", "read_fact", {"field": "capacity", "value": "2 TB"}),
        Request(
            "c", "read_fact", {"field": "contact", "value": "help@example.invalid"}
        ),
    ]
    for parallel in [False, True]:
        scheduler = Scheduler(tools)
        started = perf_counter()
        results = await scheduler.run_batch(requests, parallel=parallel)
        elapsed_ms = (perf_counter() - started) * 1000
        print(
            f"{'并行' if parallel else '串行'}：{elapsed_ms:.1f} ms，成功 {sum(item['ok'] for item in results)}/3"
        )
    conflict_requests = [
        Request(
            "old",
            "read_fact",
            {"field": "retention", "value": "14 days", "source": "old"},
        ),
        Request(
            "new",
            "read_fact",
            {"field": "retention", "value": "30 days", "source": "new"},
        ),
        Request("missing", "not_registered", {}),
    ]
    conflict_results = await Scheduler(tools).run_batch(conflict_requests)
    merged = merge_facts(conflict_results)
    print("部分成功/冲突：", merged)
    print(
        "依据错误的下一步：", plan_next_actions(conflict_results, merged["conflicts"])
    )
    scheduler = Scheduler(tools, max_output_characters=100)
    result = (await scheduler.run_batch([Request("long", "long_result", {})]))[0]
    summary = result["data"]
    print("长输出摘要：", summary)
    print(
        "完整资料长度：", len(scheduler.read_full_result(summary["result_ref"])["text"])
    )


if __name__ == "__main__":
    asyncio.run(main())
