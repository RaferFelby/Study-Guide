import json
from decimal import Decimal

import pytest

from costs import allocate_infrastructure, model_cost
from demo import run_experiments
from pipeline import Pipeline
from reporting import check_slo, percentile_nearest_rank, write_dashboard
from telemetry import SimulatedClock, TraceRecorder
from workload import make_workload


def test_parent_child_duration_and_trace_ids():
    clock = SimulatedClock()
    recorder = TraceRecorder(clock, timing_kind="simulated")
    with recorder.span("task") as parent:
        clock.advance(0.01)
        with recorder.span("tool", {"tool": "search_policy"}) as child:
            clock.advance(0.02)
    assert parent["duration_ms"] == 30 and child["duration_ms"] == 20
    assert child["parent_span_id"] == parent["span_id"]
    assert child["trace_id"] == parent["trace_id"]
    with recorder.span("task") as second:
        pass
    assert second["trace_id"] != parent["trace_id"]


def test_exception_recorded_without_secret_message_and_reraised():
    recorder = TraceRecorder()
    with pytest.raises(TimeoutError), recorder.span("tool"):
        raise TimeoutError("password=private-secret")
    event = recorder.events[0]
    assert event["status"] == "error" and event["error_type"] == "TimeoutError"
    assert "private-secret" not in json.dumps(event)
    assert recorder.active_spans == []
    with (
        pytest.raises(ValueError, match="白名单"),
        recorder.span("task", {"authorization": "secret"}),
    ):
        pass


def test_jsonl_valid_and_no_overwrite(tmp_path):
    recorder = TraceRecorder()
    with recorder.span("task"):
        pass
    path = tmp_path / "trace.jsonl"
    recorder.write_jsonl(path)
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == "task"
    with pytest.raises(FileExistsError):
        recorder.write_jsonl(path)


@pytest.mark.parametrize("counts", [(-1, 2), (True, 2), (1.0, 3)])
def test_cost_rejects_invalid_counts(counts):
    with pytest.raises(ValueError):
        model_cost("large-mock", *counts)


def test_decimal_cost_and_unknown_model_not_free():
    assert model_cost("large-mock", 10, 2) == Decimal("0.014")
    assert allocate_infrastructure(Decimal(2), 4) == Decimal("0.5")
    with pytest.raises(ValueError):
        model_cost("missing", 1, 1)
    with pytest.raises(ValueError):
        allocate_infrastructure(Decimal("NaN"), 2)


def test_quality_cost_cache_and_p95_different_dimensions():
    experiments = run_experiments()
    baseline = experiments["baseline"]["summary"]
    assert baseline["n"] == 24 and baseline["quality"] == 1
    assert baseline["availability"] == 20 / 24
    assert baseline["p95_ms"] == 305 and baseline["cost_units"] == "2.680"
    for name in ("cached", "routed", "cache_routed"):
        summary = experiments[name]["summary"]
        assert summary["quality"] == baseline["quality"]
        assert Decimal(summary["cost_units"]) < Decimal(baseline["cost_units"])
    assert experiments["cached"]["summary"]["cache_hits"] == 10
    assert experiments["bad_crop"]["summary"]["quality"] == 16 / 24
    assert experiments["cached"]["summary"]["p95_ms"] == 305


def test_cache_owner_version_isolation_and_failure_not_cached():
    pipeline = Pipeline("cached")
    input_data = make_workload()[0]["input"]
    assert not pipeline.run(input_data)["cache_hit"]
    assert pipeline.run(input_data)["cache_hit"]
    assert not pipeline.run({**input_data, "owner": "another"})["cache_hit"]
    assert not pipeline.run({**input_data, "knowledge_version": "v2"})["cache_hit"]
    timeout = make_workload()[10]["input"]
    assert not pipeline.run(timeout)["cache_hit"]
    assert not pipeline.run(timeout)["cache_hit"]


def test_trace_correlation_model_usage_and_total_cost_not_double_counted():
    pipeline = Pipeline("baseline")
    row = pipeline.run(make_workload()[0]["input"])
    events = pipeline.recorder.events
    assert all(event["trace_id"] == row["trace_id"] for event in events)
    roots = [event for event in events if event["parent_span_id"] is None]
    assert len(roots) == 1
    model = next(event for event in events if event["name"] == "model")
    assert model["attributes"]["input_tokens"] == row["input_tokens"]
    assert Decimal(row["cost_units"]) == Decimal(
        model["attributes"]["cost_units"]
    ) + Decimal("0.01")


def test_percentile_small_sample_and_invalid_values():
    assert percentile_nearest_rank([1, 2, 3, 4], 0.95) == 4
    with pytest.raises(ValueError):
        percentile_nearest_rank([], 0.95)
    with pytest.raises(ValueError):
        percentile_nearest_rank([float("nan")], 0.95)


def test_slo_window_alert_and_budget():
    rows = [{"output": {"status": "answered"}, "duration_ms": 10}] * 99
    rows += [{"output": {"status": "failed"}, "duration_ms": 10}]
    assert not check_slo(rows)["alert"]
    rows[-1] = {"output": {"status": "answered"}, "duration_ms": 300}
    assert check_slo(rows)["good"] == 99
    rows.append({"output": {"status": "failed"}, "duration_ms": 0})
    assert check_slo(rows)["alert"]


def test_dashboard_escape_and_no_overwrite(tmp_path):
    experiments = run_experiments()
    experiments["<script>alert(1)</script>"] = experiments["baseline"]
    path = tmp_path / "dashboard.html"
    write_dashboard(path, experiments)
    text = path.read_text(encoding="utf-8")
    assert "&lt;script&gt;" in text and "<script>" not in text
    assert "不是线上仪表盘" in text
    with pytest.raises(FileExistsError):
        write_dashboard(path, experiments)


def test_attributes_rechecked_after_update_and_state_cleared():
    recorder = TraceRecorder()
    with pytest.raises(ValueError, match="白名单"), recorder.span("task") as event:
        event["attributes"]["password"] = "private"
    assert recorder.active_spans == [] and recorder.trace_id is None
    assert recorder.events == []
    with (
        pytest.raises(ValueError, match="标量"),
        recorder.span("task", {"model": {"password": "private"}}),
    ):
        pass
