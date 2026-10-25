"""同步进度时不能丢失个人安排，也不能把勾选数误算为掌握程度。"""

import pytest
from sync_learning_overview import (
    DISPLAY_END,
    DISPLAY_START,
    collect_task_states,
    progress_for,
    refresh_text,
)


def sample_structure():
    return {
        "units": [
            {
                "map": "unit/map.md",
                "lessons": ["unit/01 first.md", "unit/02 second.md"],
                "optional": ["unit/optional.md"],
            }
        ],
        "first_learning_path": {"phases": [{"lessons": ["unit/01 first.md"]}]},
    }


def sample_table():
    rows = []
    for name in ["unit/map", "unit/01 first", "unit/optional"]:
        rows.append(
            "| 我的课程 | 类型 | 内容 | [["
            + name
            + "\\|正文]] | 受阻 | 周末；实际45分钟 | 待同步 | 自定优先 | 前置 | 产物 | 原因：A\\|B |"
        )
    return (
        "---\nupdated: 2026-10-24\n---\n\n进度快照：待同步\n已勾选汇总：待同步\n\n"
        + "\n".join(rows)
        + "\n"
    )


def test_multiple_tasks_and_code_examples_do_not_inflate_completed_lessons():
    states = collect_task_states(
        "> - [x] [[unit/01 first|跟做]]\n"
        "> - [ ] [[unit/01 first|独立]]\n"
        "```text\n- [x] [[unit/02 second|代码里的示例]]\n```\n"
        "- [x] [[unit/02 second|实际勾选]]\n"
    )
    assert progress_for(["unit/01 first.md", "unit/02 second.md"], states) == (1, 2)


def test_refresh_preserves_manual_schedule_status_priority_and_escaped_notes():
    states = {
        "unit/01 first": [True],
        "unit/02 second": [False],
        "unit/optional": [False],
    }
    updated = refresh_text(sample_table(), sample_structure(), states, "2026-10-25")
    assert "1/2（50%）" in updated
    assert "首次主线 1/1（100%）" in updated
    assert "选修 0/1（0%）" in updated
    assert updated.count("受阻") == 3
    assert updated.count("周末；实际45分钟") == 3
    assert updated.count("自定优先") == 3
    assert updated.count("原因：A\\|B") == 3
    assert refresh_text(updated, sample_structure(), states, "2026-10-25") == updated


def test_missing_task_is_reported_instead_of_assuming_zero_progress():
    with pytest.raises(ValueError, match="完成清单缺少课程任务"):
        refresh_text(sample_table(), sample_structure(), {}, "2026-10-25")


def test_missing_overview_row_is_reported_instead_of_silently_omitting_a_course():
    text = "\n".join(
        line for line in sample_table().splitlines() if "[[unit/optional\\|" not in line
    )
    states = {
        "unit/01 first": [False],
        "unit/02 second": [False],
        "unit/optional": [False],
    }
    with pytest.raises(ValueError, match="总表行范围"):
        refresh_text(text, sample_structure(), states, "2026-10-25")


def test_generated_view_does_not_double_count_rows_and_tracks_manual_plan_changes():
    text = (
        sample_table()
        + "\n"
        + DISPLAY_START
        + "\n\n| 旧显示 |\n|---|\n| 待刷新 |\n\n"
        + DISPLAY_END
        + "\n"
    )
    states = {
        "unit/01 first": [True],
        "unit/02 second": [False],
        "unit/optional": [False],
    }
    updated = refresh_text(text, sample_structure(), states, "2026-10-25")
    generated = updated.split(DISPLAY_START, 1)[1].split(DISPLAY_END, 1)[0]
    assert "**本轮已勾选：1/1 讲。**" in generated
    assert "| 课程与入口 |" in generated
    assert "周末<br>实际45分钟" in generated
    assert "受阻<br>1/1（100%）" in generated
    assert "自定优先" in generated
    assert "待刷新" not in generated
    assert refresh_text(updated, sample_structure(), states, "2026-10-25") == updated


def test_incomplete_display_markers_fail_before_rewriting_user_data():
    states = {
        "unit/01 first": [False],
        "unit/02 second": [False],
        "unit/optional": [False],
    }
    with pytest.raises(ValueError, match="显示区标记不完整"):
        refresh_text(
            sample_table() + "\n" + DISPLAY_START,
            sample_structure(),
            states,
            "2026-10-25",
        )
