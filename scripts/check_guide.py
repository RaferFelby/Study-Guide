"""检查指定教材的结构、YAML 和本地链接；不改写任何教材。"""

import argparse
import re
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]


def check_document(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    problems = []
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if match is None:
        problems.append("缺少 YAML properties")
        body = text
    else:
        try:
            properties = yaml.safe_load(match.group(1))
            if not isinstance(properties, dict):
                problems.append("properties 不是映射")
            else:
                for key in ["title", "tags", "updated"]:
                    if key not in properties:
                        problems.append(f"缺少 property: {key}")
                if not re.fullmatch(
                    r"\d{4}-\d{2}-\d{2}", str(properties.get("updated", ""))
                ):
                    problems.append("updated 日期格式错误")
        except yaml.YAMLError as error:
            problems.append(f"YAML 无法解析：{error}")
        body = text[match.end() :]
    fence = None
    visible_lines = []
    for line in body.splitlines():
        stripped = re.sub(r"^\s*(?:>\s*)+", "", line)
        if fence is None and re.match(r"^\s*(?:\\`){3,}", stripped):
            problems.append("代码围栏被转义，会显示成普通正文")
        fence_match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", stripped)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
                if not fence_match.group(2).strip():
                    problems.append("代码块开头没有语言标识")
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            visible_lines.append(line)
    if fence is not None:
        problems.append("代码围栏未闭合")
    visible = "\n".join(visible_lines)
    headings = re.findall(r"^(#{1,6})\s+(.+)$", visible, re.MULTILINE)
    if sum(len(level) == 1 for level, _ in headings) != 1:
        problems.append("一级标题数量必须为1")
    previous_level = 1
    for level, title in headings:
        if len(level) > previous_level + 1:
            problems.append(f"标题跳级：{title}")
        previous_level = len(level)
    # 行内代码中的双链或 Markdown 写法不是可点击的导航。
    link_text = re.sub(r"(?<!`)(`+)(?!`)[^\n]*?(?<!`)\1(?!`)", "", visible)
    for target in re.findall(r"\[\[([^\]]+)\]\]", link_text):
        target = target.replace("\\|", "|").split("|", 1)[0]
        file_target, _, anchor = target.partition("#")
        if not file_target:
            if anchor and anchor not in {title for _, title in headings}:
                problems.append(f"同页标题不存在：{anchor}")
            continue
        candidates = [path.parent / file_target, ROOT / file_target]
        resolved = []
        for candidate in candidates:
            if not candidate.suffix:
                candidate = Path(f"{candidate}.md")
            if candidate.exists():
                resolved.append(candidate)
        if not resolved:
            problems.append(f"双链目标不存在：{file_target}")
        elif anchor:
            target_text = resolved[0].read_text(encoding="utf-8-sig")
            target_headings = re.findall(r"^#{1,6}\s+(.+)$", target_text, re.MULTILINE)
            if anchor not in target_headings:
                problems.append(f"目标标题不存在：{file_target}#{anchor}")
    for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", link_text):
        target = target.strip("<>").split("#", 1)[0]
        if not target or re.match(r"^[a-z]+:", target, re.IGNORECASE):
            continue
        if not (path.parent / unquote(target)).exists():
            problems.append(f"本地 Markdown 链接不存在：{target}")
    for line in visible_lines:
        if line.lstrip().startswith("|"):
            for target in re.findall(r"\[\[([^\]]+)\]\]", line):
                if "|" in target.replace("\\|", ""):
                    problems.append("表格双链别名分隔符没有转义")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    files = []
    for path in args.paths:
        if path.is_dir():
            files.extend(
                item
                for item in path.rglob("*.md")
                if not any(
                    part in {"fixtures", ".pytest_cache", ".venv"}
                    for part in item.parts
                )
            )
        else:
            files.append(path)
    issue_count = 0
    for path in sorted(set(files)):
        problems = check_document(path)
        for problem in problems:
            print(f"{path}: {problem}")
        issue_count += len(problems)
    print(f"检查 {len(set(files))} 份文档，发现 {issue_count} 个问题")
    raise SystemExit(1 if issue_count else 0)


if __name__ == "__main__":
    main()
