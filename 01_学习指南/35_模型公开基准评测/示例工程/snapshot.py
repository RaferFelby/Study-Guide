"""显式下载固定提交的公开文本数据；默认导入不联网。"""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

COMMIT = "3101c7d5072418e28b9008a6636bde82a006892c"
BASE_URL = f"https://raw.githubusercontent.com/openai/grade-school-math/{COMMIT}/"
MAX_BYTES = 16 * 1024 * 1024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(relative):
    request = urllib.request.Request(
        BASE_URL + relative, headers={"User-Agent": "LearningGuide"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("单文件超过16MiB，停止下载")
    return data


def create_snapshot(output):
    output.mkdir(parents=True, exist_ok=False)
    files = {
        "archive.jsonl": "grade_school_math/data/example_model_solutions.jsonl",
        "GSM8K-LICENSE.txt": "LICENSE",
    }
    sources = {}
    for name, relative in files.items():
        path = output / name
        path.write_bytes(download(relative))
        sources[name] = {
            "url": BASE_URL + relative,
            "sha256": digest(path),
            "bytes": path.stat().st_size,
        }
    raw_train = download("grade_school_math/data/train.jsonl")
    demos = [json.loads(line) for line in raw_train.decode("utf-8").splitlines()[:5]]
    demo_path = output / "demos.json"
    demo_path.write_text(
        json.dumps(demos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sources["demos.json"] = {
        "url": BASE_URL + "grade_school_math/data/train.jsonl",
        "sha256": digest(demo_path),
        "upstream_sha256": hashlib.sha256(raw_train).hexdigest(),
        "selection": "first_5_training_rows_only",
    }
    manifest = {
        "benchmark": "GSM8K_archived_model_outputs",
        "commit": COMMIT,
        "snapshot_date": "2026-10-13",
        "scope": "public_saved_outputs_replay_not_live_model_generation",
        "sources": sources,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(create_snapshot(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
