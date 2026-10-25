"""先列配置差异，再决定分数是否具有可比性。"""

FIELDS = (
    "dataset_revision",
    "split",
    "selection",
    "shots",
    "prompt_hash",
    "scoring",
    "extractor",
    "precision",
    "quantization",
    "decoding",
    "max_new_tokens",
    "model_revision",
)


def compare_configs(local, published):
    rows = []
    for field in FIELDS:
        left, right = local.get(field), published.get(field)
        status = (
            "unknown"
            if left is None or right is None
            else "same"
            if left == right
            else "different"
        )
        rows.append(
            {"field": field, "local": left, "published": right, "status": status}
        )
    return {
        "directly_comparable": all(row["status"] == "same" for row in rows),
        "differences": rows,
    }
