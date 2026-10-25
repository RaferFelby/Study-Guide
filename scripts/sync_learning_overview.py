"""同步学习总表的勾选进度，保留手填计划、状态和备注。"""

import argparse
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERVIEW = ROOT / "02_学习记录" / "02 学习总表.md"
CHECKLIST = ROOT / "02_学习记录" / "01 全课程完成清单.md"
AUTOMATIC_STATUSES = {"待确认", "有完成记录", "课次已勾完"}
DISPLAY_START = "<!-- learning-overview-display:start -->"
DISPLAY_END = "<!-- learning-overview-display:end -->"


def render_reading_view(structure, rows):
    """用完整表的同一份数据生成窄屏可读的五列视图。"""
    first_lessons = [
        name
        for phase in structure["first_learning_path"]["phases"]
        for name in phase["lessons"]
    ]
    completed = sum(
        int(rows[name.removesuffix(".md")][6].split("/", 1)[0])
        for name in first_lessons
    )
    lines = [f"**本轮已勾选：{completed}/{len(first_lessons)} 讲。**", ""]
    for index, phase in enumerate(structure["first_learning_path"]["phases"], 1):
        heading = phase.get("heading", f"阶段 {index}")
        lines.extend(
            [
                "### " + heading,
                "",
                "| 课程与入口 | 学习重点 | 建议安排 | 状态与进度 | 优先级 |",
                "|---|---|---|---|---|",
            ]
        )
        for name in phase["lessons"]:
            key = name.removesuffix(".md")
            cells = rows[key]
            title = "[[" + key + "\\|" + cells[0] + "]]"
            links = re.findall(r"\[\[([^\]]+)\]\]", cells[3])
            if len(links) > 1:
                title += "<br>[[" + links[1] + "]]"
            schedule = cells[5].replace("；", "<br>", 1)
            status = cells[4] + "<br>" + cells[6]
            priority = "A · 必学" if cells[7] == "A：当前必学" else cells[7]
            lines.append(
                "| " + " | ".join([title, cells[2], schedule, status, priority]) + " |"
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def collect_task_states(text):
    """同一课程有多个任务时，只有全部勾选才计为完成一讲。"""
    states = {}
    fence = False
    for line in text.splitlines():
        stripped = re.sub(r"^\s*(?:>\s*)+", "", line)
        if re.match(r"^\s*(`{3,}|~{3,})", stripped):
            fence = not fence
            continue
        if fence:
            continue
        task = re.match(r"^\s*- \[([ xX])\]", stripped)
        if task is None:
            continue
        for link in re.findall(r"\[\[([^\]]+)\]\]", stripped):
            name = link.replace("\\|", "|").split("|", 1)[0].split("#", 1)[0]
            states.setdefault(name.removesuffix(".md"), []).append(
                task[1].lower() == "x"
            )
    return states


def progress_for(lessons, task_states):
    completed = 0
    for name in lessons:
        key = name.removesuffix(".md")
        if key not in task_states:
            raise ValueError(f"完成清单缺少课程任务：{name}")
        if all(task_states[key]):
            completed += 1
    total = len(lessons)
    if total == 0:
        raise ValueError("不能对空课程范围计算进度")
    return completed, total


def progress_text(completed, total):
    return f"{completed}/{total}（{completed / total:.0%}）"


def refresh_text(text, structure, task_states, as_of):
    start_count = text.count(DISPLAY_START)
    end_count = text.count(DISPLAY_END)
    if (start_count, end_count) not in {(0, 0), (1, 1)}:
        raise ValueError("简明显示区标记不完整，请保留一对开始与结束标记")
    scopes = {}
    main_lessons = []
    optional_lessons = []
    for unit in structure["units"]:
        scopes[unit["map"].removesuffix(".md")] = unit["lessons"]
        main_lessons.extend(unit["lessons"])
        optional_lessons.extend(unit["optional"])
        for name in unit["lessons"] + unit["optional"]:
            scopes[name.removesuffix(".md")] = [name]
    first_lessons = []
    for phase in structure["first_learning_path"]["phases"]:
        first_lessons.extend(phase["lessons"])

    expected_rows = {unit["map"].removesuffix(".md") for unit in structure["units"]}
    expected_rows.update(
        name.removesuffix(".md") for name in first_lessons + optional_lessons
    )
    seen_rows = set()
    rows = {}
    inside_display = False
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line == DISPLAY_START:
            inside_display = True
            continue
        if line == DISPLAY_END:
            if not inside_display:
                raise ValueError("简明显示区的结束标记不能位于开始标记之前")
            inside_display = False
            continue
        if inside_display:
            continue
        prefix = "> " if line.startswith("> ") else ""
        body = line[len(prefix) :].strip()
        if not body.startswith("|") or not body.endswith("|"):
            continue
        cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", body[1:-1])]
        if cells[0] == "名称" or re.fullmatch(r"[-: ]+", cells[0]):
            continue
        if len(cells) != 11:
            raise ValueError("总表数据行应有 11 列，请检查未转义的竖线")
        links = re.findall(r"\[\[([^\]]+)\]\]", cells[3])
        if not links:
            raise ValueError(f"总表缺少路径链接：{cells[0]}")
        key = links[0].replace("\\|", "|").split("|", 1)[0].split("#", 1)[0]
        if key not in scopes:
            raise ValueError(f"总表路径不在课程清单中：{key}")
        if key in seen_rows:
            raise ValueError(f"总表重复列出同一路径：{key}")
        seen_rows.add(key)
        completed, total = progress_for(scopes[key], task_states)
        cells[6] = progress_text(completed, total)
        if cells[4] in AUTOMATIC_STATUSES:
            cells[4] = (
                "课次已勾完"
                if completed == total
                else "有完成记录"
                if completed
                else "待确认"
            )
        rows[key] = cells
        lines[index] = prefix + "| " + " | ".join(cells) + " |"

    if seen_rows != expected_rows:
        raise ValueError("总表行范围与课程清单不一致，请核对单元、首次主线和选修")
    result = "\n".join(lines) + "\n"
    if start_count:
        display = DISPLAY_START + "\n\n" + render_reading_view(structure, rows)
        display += "\n\n" + DISPLAY_END
        result = re.sub(
            re.escape(DISPLAY_START) + r".*?" + re.escape(DISPLAY_END),
            lambda match: display,
            result,
            count=1,
            flags=re.DOTALL,
        )
    result = re.sub(
        r"^updated: \d{4}-\d{2}-\d{2}$",
        f"updated: {as_of}",
        result,
        count=1,
        flags=re.MULTILINE,
    )
    result = re.sub(
        r"^进度快照：.*$",
        f"进度快照：{as_of}；依据原完成清单，不代表熟练度。",
        result,
        count=1,
        flags=re.MULTILINE,
    )
    summary = (
        "已勾选汇总：首次主线 "
        + progress_text(*progress_for(first_lessons, task_states))
        + "；单元正文 "
        + progress_text(*progress_for(main_lessons, task_states))
        + "；选修 "
        + progress_text(*progress_for(optional_lessons, task_states))
        + "。首次主线包含在单元正文中，不重复累计。"
    )
    result = re.sub(r"^已勾选汇总：.*$", summary, result, count=1, flags=re.MULTILINE)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="只检查是否需要同步，不写入"
    )
    parser.add_argument("--as-of", help="明确指定快照日期，格式为 YYYY-MM-DD")
    args = parser.parse_args()
    as_of = args.as_of or datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of):
        parser.error("快照日期应为 YYYY-MM-DD")
    date.fromisoformat(as_of)
    structure = json.loads(
        (ROOT / "scripts" / "guide_structure.json").read_text(encoding="utf-8")
    )
    states = collect_task_states(CHECKLIST.read_text(encoding="utf-8"))
    original = OVERVIEW.read_text(encoding="utf-8")
    updated = refresh_text(original, structure, states, as_of)
    if args.check:
        print("总表进度已同步" if original == updated else "总表需要同步")
        raise SystemExit(0 if original == updated else 1)
    if original != updated:
        OVERVIEW.write_text(updated, encoding="utf-8")
    print("总表进度已同步；手填状态、时间安排、重要程度和备注保留")


if __name__ == "__main__":
    main()
