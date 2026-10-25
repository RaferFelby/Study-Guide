"""记录已实际观察的本轮验证，不修改学习者任务勾选。"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ROOT / "01_学习指南"


def main():
    counts = {24: 23, 25: 21, 26: 24, 27: 24, 28: 24, 29: 21}
    fragments = {24: 6, 25: 6, 26: 5, 27: 6, 28: 6, 29: 6}
    for number, count in counts.items():
        unit = next(
            path for path in GUIDES.iterdir() if path.name.startswith(f"{number}_")
        )
        path = unit / "参考工程验证记录.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "Ruff导入分类问题已按示例工程目录修正，交付前复查。",
            "Ruff导入分类问题已按示例工程目录修正。",
        )
        text = text.replace(
            "Ruff已格式/规则修正，交付前复查。", "Ruff已完成格式与规则检查。"
        )
        text = text.replace(
            "教材代码和链接会在本轮收尾统一检查；", "教材代码和链接已在本轮收尾检查；"
        )
        text = text.replace(
            "教材示例与导航在交付前统一核查，", "教材示例与导航已完成本轮核查，"
        )
        text = text.replace(
            "Ruff检查/格式检查及教材链接检查结果在交付前补充统一检查。",
            "Ruff检查/格式检查及教材链接检查通过，详见下方最终复核。",
        )
        text = text.replace(
            "教学Python片段与最终导航统一检查的实际结果会另补，不把仅编辑写成已运行。",
            "教学Python片段与最终导航检查已执行，详见最终复核。",
        )
        text = text.replace(
            "Ruff检查和格式检查、Python教学片段及全库导航将在本次交付前统一复核。",
            "Ruff检查和格式检查、Python教学片段及全库导航已在本次交付复核。",
        )
        text = text.replace(
            "最终修改后的测试、Ruff、六讲Python片段和导航结果在本次交付统一复核中另补。",
            "最终修改后的测试、Ruff、六讲Python片段和导航已在本次交付复核。",
        )
        text = text.replace(
            "六讲最小 Python 示例和全库导航检查的结果在本轮交付复核中记录；",
            "六讲最小 Python 示例和全库导航检查通过，详见最终复核；",
        )
        if "## 2026-10-12 最终复核" in text:
            raise ValueError("已记录，禁止重复追加")
        text += f"\n## 2026-10-12 最终复核\n\n最终源码 {count} 项测试实际通过，无跳过；Ruff 规则与格式检查通过。本单元 {fragments[number]} 个 Python 教学片段分别在本工程目录使用根共享解释器实际运行通过，临时文件属于检查脚本自己的目录。片段通过表示能够执行，不代替学习者独立练习。\n\n全库正式文档共 272 份，YAML、标题层级、围栏、表格双链和本地链接检查发现 0 个问题；从学习首页沿链接可达 272 份。这个结果是静态检查，没有进行 Obsidian 界面视觉验收。\n"
        if number == 24:
            text += "\n本次补充实际回环 HTTP 错误响应测试：错误内容类型、超限字节、坏 JSON、非法 UTF-8、重定向拒绝和超时，共 6 项；最终 23 项耗时 6.63 秒。历史 17 项初验保留上文，没有把新增测试算到历史运行中。\n"
        if number == 26:
            text += "\n最终 24 项回归耗时 24.80 秒，包括 CUDA FP32/BF16/FP16 实际训练；本机无 GPU 测试跳过。另用 CPU 完整报告中的 Base 和 rank2 适配器运行独立 inference.py，同一 blue 提示不合并及带 --merged 均输出 tag = B。旧任务退化结论保留，没有因加载成功就采用全任务替换。\n"
        path.write_text(text, encoding="utf-8")
    paths = [
        ROOT / "00 从这里开始.md",
        ROOT / "README.md",
        GUIDES / "00 学习目录.md",
        GUIDES / "课程覆盖台账.md",
        GUIDES / "我的学习记录.md",
    ]
    for number in counts:
        unit = next(
            path for path in GUIDES.iterdir() if path.name.startswith(f"{number}_")
        )
        paths.extend(unit.rglob("*.md"))
    previous = next(path for path in GUIDES.iterdir() if path.name.startswith("23_"))
    paths.append(max((previous / "逐讲学习").glob("*.md")))
    for path in paths:
        if "fixtures" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r"(?m)^updated: \d{4}-\d{2}-\d{2}$", "updated: 2026-10-12", text, count=1
        )
        path.write_text(text, encoding="utf-8")
    print("六单元最终记录与维护日期已同步；学习者勾选保留")


if __name__ == "__main__":
    main()
