"""显式生成阅读检查与试点建议；不联网核验论文语义。"""

import argparse
import json
from pathlib import Path

from catalog import reading_cards
from decision import decide, lora_demo_facts
from evidence import validate_note


def run(output_dir):
    cards = [validate_note(card) for card in reading_cards()]
    report = {
        "scope": "author_structured_reading_demo_not_automatic_fact_check",
        "checked_date": "2026-10-14",
        "cards": cards,
        "decision_facts": lora_demo_facts(),
        "decision": decide(lora_demo_facts()),
        "limits": "five_overview_cards_and_one_selected_LoRA_deep_read_not_six_full_reproductions",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output_dir)
    print("阅读卡", len(report["cards"]), report["decision"])


if __name__ == "__main__":
    main()
