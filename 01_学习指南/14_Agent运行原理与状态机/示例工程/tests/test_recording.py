import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from agent import approve_pending_action, run_agent
from policy import policy_ticket
from recording import play_recording, save_recording
from state import AgentState
from tools import make_tools


def test_playback_uses_recorded_results_and_has_no_write():
    state = AgentState("演示工单", "test")
    store = []
    tools = make_tools(store)
    run_agent(state, policy_ticket, tools)
    approve_pending_action(state)
    run_agent(state, policy_ticket, tools)
    with TemporaryDirectory(dir=Path(__file__).parent) as directory:
        path = Path(directory) / "trace.json"
        save_recording(state, path)
        replay = play_recording(path)
        assert replay["status"] == state.status.value
        assert replay["final_text"] == state.final_text
        assert len(replay["observations"]) == 1
        assert len(store) == 1
        # 修改顺序后，播放器应拒绝伪造的连续轨迹。
        recording = json.loads(path.read_text(encoding="utf-8"))
        recording["trace"][0]["sequence"] = 9
        path.write_text(json.dumps(recording), encoding="utf-8")
        with pytest.raises(ValueError, match="顺序"):
            play_recording(path)
