"""生成候选数据包；自动检查不冒充真实人工抽检或已训练成果。"""

import argparse
import hashlib
import json
from pathlib import Path

from data import deduplicate, make_raw_samples, make_sources
from formatting import encode_training_sample, make_review_sheet, to_messages
from splitting import check_leakage, split_samples
from validation import clean_samples


def prepare_dataset():
    sources, raw = make_sources(), make_raw_samples()
    valid, rejected = clean_samples(raw, sources)
    unique, duplicates = deduplicate(valid)
    splits = split_samples(unique)
    for sample in unique:
        encode_training_sample(sample)
    digest = hashlib.sha256(
        json.dumps(unique, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    report = {
        "raw": len(raw),
        "auto_valid": len(valid),
        "rejected": rejected,
        "duplicates": duplicates,
        "unique": len(unique),
        "split_sizes": {name: len(samples) for name, samples in splits.items()},
        "split_groups": {
            name: len({sample["family_id"] for sample in samples})
            for name, samples in splits.items()
        },
        "leakage": check_leakage(splits),
        "dataset_sha256": digest,
        "generator": "fixed-addition-v1",
        "cleaning_rules": {
            "validator": "fixed-addition-validation-v1",
            "deduplication": "same-content-and-evidence-v1",
            "split": "connected-source-family-fingerprint-v1",
            "split_seed": 17,
            "template": "teaching-byte-chat-v1",
            "maximum_bytes": 2048,
        },
        "generation_model": None,
        "usage_policy": "local_teaching_only",
        "source_kind": "author_synthetic_fixture",
        "human_review_complete": False,
        "stage": "candidate_only_pending_human_review",
        "training_executed": False,
        "learning_curve_measured": False,
        "real_model_template_verified": False,
    }
    return splits, report, make_review_sheet(unique)


def write_dataset(output_dir):
    splits, report, review = prepare_dataset()
    output_dir.mkdir(parents=True, exist_ok=False)
    candidates = [sample for samples in splits.values() for sample in samples]
    for name, records in (
        ("raw.jsonl", make_raw_samples()),
        ("candidates.jsonl", candidates),
    ):
        with (output_dir / name).open("x", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
    for name, samples in splits.items():
        with (output_dir / f"{name}.jsonl").open("x", encoding="utf-8") as file:
            for sample in samples:
                file.write(
                    json.dumps(
                        {
                            "sample_id": sample["sample_id"],
                            "source_id": sample["source_id"],
                            "family_id": sample["family_id"],
                            "messages": to_messages(sample),
                            "stage": report["stage"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    for name, value in (
        ("report.json", report),
        ("review_sheet.json", review),
        ("sources.json", make_sources()),
    ):
        with (output_dir / name).open("x", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("report-my-01"))
    args = parser.parse_args()
    print(json.dumps(write_dataset(args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
