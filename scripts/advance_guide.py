"""连接一个已写完的顺序单元；保留学习者勾选和原始模块清单。"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_latest(text, previous_folder, previous_map, folder, map_name):
    return text.replace(previous_folder, folder).replace(previous_map, map_name)


def advance(spec):
    number = spec["number"]
    folder, map_name, topic = spec["folder"], spec["map"], spec["topic"]
    unit_path = ROOT / "01_学习指南" / folder
    lessons = sorted((unit_path / "逐讲学习").glob("*.md"))
    if len(lessons) != 6 or not (unit_path / f"{map_name}.md").is_file():
        raise ValueError("完整六讲和学习地图必须先存在")
    previous = next(
        path
        for path in unit_path.parent.iterdir()
        if path.name.startswith(f"{number - 1:02d}_")
    )
    previous_map = next(previous.glob("00 *学习地图.md")).stem
    previous_first = min((previous / "逐讲学习").glob("*.md")).stem
    first = lessons[0].stem
    for filename in ("00 从这里开始.md", "README.md", "01_学习指南/我的学习记录.md"):
        path = ROOT / filename
        text = path.read_text(encoding="utf-8")
        position = text.index("\n## ")
        header, tail = text[:position], text[position:]
        header = replace_latest(header, previous.name, previous_map, folder, map_name)
        header = header.replace(previous_first, first)
        header = header.replace(
            f"已经学完单元 {number - 2}", f"已经学完单元 {number - 1}"
        )
        header = header.replace(
            f"单元 {number - 1} 学习地图", f"单元 {number} 学习地图"
        )
        header = header.replace(
            f"最新教材为单元 {number - 1}", f"最新教材为单元 {number}"
        )
        header = re.sub(r"最新教材：[^\]]+", f"最新教材：{topic}", header)
        header = re.sub(r"第 1 讲：[^\]]+", f"第 1 讲：{first[3:]}", header)
        text = header + tail
        if filename == "00 从这里开始.md":
            # 首页正文中的“最新源码/作者验证”也是动态导航。
            text = replace_latest(text, previous.name, previous_map, folder, map_name)
        if filename.endswith("我的学习记录.md"):
            if f"## 单元 {number:02d}：" in text:
                raise ValueError("学习记录已含本单元；不要重复追加")
            section = f"\n## 单元 {number:02d}：{topic}\n\n"
            for lesson in lessons:
                section += f"- [ ] [[{folder}/逐讲学习/{lesson.stem}|{lesson.stem}]]\n"
            section += (
                "\n请记录亲自操作、解释与独立练习结果，作者验证不代替学习进度。\n"
            )
            text = text.replace(
                "\n## 每次学习怎么记录", section + "\n## 每次学习怎么记录"
            )
        path.write_text(text, encoding="utf-8")
    index = ROOT / "01_学习指南/00 学习目录.md"
    text = index.read_text(encoding="utf-8")
    position = text.index("\n## 当前内容")
    header = replace_latest(
        text[:position], previous.name, previous_map, folder, map_name
    )
    header = header.replace(f"单元 {number - 1}", f"单元 {number}").replace(
        f"完成单元 {number - 2}", f"完成单元 {number - 1}"
    )
    header = re.sub(
        r"(单元 " + str(number) + r"：)[^\]]+", lambda match: match[1] + topic, header
    )
    text = header + text[position:]
    text = re.sub(
        r"当前已编写 \d+/38 个单元，其余 \d+ 个",
        f"当前已编写 {number}/38 个单元，其余 {38 - number} 个",
        text,
    )
    text = re.sub(r"下一单元为“[^”]+”", f"下一单元为“{spec['next_topic']}”", text)
    entries = f"- [[{folder}/{map_name}|单元 {number:02d}：{topic}]]：{spec['summary']}\n- [[{folder}/示例工程/README|单元 {number:02d} 代码导航]] · [[{folder}/参考工程验证记录|作者验证]]。\n"
    text = text.replace(
        "- [[我的学习记录|我的学习记录]]：",
        entries + "- [[我的学习记录|我的学习记录]]：",
        1,
    )
    pattern = rf"^\| {number:02d} \| {spec['module']:02d} \| [^\n]+$"
    replacement = f"| {number:02d} | {spec['module']:02d} | [[{folder}/{map_name}\\|{topic}]] | 六讲与教学工程已编写并验证；实际范围见作者记录 |"
    text, count = re.subn(pattern, lambda _: replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("课程表必须恰有一行对应教材/模块编号")
    index.write_text(text, encoding="utf-8")
    ledger = ROOT / "01_学习指南/课程覆盖台账.md"
    text = ledger.read_text(encoding="utf-8")
    start = text.index(f"## 模块 {spec['module']:02d}：")
    end = text.find("\n## 模块 ", start + 1)
    if end == -1:
        end = len(text)
    block = text[start:end]
    block = block.replace(
        "教材状态：待编写；本节为清单要求，尚不是详细教材。",
        f"教材状态：已编写单元 {number:02d}；详见 [[{folder}/{map_name}|学习地图]]。作者机制验证与学习者验收分开，未测/简化范围见验证记录。",
    )
    for code, lesson in spec["mapping"].items():
        pattern = rf"(^[^\n]*\*\*{code}\*\*[^\n]*)"
        block = re.sub(
            pattern,
            lambda match, lesson=lesson: (
                match[0] + f" 见 [[{folder}/逐讲学习/{lesson}|详细教程]]。"
            ),
            block,
            flags=re.MULTILINE,
        )
    ledger.write_text(text[:start] + block + text[end:], encoding="utf-8")
    previous_last = max((previous / "逐讲学习").glob("*.md"))
    for path, prefix in (
        (previous / f"{previous_map}.md", "../"),
        (previous_last, "../../"),
    ):
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r"下一单元[^\n]*",
            f"下一单元：[[{prefix}{folder}/{map_name}|{topic}]]。",
            text,
        )
        if path == previous_last:
            old_return = re.escape(f"[[../{previous_map}|")
            text = re.sub(
                old_return + r"返回(?:单元)?地图\]\]",
                f"[[../../{folder}/逐讲学习/{first}|下一讲]]",
                text,
                count=1,
            )
        path.write_text(text, encoding="utf-8")
    print(f"单元 {number:02d} 导航同步；学习者勾选未改变")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    options = parser.parse_args()
    advance(json.loads(options.spec.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
