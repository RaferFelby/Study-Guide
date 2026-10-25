import json
from pathlib import Path

from career import (
    audit_evidence,
    describe_evidence,
    summarize_applications,
    validate_jobs,
)


def main():
    root = Path(__file__).parent

    def read(name):
        return json.loads((root / "fixtures" / name).read_text(encoding="utf-8"))

    jobs = validate_jobs(read("jobs.json"))
    evidence = read("evidence.json")
    print("官方岗位快照", len(jobs), "检查日2026-10-11；不保证今天仍开放")
    print("结构证据", audit_evidence(evidence, root))
    print(describe_evidence(evidence))
    print("模拟复盘", summarize_applications(read("applications.json"), "2026-10-11"))


if __name__ == "__main__":
    main()
