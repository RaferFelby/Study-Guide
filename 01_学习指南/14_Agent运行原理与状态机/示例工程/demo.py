import argparse
from pathlib import Path

from agent import approve_pending_action, run_agent
from policy import policy_lookup, policy_repeat, policy_ticket
from recording import play_recording, save_recording
from state import AgentState, Status
from tools import make_tools


def main() -> None:
    parser = argparse.ArgumentParser(description="本地 Agent 状态机教学")
    parser.add_argument(
        "--scenario",
        choices=["lookup", "loop", "limit", "cancel", "confirmation"],
        default="lookup",
    )
    parser.add_argument(
        "--approve", action="store_true", help="仅批准写入本次内存演示工单"
    )
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).parent / "results/trace.json"
    )
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    if args.replay is not None:
        print(play_recording(args.replay))
        return
    ticket_store = []
    tools = make_tools(ticket_store)
    state = AgentState("查询存储保留时间", "demo-run")
    decide = policy_ticket if args.scenario == "confirmation" else policy_lookup
    if args.scenario == "loop":
        decide = policy_repeat
    max_steps = 1 if args.scenario == "limit" else 4
    cancelled = lambda: args.scenario == "cancel"
    run_agent(state, decide, tools, max_steps, cancelled)
    if state.status == Status.WAITING_CONFIRMATION and args.approve:
        approve_pending_action(state)
        run_agent(state, decide, tools, max_steps)
    save_recording(state, args.output)
    print(
        f"状态={state.status.value}，决策步数={state.steps}，内存工单数={len(ticket_store)}"
    )
    print(f"答案={state.final_text}")
    print(f"Trace={args.output.resolve()}")


if __name__ == "__main__":
    main()
