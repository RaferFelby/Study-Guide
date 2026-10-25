"""验证首页导航的相对链接、围栏排除与作者工具导入边界。"""

import importlib.util
from pathlib import Path

import pytest
from check_navigation import (
    course_navigation_problems,
    route_return_problems,
    targets,
    visible_text,
    whole_unit_return_problems,
    whole_unit_route_contexts,
)


def test_relative_wiki_alias_and_markdown_links_resolve(tmp_path):
    home = tmp_path / "home.md"
    target = tmp_path / "next.md"
    target.write_text("# 下一讲\n", encoding="utf-8")
    home.write_text("[[next|下一讲]]\n[正文](./next.md)\n", encoding="utf-8")
    assert targets(home) == {target.resolve()}


def test_code_and_folded_code_do_not_create_navigation(tmp_path):
    home = tmp_path / "home.md"
    hidden = tmp_path / "hidden.md"
    shown = tmp_path / "shown.md"
    hidden.write_text("# 隐藏\n", encoding="utf-8")
    shown.write_text("# 正文\n", encoding="utf-8")
    home.write_text(
        '```python\ntext = "[[hidden]]"\n```\n'
        '> [!example]- 参考答案\n> ```python\n> text = "[[hidden]]"\n> ```\n'
        "> [[shown|答案正文]]\n",
        encoding="utf-8",
    )
    assert "hidden" not in visible_text(home)
    assert targets(home) == {shown.resolve()}


def test_local_heading_is_not_an_extra_document(tmp_path):
    home = tmp_path / "home.md"
    home.write_text("[[#问题|跳到问题]]\n## 问题\n", encoding="utf-8")
    assert targets(home) == set()


def test_inline_link_example_does_not_make_a_document_reachable(tmp_path):
    home = tmp_path / "home.md"
    hidden = tmp_path / "hidden.md"
    hidden.write_text("# 隐藏\n", encoding="utf-8")
    home.write_text(
        "示例：`[[hidden]]` 与 `` `[隐藏](./hidden.md)` ``。\n", encoding="utf-8"
    )
    assert targets(home) == set()


def make_course(tmp_path):
    """构造能打开的两讲课程，供测试错误跳转与缺少返程。"""
    unit_directory = tmp_path / "unit"
    lessons = unit_directory / "逐讲学习"
    lessons.mkdir(parents=True)
    readme = unit_directory / "示例工程" / "README.md"
    readme.parent.mkdir()
    readme.write_text("# 源码\n\n[[unit/map|课表]]\n", encoding="utf-8")
    course_map = unit_directory / "map.md"
    course_map.write_text(
        "# 课表\n\n[[unit/逐讲学习/01 first]]\n"
        "[[unit/逐讲学习/02 second]]\n\n## 完成后继续\n",
        encoding="utf-8",
    )
    checklist = tmp_path / "02_学习记录" / "01 全课程完成清单.md"
    checklist.parent.mkdir()
    checklist.write_text("# 清单\n\n## 单元 01：示例\n", encoding="utf-8")
    resources = (
        "[[unit/示例工程/README|源码]] · "
        "[[02_学习记录/01 全课程完成清单#单元 01：示例|本单元清单]]\n"
    )
    first = lessons / "01 first.md"
    second = lessons / "02 second.md"
    first.write_text(
        "# 第一讲\n\n[[unit/map|地图]] · [[unit/逐讲学习/02 second|下一讲]]\n\n"
        "## 讲解\n\n正文\n\n## 继续学习\n\n"
        "[[unit/逐讲学习/02 second|下一讲]]\n\n" + resources,
        encoding="utf-8",
    )
    second.write_text(
        "# 第二讲\n\n[[unit/map|地图]] · [[unit/逐讲学习/01 first|上一讲]]\n\n"
        "## 讲解\n\n正文\n\n## 继续学习\n\n"
        "[[unit/逐讲学习/01 first|上一讲]] · [[unit/map#完成后继续|后续]]\n\n"
        + resources,
        encoding="utf-8",
    )
    structure = {
        "units": [
            {
                "number": 1,
                "directory": "unit",
                "map": "unit/map.md",
                "lessons": ["unit/逐讲学习/01 first.md", "unit/逐讲学习/02 second.md"],
                "optional": [],
            }
        ]
    }
    return structure, first, second, readme


def test_valid_course_has_no_navigation_problems(tmp_path):
    structure, *_ = make_course(tmp_path)
    assert course_navigation_problems(tmp_path, structure) == []


def test_existing_but_wrong_next_lesson_is_reported(tmp_path):
    structure, first, _, _ = make_course(tmp_path)
    text = first.read_text(encoding="utf-8")
    first.write_text(text.replace("02 second", "01 first"), encoding="utf-8")
    problems = course_navigation_problems(tmp_path, structure)
    assert any("页首缺少" in problem for problem in problems)
    assert any("页末相邻" in problem for problem in problems)


def test_link_in_folded_code_does_not_replace_footer_navigation(tmp_path):
    structure, first, _, _ = make_course(tmp_path)
    text = first.read_text(encoding="utf-8")
    before, footer = text.split("## 继续学习\n", 1)
    first.write_text(
        before + "## 继续学习\n\n> ```text\n> " + footer.strip() + "\n> ```\n",
        encoding="utf-8",
    )
    problems = course_navigation_problems(tmp_path, structure)
    assert any("页末相邻" in problem for problem in problems)


def test_source_readme_needs_return_to_its_own_course_map(tmp_path):
    structure, _, _, readme = make_course(tmp_path)
    readme.write_text("# 源码\n\n[[unit/逐讲学习/01 first|正文]]\n", encoding="utf-8")
    problems = course_navigation_problems(tmp_path, structure)
    assert any("源码导航缺少返回单元地图" in problem for problem in problems)


def test_checklist_link_must_land_in_the_current_unit(tmp_path):
    structure, first, _, _ = make_course(tmp_path)
    text = first.read_text(encoding="utf-8")
    first.write_text(text.replace("#单元 01：示例", "#单元 02：其他"), encoding="utf-8")
    problems = course_navigation_problems(tmp_path, structure)
    assert any("没有定位到本单元" in problem for problem in problems)


def make_first_learning_path(tmp_path, structure, first):
    route = tmp_path / "route.md"
    route.write_text(
        "# 首次主线\n\n[[unit/逐讲学习/01 first|第一个任务]]\n\n## 本轮完成\n",
        encoding="utf-8",
    )
    structure["first_learning_path"] = {
        "route": "route.md",
        "finish_heading": "本轮完成",
        "phases": [{"lessons": ["unit/逐讲学习/01 first.md"]}],
    }
    before, footer = first.read_text(encoding="utf-8").split("## 继续学习\n", 1)
    before = before.replace(
        "[[unit/逐讲学习/02 second|下一讲]]", "[[route#本轮完成|本轮完成]]"
    )
    resources = footer.split("\n\n", 1)[1].strip()
    first.write_text(
        before
        + "## 继续学习\n\n[[route#本轮完成|本轮完成]]\n\n"
        + "> [!info]- 练习与记录\n> "
        + resources
        + "\n",
        encoding="utf-8",
    )


def test_first_path_can_finish_before_the_end_of_a_unit(tmp_path):
    structure, first, _, _ = make_course(tmp_path)
    make_first_learning_path(tmp_path, structure, first)
    assert course_navigation_problems(tmp_path, structure) == []


def test_first_path_does_not_silently_continue_into_extra_unit_lessons(tmp_path):
    structure, first, _, _ = make_course(tmp_path)
    make_first_learning_path(tmp_path, structure, first)
    text = first.read_text(encoding="utf-8")
    first.write_text(
        text.replace(
            "[[route#本轮完成|本轮完成]]", "[[unit/逐讲学习/02 second|下一讲]]"
        ),
        encoding="utf-8",
    )
    problems = course_navigation_problems(tmp_path, structure)
    assert any("本轮末讲没有返回" in problem for problem in problems)


def test_next_step_must_be_visible_outside_folded_supporting_links(tmp_path):
    structure, first, _, _ = make_course(tmp_path)
    before, footer = first.read_text(encoding="utf-8").split("## 继续学习\n", 1)
    first.write_text(
        before + "## 继续学习\n\n> [!info]- 其他入口\n> " + footer.strip() + "\n",
        encoding="utf-8",
    )
    problems = course_navigation_problems(tmp_path, structure)
    assert any("页末相邻" in problem for problem in problems)


def test_visible_next_callout_is_a_valid_primary_navigation(tmp_path):
    structure, first, _, _ = make_course(tmp_path)
    text = first.read_text(encoding="utf-8")
    before, footer = text.split("## 继续学习\n", 1)
    footer = footer.replace(
        "[[unit/逐讲学习/02 second|下一讲]]",
        "> [!next] 下一步\n> [[unit/逐讲学习/02 second|下一讲]]",
        1,
    )
    first.write_text(before + "## 继续学习\n" + footer, encoding="utf-8")
    assert course_navigation_problems(tmp_path, structure) == []


@pytest.mark.parametrize("number", [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38])
def test_importing_author_writer_does_not_write_documents(monkeypatch, number):
    def refuse_write(*args, **kwargs):
        raise AssertionError("导入不应修改教材")

    monkeypatch.setattr(Path, "write_text", refuse_write)
    path = Path(__file__).parent / f"write_unit{number}.py"
    spec = importlib.util.spec_from_file_location(f"author_writer_{number}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def make_route_return(tmp_path):
    lesson = tmp_path / "unit" / "01 lesson.md"
    lesson.parent.mkdir()
    lesson.write_text(
        "# 课程\n\n> [!nav] 路线续读\n> [[route#阶段 5：整合|回原阶段]]\n",
        encoding="utf-8",
    )
    route = tmp_path / "route.md"
    route.write_text(
        "# 方向\n\n### 阶段 5：整合\n\n[[unit/01 lesson|第 1 讲]]\n"
        "\n### 阶段 6：扩展\n\n其他内容\n",
        encoding="utf-8",
    )
    structure = {
        "units": [{"directory": "unit", "lessons": ["unit/01 lesson.md"]}],
        "direction_route_returns": [
            {
                "lesson": "unit/01 lesson.md",
                "destinations": [{"route": "route.md", "heading": "阶段 5：整合"}],
            }
        ],
    }
    return structure, lesson, route


def test_route_return_reaches_visible_stage_with_matching_scope(tmp_path):
    structure, _, _ = make_route_return(tmp_path)
    assert route_return_problems(tmp_path, structure) == []


def test_route_return_rejects_an_existing_but_wrong_stage(tmp_path):
    structure, lesson, _ = make_route_return(tmp_path)
    lesson.write_text(
        lesson.read_text(encoding="utf-8").replace("route#阶段 5", "route#阶段 6"),
        encoding="utf-8",
    )
    assert any(
        "未定位到规定阶段" in item
        for item in route_return_problems(tmp_path, structure)
    )


def test_route_return_cannot_be_hidden_in_a_folded_callout(tmp_path):
    structure, lesson, _ = make_route_return(tmp_path)
    lesson.write_text(
        lesson.read_text(encoding="utf-8").replace("[!nav]", "[!nav]-"),
        encoding="utf-8",
    )
    assert any(
        "缺少展开" in item for item in route_return_problems(tmp_path, structure)
    )


def test_route_return_requires_the_lesson_to_remain_a_scope_endpoint(tmp_path):
    structure, _, route = make_route_return(tmp_path)
    route.write_text(
        route.read_text(encoding="utf-8").replace(
            "[[unit/01 lesson|第 1 讲]]", "暂无课次"
        ),
        encoding="utf-8",
    )
    assert any(
        "不是该阶段" in item for item in route_return_problems(tmp_path, structure)
    )


def make_whole_unit_return(tmp_path):
    unit_directory = tmp_path / "unit"
    unit_directory.mkdir()
    course_map = unit_directory / "map.md"
    course_map.write_text(
        "# 地图\n\n## 完成后继续\n\n> [!next] 回原路线\n"
        "> [[00_学习路线/05 route#完整单元与工程扩展|回完整实验]]\n",
        encoding="utf-8",
    )
    routes = tmp_path / "00_学习路线"
    routes.mkdir()
    route = routes / "05 route.md"
    route.write_text(
        "# GPU 方向\n\n### 阶段 2：理解服务与测量\n\n"
        "#### 机制入门\n\n[[unit/01 first|单元 10 第 1 讲]]\n\n"
        "#### 完整单元与工程扩展\n\n"
        "[[unit/01 first|单元 10 第 1～2 讲]]\n",
        encoding="utf-8",
    )
    structure = {
        "units": [
            {
                "directory": "unit",
                "map": "unit/map.md",
                "lessons": ["unit/01 first.md", "unit/02 second.md"],
            }
        ]
    }
    return structure, course_map, route


@pytest.mark.parametrize("heading", ["阶段 2：理解服务与测量", "完整单元与工程扩展"])
def test_whole_unit_return_accepts_original_stage_or_matching_branch(tmp_path, heading):
    structure, course_map, _ = make_whole_unit_return(tmp_path)
    course_map.write_text(
        course_map.read_text(encoding="utf-8").replace(
            "#完整单元与工程扩展", "#" + heading
        ),
        encoding="utf-8",
    )
    contexts = whole_unit_route_contexts(tmp_path, structure)
    assert len(contexts) == 1
    assert whole_unit_return_problems(tmp_path, contexts) == []


def test_whole_unit_return_finds_omission_without_manual_registration(tmp_path):
    structure, course_map, _ = make_whole_unit_return(tmp_path)
    course_map.write_text("# 地图\n\n## 完成后继续\n\n暂无路线\n", encoding="utf-8")
    contexts = whole_unit_route_contexts(tmp_path, structure)
    assert any(
        "缺少原路线" in item for item in whole_unit_return_problems(tmp_path, contexts)
    )


def test_whole_unit_return_rejects_existing_but_unrelated_subsection(tmp_path):
    structure, course_map, _ = make_whole_unit_return(tmp_path)
    course_map.write_text(
        course_map.read_text(encoding="utf-8").replace(
            "#完整单元与工程扩展", "#机制入门"
        ),
        encoding="utf-8",
    )
    contexts = whole_unit_route_contexts(tmp_path, structure)
    assert whole_unit_return_problems(tmp_path, contexts)


@pytest.mark.parametrize("placement", ["reference", "folded"])
def test_whole_unit_return_must_be_in_visible_continuation_area(tmp_path, placement):
    structure, course_map, _ = make_whole_unit_return(tmp_path)
    target = "[[00_学习路线/05 route#完整单元与工程扩展|回完整实验]]"
    text = "# 地图\n\n## 完成后继续\n\n> [!info]- 记录\n> " + target + "\n"
    if placement == "reference":
        text = "# 地图\n\n## 参考\n\n" + target + "\n\n## 完成后继续\n\n暂无路线\n"
    course_map.write_text(text, encoding="utf-8")
    contexts = whole_unit_route_contexts(tmp_path, structure)
    assert whole_unit_return_problems(tmp_path, contexts)


def test_partial_unit_scope_does_not_require_whole_unit_map_return(tmp_path):
    structure, _, route = make_whole_unit_return(tmp_path)
    route.write_text(
        route.read_text(encoding="utf-8").replace("第 1～2 讲", "第 1～1 讲"),
        encoding="utf-8",
    )
    assert whole_unit_route_contexts(tmp_path, structure) == []


def test_whole_unit_scope_ignores_code_examples(tmp_path):
    structure, _, route = make_whole_unit_return(tmp_path)
    route.write_text(
        "# 路线\n\n### 阶段 2：理解服务与测量\n\n"
        "示例：`[[unit/01 first|单元 10 第 1～2 讲]]`\n\n"
        "```text\n[[unit/01 first|单元 10 第 1～2 讲]]\n```\n",
        encoding="utf-8",
    )
    assert whole_unit_route_contexts(tmp_path, structure) == []
