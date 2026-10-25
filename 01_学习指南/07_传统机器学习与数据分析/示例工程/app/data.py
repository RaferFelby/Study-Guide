"""生成一个可重复的、带缺失值和类别特征的教学数据集。"""

from __future__ import annotations

import numpy as np
import pandas as pd

RANDOM_SEED = 34


def make_customer_dataset(sample_count: int = 1200) -> pd.DataFrame:
    """生成模拟续费数据；标签仅用于练习，不代表真实客户结论。"""
    if sample_count < 100:
        raise ValueError("sample_count 至少为 100，才能留下可用的数据划分")

    random_generator = np.random.default_rng(RANDOM_SEED)
    age = random_generator.integers(18, 76, size=sample_count)
    monthly_usage = random_generator.normal(30, 12, size=sample_count).clip(0, 80)
    late_payments = random_generator.poisson(0.6, size=sample_count)
    plan_type = random_generator.choice(
        ["basic", "plus", "premium"], size=sample_count, p=[0.45, 0.35, 0.20]
    )
    region = random_generator.choice(["north", "south", "west"], size=sample_count)

    plan_effect = np.select(
        [plan_type == "basic", plan_type == "plus", plan_type == "premium"],
        [0.55, 0.0, -0.45],
    )
    log_odds = (
        -0.5
        + 0.55 * late_payments
        - 0.035 * monthly_usage
        + 0.008 * (age - 40)
        + plan_effect
    )
    renewal_probability = 1 / (1 + np.exp(-log_odds))
    renewed = random_generator.binomial(1, renewal_probability)

    frame = pd.DataFrame(
        {
            "age": age,
            "monthly_usage": monthly_usage.round(1),
            "late_payments": late_payments,
            "plan_type": plan_type,
            "region": region,
            "renewed": renewed,
        }
    )

    # 缺失值只放在输入特征中；目标列保持完整，便于定义预测任务。
    for column_name in ["age", "monthly_usage", "plan_type"]:
        missing_rows = random_generator.choice(
            sample_count, size=sample_count // 20, replace=False
        )
        frame.loc[missing_rows, column_name] = np.nan

    return frame
