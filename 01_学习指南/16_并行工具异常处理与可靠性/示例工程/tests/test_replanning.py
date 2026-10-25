import pytest

from replanning import plan_next_actions
from scheduler import error_result


@pytest.mark.parametrize(
    "code,action",
    [
        ("outcome_unknown", "verify_write_status"),
        ("invalid_arguments_or_result", "repair_arguments_or_adapter"),
        ("circuit_open", "defer_or_use_authorized_fallback"),
        ("rate_limited", "defer_or_use_authorized_fallback"),
        ("timeout", "report_exhausted_attempts_or_choose_alternative"),
        ("unknown_tool", "report_unavailable"),
    ],
)
def test_public_error_code_drives_next_action(code, action):
    result = {"call_id": "a", **error_result(code, "example")}
    assert plan_next_actions([result])[0]["next_action"] == action


def test_summary_requires_full_result_instead_of_guessing():
    result = {"call_id": "a", "ok": True, "data": {"is_summary": True}}
    assert plan_next_actions([result])[0]["next_action"] == "read_full_result"


def test_conflicting_field_is_verified_before_use():
    result = {
        "call_id": "a",
        "ok": True,
        "data": {
            "is_summary": False,
            "content": {"field": "retention", "value": "14 days"},
        },
    }
    assert (
        plan_next_actions([result], [{"field": "retention"}])[0]["next_action"]
        == "verify_source_conflict"
    )
