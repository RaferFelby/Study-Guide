"""只读扫描正式教材的高风险措辞；结果是复核候选，不是事实判定。"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "certainty": r"一定|保证|完全一致|精确恢复|等价恢复|无损|永远|只要.*就",
    "evaluation": r"AP|PR-AUC|ROC-AUC|测试集|开发集|验证集|置信|pass@|正确率",
    "environment": r"CUDA|FlashAttention|FSDP|ZeRO|未安装|尚待.*验证|pip install",
    "numerical": r"softmax|交叉熵|log2|KL|RoPE|O\(|GiB|FP16|BF16",
}


def scan():
    paths = [ROOT / "00 从这里开始.md", ROOT / "README.md"]
    for directory in ("00_学习路线", "01_学习指南"):
        paths.extend((ROOT / directory).rglob("*.md"))
    formal = [
        path for path in paths if path.read_text(encoding="utf-8").startswith("---\n")
    ]
    counts = {name: 0 for name in PATTERNS}
    candidates = []
    for path in sorted(formal):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            kinds = [
                name for name, pattern in PATTERNS.items() if re.search(pattern, line)
            ]
            for kind in kinds:
                counts[kind] += 1
            if kinds:
                candidates.append(
                    {
                        "file": path.relative_to(ROOT).as_posix(),
                        "line": number,
                        "kinds": kinds,
                        "text": line,
                    }
                )
    return {
        "formal_documents_scanned": len(formal),
        "pattern_counts": counts,
        "scope": "全库文本候选扫描，不等于逐句事实验证或全工程执行",
        "candidates": candidates,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    report = scan()
    options.output.parent.mkdir(parents=True, exist_ok=True)
    with options.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "candidates"},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
