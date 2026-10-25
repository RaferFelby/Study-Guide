"""只读检查正式教材是否能从学习首页沿本地链接到达。"""

import json
import re
from collections import deque
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def without_inline_code(text):
    """反引号里的链接写法只是代码示例，不参与跳转。"""
    return re.sub(r"(?<!`)(`+)(?!`)[^\n]*?(?<!`)\1(?!`)", "", text)


def visible_text(path):
    lines = []
    fence = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = re.sub(r"^\s*(?:>\s*)+", "", line)
        marker = re.match(r"^\s*(`{3,}|~{3,})", stripped)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        elif fence is None:
            lines.append(line)
    return "\n".join(lines)


def targets_in_text(path, text, root=ROOT):
    text = without_inline_code(text)
    found = set()
    for value in re.findall(r"\[\[([^\]]+)\]\]", text):
        target = value.replace("\\|", "|").split("|", 1)[0].split("#", 1)[0]
        if not target:
            continue
        relative = Path(target + ("" if target.endswith(".md") else ".md"))
        for candidate in (path.parent / relative, root / relative):
            if candidate.is_file():
                found.add(candidate.resolve())
                break
    for value in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", text):
        target = unquote(value.strip("<>").split("#", 1)[0])
        if target and not re.match(r"^[a-z]+:", target, re.IGNORECASE):
            candidate = (path.parent / target).resolve()
            if candidate.is_file() and candidate.suffix == ".md":
                found.add(candidate)
    return found


def targets(path, root=ROOT):
    return targets_in_text(path, visible_text(path), root)


def course_navigation_problems(root, structure):
    """核对实际学习路径，发现能打开但跳错课的链接。"""
    problems = []
    first_path = structure.get("first_learning_path")
    first_steps = []
    if first_path:
        for phase in first_path["phases"]:
            first_steps.extend(phase["lessons"])
        if len(first_steps) != len(set(first_steps)):
            problems.append("首次主线重复列出同一课程")
        known_lessons = {
            name
            for unit in structure["units"]
            for name in unit["lessons"] + unit["optional"]
        }
        for name in first_steps:
            if name not in known_lessons:
                problems.append(f"首次主线课程不在课程清单中：{name}")
        route_path = root / first_path["route"]
        if not route_path.is_file():
            problems.append(f"首次主线入口不存在：{route_path}")
        else:
            route_targets = targets(route_path, root)
            for name in first_steps:
                if (root / name).resolve() not in route_targets:
                    problems.append(f"首次主线入口没有列出课程：{name}")
    for unit in structure["units"]:
        map_path = root / unit["map"]
        readme_path = root / unit["directory"] / "示例工程" / "README.md"
        listed = unit["lessons"] + unit["optional"]
        required_paths = [map_path, readme_path] + [root / name for name in listed]
        missing = [path for path in required_paths if not path.is_file()]
        if missing:
            problems.extend(f"学习路径文件缺失：{path}" for path in missing)
            continue

        actual = set()
        for directory in ("逐讲学习", "选修专题"):
            actual.update(
                path.relative_to(root).as_posix()
                for path in (root / unit["directory"] / directory).glob("*.md")
            )
        if actual != set(listed):
            problems.append(f"课次清单与正文目录不一致：{unit['directory']}")

        map_targets = targets(map_path, root)
        for name in listed:
            if (root / name).resolve() not in map_targets:
                problems.append(f"单元地图未列出课程：{name}")

        readme_header = visible_text(readme_path).split("\n## ", 1)[0]
        if map_path.resolve() not in targets_in_text(readme_path, readme_header, root):
            problems.append(f"源码导航缺少返回单元地图的入口：{readme_path}")

        for kind in ("lessons", "optional"):
            names = unit[kind]
            for index, name in enumerate(names):
                path = root / name
                text = visible_text(path)
                header = text.split("\n## ", 1)[0]
                required = {map_path.resolve()}
                previous = None
                following = None
                finish_name = unit["map"]
                finish_heading = "完成后继续"
                if name in first_steps:
                    position = first_steps.index(name)
                    if position:
                        previous = first_steps[position - 1]
                    if position + 1 < len(first_steps):
                        following = first_steps[position + 1]
                    finish_name = first_path["route"]
                    finish_heading = first_path["finish_heading"]
                else:
                    if index:
                        previous = names[index - 1]
                    elif kind == "optional":
                        previous = unit["lessons"][-1]
                    if index + 1 < len(names):
                        following = names[index + 1]
                if previous:
                    required.add((root / previous).resolve())
                if following:
                    required.add((root / following).resolve())
                else:
                    required.add((root / finish_name).resolve())
                if not required <= targets_in_text(path, header, root):
                    problems.append(f"页首缺少本单元或相邻课次链接：{name}")

                if "\n## 继续学习\n" not in text:
                    problems.append(f"缺少页末续读导航：{name}")
                    continue
                footer = text.rsplit("\n## 继续学习\n", 1)[1]
                footer_targets = targets_in_text(path, footer, root)
                # 展开的下一步提示仍是主要导航；只排除默认折叠的辅助入口。
                primary_footer = re.split(
                    r"^> \[![^\]]+\]-", footer, maxsplit=1, flags=re.MULTILINE
                )[0]
                primary_targets = targets_in_text(path, primary_footer, root)
                if following and (root / following).resolve() not in primary_targets:
                    problems.append(f"页末相邻课次链接不完整：{name}")
                if readme_path.resolve() not in footer_targets:
                    problems.append(f"页末缺少本单元源码入口：{name}")
                checklist = root / "02_学习记录" / "01 全课程完成清单.md"
                if checklist.resolve() not in footer_targets:
                    problems.append(f"页末缺少本单元完成清单：{name}")
                else:
                    checklist_prefix = "02_学习记录/01 全课程完成清单#"
                    matching_unit = re.compile(
                        r"(?:扩展)?单元 " + f"{unit['number']:02d}" + "："
                    )
                    checklist_links = re.findall(r"\[\[([^\]]+)\]\]", footer)
                    if not any(
                        link.startswith(checklist_prefix)
                        and matching_unit.match(link[len(checklist_prefix) :])
                        for link in checklist_links
                    ):
                        problems.append(f"页末完成清单没有定位到本单元：{name}")
                if following is None:
                    links = re.findall(r"\[\[([^\]]+)\]\]", primary_footer)
                    expected = finish_name.removesuffix(".md") + "#" + finish_heading
                    if not any(
                        link.replace("\\|", "|").split("|", 1)[0] == expected
                        for link in links
                    ):
                        problems.append(f"本轮末讲没有返回后续选择：{name}")
    return problems


def route_return_problems(root, structure):
    """核对分段学习的返程入口、实际阶段与课次范围。"""
    problems = []
    positions = {
        name.removesuffix(".md"): (unit["directory"], index)
        for unit in structure["units"]
        for index, name in enumerate(unit["lessons"], 1)
    }
    for record in structure.get("direction_route_returns", []):
        name = record["lesson"]
        lesson_path = root / name
        position = positions.get(name.removesuffix(".md"))
        if not lesson_path.is_file() or position is None:
            problems.append(f"路线返程课次不存在或不在清单中：{name}")
            continue
        text = visible_text(lesson_path)
        callout = re.search(
            r"^> \[!nav\] 路线续读\n(?:>[^\n]*(?:\n|$))+",
            text,
            flags=re.MULTILINE,
        )
        if callout is None:
            problems.append(f"缺少展开的路线返程入口：{name}")
            continue
        actual_links = {
            value.replace("\\|", "|").split("|", 1)[0]
            for value in re.findall(r"\[\[([^\]]+)\]\]", callout[0])
        }
        for destination in record["destinations"]:
            route_name = destination["route"]
            heading = destination["heading"]
            expected = route_name.removesuffix(".md") + "#" + heading
            if expected not in actual_links:
                problems.append(f"路线返程未定位到规定阶段：{name} → {expected}")
            route_path = root / route_name
            if not route_path.is_file():
                problems.append(f"返程路线不存在：{route_name}")
                continue
            route_text = visible_text(route_path)
            header = re.search(
                r"^(#{2,4}) " + re.escape(heading) + r"\s*$",
                route_text,
                flags=re.MULTILINE,
            )
            if header is None:
                problems.append(f"返程阶段标题不存在：{expected}")
                continue
            section = re.split(
                r"\n#{1," + str(len(header[1])) + r"} ",
                route_text[header.end() :],
                maxsplit=1,
            )[0]
            is_stop = False
            for target, alias in re.findall(r"\[\[([^|\]]+)\|([^\]]+)\]\]", section):
                start = positions.get(target)
                if start is None or start[0] != position[0]:
                    continue
                scope = re.search(r"第 (\d+)～(\d+) 讲", alias)
                end = int(scope[2]) if scope else start[1]
                if end == position[1]:
                    is_stop = True
                    break
            if not is_stop:
                problems.append(
                    f"返程课次不是该阶段列出的范围终点：{name} → {expected}"
                )
    return problems


def whole_unit_route_contexts(root, structure):
    """从方向正文发现整单元范围，不依赖人工登记返程清单。"""
    positions = {
        name.removesuffix(".md"): (unit, index)
        for unit in structure["units"]
        for index, name in enumerate(unit["lessons"], 1)
    }
    contexts = []
    for route_path in sorted((root / "00_学习路线").glob("*.md")):
        text = without_inline_code(visible_text(route_path))
        headers = list(re.finditer(r"^(#{3,4}) (.+)$", text, flags=re.MULTILINE))
        for match in re.finditer(r"\[\[([^|\]]+)\|([^\]]+)\]\]", text):
            target, alias = match.groups()
            position = positions.get(target)
            if position is None:
                continue
            unit, start = position
            scope = re.search(r"第 (\d+)～(\d+) 讲", alias)
            if scope is None or start != 1 or int(scope[1]) != 1:
                continue
            if int(scope[2]) != len(unit["lessons"]):
                continue
            stage = next(
                (
                    header
                    for header in reversed(headers)
                    if header.start() < match.start()
                    and header[1] == "###"
                    and header[2].startswith("阶段 ")
                ),
                None,
            )
            if stage is None:
                continue
            subsection = next(
                (
                    header[2]
                    for header in reversed(headers)
                    if stage.start() < header.start() < match.start()
                    and header[1] == "####"
                ),
                None,
            )
            contexts.append(
                {
                    "map": unit["map"],
                    "route": route_path.relative_to(root).as_posix(),
                    "headings": [stage[2]] + ([subsection] if subsection else []),
                }
            )
    return contexts


def whole_unit_return_problems(root, contexts):
    """整单元学完后，地图须能返回原阶段或该范围所在的分支。"""
    problems = []
    for context in contexts:
        map_path = root / context["map"]
        if not map_path.is_file():
            problems.append(f"整单元返程地图不存在：{context['map']}")
            continue
        footer = visible_text(map_path).partition("\n## 完成后继续\n")[2]
        # 参考区或折叠记录里的链接不能冒充主要返程入口。
        primary_footer = re.split(
            r"^> \[![^\]]+\]-", footer, maxsplit=1, flags=re.MULTILINE
        )[0]
        actual_links = {
            value.replace("\\|", "|").split("|", 1)[0]
            for value in re.findall(r"\[\[([^\]]+)\]\]", primary_footer)
        }
        route = context["route"].removesuffix(".md")
        expected = {route + "#" + heading for heading in context["headings"]}
        if not actual_links & expected:
            problems.append(
                f"整单元地图缺少原路线返程：{context['map']} → "
                f"{route}#{context['headings'][-1]}"
            )
    return problems


def main():
    documents = {ROOT / "00 从这里开始.md", ROOT / "README.md"}
    for directory in ("00_学习路线", "01_学习指南", "02_学习记录", "90_参考与维护"):
        documents.update(
            path.resolve()
            for path in (ROOT / directory).rglob("*.md")
            if not set(path.parts) & {"fixtures", ".pytest_cache", ".venv"}
        )
    visited = set()
    pending = deque([ROOT / "00 从这里开始.md"])
    while pending:
        path = pending.popleft().resolve()
        if path in visited:
            continue
        visited.add(path)
        pending.extend(targets(path) - visited)
    missing = documents - visited
    for path in sorted(missing):
        print(f"首页不可达：{path.relative_to(ROOT)}")
    print(f"正式文档 {len(documents)} 份，首页可达 {len(documents & visited)} 份")
    structure_path = ROOT / "scripts" / "guide_structure.json"
    course_problems = []
    if structure_path.is_file():
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
        course_problems = course_navigation_problems(ROOT, structure)
        course_problems.extend(route_return_problems(ROOT, structure))
        whole_unit_contexts = whole_unit_route_contexts(ROOT, structure)
        course_problems.extend(whole_unit_return_problems(ROOT, whole_unit_contexts))
        for problem in course_problems:
            print(problem)
        lesson_count = sum(
            len(unit["lessons"]) + len(unit["optional"]) for unit in structure["units"]
        )
        print(f"学习路径 {lesson_count} 篇，发现 {len(course_problems)} 个问题")
        return_count = len(structure.get("direction_route_returns", []))
        print(f"分段学习返程 {return_count} 篇")
        print(f"整单元返程 {len(whole_unit_contexts)} 处")
        first_path = structure.get("first_learning_path")
        if first_path:
            first_count = sum(len(phase["lessons"]) for phase in first_path["phases"])
            print(f"首次学习主线 {first_count} 讲")
    raise SystemExit(1 if missing or course_problems else 0)


if __name__ == "__main__":
    main()
