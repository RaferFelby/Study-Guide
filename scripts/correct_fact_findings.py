"""同步2026-10-14已核实的指标勘误与日期；不改历史实验结果。"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def update(path, text):
    text = re.sub(
        r"^updated: .*", "updated: 2026-10-14", text, count=1, flags=re.MULTILINE
    )
    path.write_text(text, encoding="utf-8")


def main():
    unit = ROOT / "01_学习指南/07_传统机器学习与数据分析"
    for path in unit.rglob("*.md"):
        if path.name == "参考工程验证记录.md":
            continue
        text = path.read_text(encoding="utf-8")
        if path.name.startswith("03 比较线性"):
            text = text.replace("的 PR-AUC、ROC-AUC", "的 AP、ROC-AUC")
            text = text.replace("dev PR-AUC", "dev AP")
            text = text.replace("## PR-AUC 与 ROC-AUC", "## AP、PR-AUC 与 ROC-AUC")
            text = text.replace("观察 PR 曲线和 PR-AUC", "观察 PR 曲线和 AP")
            text = text.replace(
                "Precision、Recall、PR-AUC、ROC-AUC", "Precision、Recall、AP、ROC-AUC"
            )
        else:
            text = text.replace("PR-AUC", "AP")
        update(path, text)
    for relative in (
        "01_学习指南/01_Python工程化/逐讲学习/03 看懂报错并安全管理资源.md",
        "01_学习指南/04_数据结构与算法/逐讲学习/01 从复杂度到数组与哈希表.md",
        "01_学习指南/05_数学概率与优化/逐讲学习/03 熵交叉熵与KL散度.md",
        "01_学习指南/05_数学概率与优化/示例工程/README.md",
        "01_学习指南/06_PyTorch训练闭环/逐讲学习/05 检查点续训与EarlyStopping.md",
        "01_学习指南/08_Transformer从零实现/逐讲学习/06 训练小模型并理解 FlashAttention.md",
        "01_学习指南/09_主流大模型架构与参数估算/逐讲学习/05 区分 Prefill Decode 与采样参数.md",
    ):
        path = ROOT / relative
        update(path, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
