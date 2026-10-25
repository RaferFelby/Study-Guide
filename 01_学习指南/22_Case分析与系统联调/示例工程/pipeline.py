import json
import time
from uuid import uuid4

from contracts import AccessDeniedError, Settings, ToolContractError
from parsing import parse_model_output
from tools import AccountTool


def run_pipeline(input_data: dict, settings: Settings):
    trace_id = uuid4().hex
    events = []
    started = time.perf_counter()
    tool = AccountTool(input_data["transient_failures"])
    output = {"status": "failed", "days": None}

    def record(stage, status, code, details=None):
        events.append(
            {
                "trace_id": trace_id,
                "stage": stage,
                "status": status,
                "code": code,
                "details": dict(details or {}),
            }
        )

    question = input_data["question"]
    known = question in {"退款期限", "账户退款期限"} or (
        settings.use_aliases and question == "退钱窗口"
    )
    record(
        "retrieval",
        "ok" if known else "missing",
        "evidence_found" if known else "no_evidence",
    )
    if not known:
        output = {"status": "refused", "days": None}
    else:
        argument_name = "owner"
        if question == "账户退款期限" and not settings.correct_argument_name:
            argument_name = "account"
        arguments = {argument_name: input_data["target"]}
        record("planning", "ok", "proposed_read", {"argument_keys": list(arguments)})
        data = None
        for attempt in range(settings.max_attempts):
            try:
                data = tool.query(
                    arguments, input_data["actor"], settings.enforce_owner
                )
            except AccessDeniedError:
                record("authorization", "deny", "owner_mismatch")
                output = {"status": "refused", "days": None}
                break
            except ToolContractError:
                record("tool", "error", "invalid_arguments")
                break
            except TimeoutError:
                record("tool", "error", "upstream_timeout", {"attempt": attempt + 1})
                if attempt + 1 == settings.max_attempts:
                    break
            else:
                record("tool", "ok", "read_completed", {"attempt": attempt + 1})
                break
        if data is not None:
            model_text = json.dumps({"status": "answered", "days": data["days"]})
            if input_data["format"] == "markdown_json":
                model_text = "```json\n" + model_text + "\n```"
            record(
                "model", "ok", "mock_output_generated", {"format": input_data["format"]}
            )
            try:
                output = parse_model_output(model_text, settings.accept_json_fence)
            except ValueError:
                record("parsing", "error", "invalid_output")
            else:
                record("parsing", "ok", "schema_valid")
    record("task", output["status"], "finished")
    return {
        "trace_id": trace_id,
        "output": output,
        "events": events,
        "tool_attempts": tool.attempts,
        "actual_reads": tool.reads,
        "duration_ms_measured": (time.perf_counter() - started) * 1000,
    }
