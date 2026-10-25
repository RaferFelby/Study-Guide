"""校验公开数据快照；提示中不放入待评问题的参考答案。"""

import json
from pathlib import Path

from scoring import extract_number
from snapshot import digest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ARCHIVE_MODELS = ("6b_finetuning", "6b_verification")
PROMPT_VERSION = "gsm8k_teaching_hash_final_v1"


def load_snapshot(directory=FIXTURES):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name, source in manifest["sources"].items():
        if digest(directory / name) != source["sha256"]:
            raise ValueError(f"数据快照哈希不符：{name}")
    with (directory / "archive.jsonl").open(encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]
    questions = set()
    for record in records:
        question = record["question"]
        if not isinstance(question, str) or not question or question in questions:
            raise ValueError("题目为空或重复")
        questions.add(question)
        if extract_number(record["ground_truth"]) is None:
            raise ValueError("参考答案无法抽取")
        for name in ARCHIVE_MODELS:
            output = record[name]
            if (
                not isinstance(output["solution"], str)
                or type(output["is_correct"]) is not bool
            ):
                raise ValueError("归档回答字段不符")
    if not records:
        raise ValueError("公开快照不能为空")
    demos = json.loads((directory / "demos.json").read_text(encoding="utf-8"))
    return records, demos, manifest


def build_prompt(record, demos, shots=0):
    if type(shots) is not int or not 0 <= shots <= len(demos):
        raise ValueError("示范数超出可用训练示范")
    question = record["question"]
    selected = demos[:shots]
    if any(demo["question"] == question for demo in selected):
        raise ValueError("不能把待评题作为自己的示范")
    sections = ["Solve the math problem. End with a line: #### number."]
    for demo in selected:
        sections.append(f"Question: {demo['question']}\nAnswer: {demo['answer']}")
    sections.append(f"Question: {question}\nAnswer:")
    return "\n\n".join(sections)
