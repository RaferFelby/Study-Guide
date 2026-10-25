import argparse
import json
import random
from pathlib import Path
from typing import Any


def run(seed: int, data_version: str, rounds: int = 10) -> dict[str, Any]:
    """执行可复现的小实验，并返回配置、输入版本和汇总结果。"""
    if rounds < 1:
        raise ValueError("rounds must be at least 1")
    rng = random.Random(seed)
    scores = [round(rng.random(), 6) for _ in range(rounds)]
    return {
        "config": {"seed": seed, "rounds": rounds},
        "data_version": data_version,
        "mean_score": round(sum(scores) / len(scores), 6),
        "scores": scores,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--data-version", required=True)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.seed, args.data_version, args.rounds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(serialized, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
