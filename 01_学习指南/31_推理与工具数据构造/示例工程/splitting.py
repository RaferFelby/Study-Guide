"""按来源/题族/规范化重复的连通分组切分，再独立检查泄漏。"""

import copy
import random

from data import fingerprint


def group_related(samples):
    groups = []
    remaining = set(range(len(samples)))
    while remaining:
        pending = [min(remaining)]
        component = []
        while pending:
            index = pending.pop()
            if index not in remaining:
                continue
            remaining.remove(index)
            sample = samples[index]
            component.append(sample)
            for other in sorted(remaining):
                candidate = samples[other]
                if (
                    sample["source_id"] == candidate["source_id"]
                    or sample["family_id"] == candidate["family_id"]
                    or fingerprint(sample) == fingerprint(candidate)
                ):
                    pending.append(other)
        groups.append(component)
    return groups


def check_leakage(splits):
    if set(splits) != {"train", "dev", "test"}:
        raise ValueError("需同时提供train/dev/test")
    findings = []
    for field in ("sample_id", "source_id", "family_id", "fingerprint"):
        owner = {}
        for split_name, samples in splits.items():
            for sample in samples:
                value = fingerprint(sample) if field == "fingerprint" else sample[field]
                if value in owner and owner[value] != split_name:
                    findings.append(
                        {
                            "field": field,
                            "splits": sorted([owner[value], split_name]),
                            "sample_id": sample["sample_id"],
                        }
                    )
                owner[value] = split_name
    return findings


def split_samples(samples, seed=17):
    groups = group_related(sorted(samples, key=lambda sample: sample["sample_id"]))
    if len(groups) < 5:
        raise ValueError("至少5个独立来源组才能演示三份非空切分")
    if type(seed) is not int:
        raise ValueError("随机种子需为整数")
    random.Random(seed).shuffle(groups)
    train_end, dev_end = int(len(groups) * 0.6), int(len(groups) * 0.8)
    ranges = {
        "train": groups[:train_end],
        "dev": groups[train_end:dev_end],
        "test": groups[dev_end:],
    }
    splits = {}
    for name, selected in ranges.items():
        splits[name] = [copy.deepcopy(sample) for group in selected for sample in group]
    if check_leakage(splits):
        raise AssertionError("分组切分后不应出现跨集合泄漏")
    return splits
