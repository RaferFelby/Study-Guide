import hashlib
import json
from copy import deepcopy


def fingerprint(owner: str, tool: str, arguments: dict):
    payload = json.dumps(
        {"owner": owner, "tool": tool, "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_digest(record):
    payload = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self):
        self.records = []

    def append(self, owner, tool, arguments, decision, code):
        record = {
            "sequence": len(self.records) + 1,
            "owner": owner,
            "tool": tool,
            "arguments_sha256": fingerprint(owner, tool, arguments),
            "decision": decision,
            "code": code,
            "previous_hash": self.records[-1]["record_hash"]
            if self.records
            else "0" * 64,
        }
        record["record_hash"] = record_digest(record)
        self.records.append(record)

    def snapshot(self):
        return deepcopy(self.records)


def verify_chain(records):
    previous = "0" * 64
    for index, record in enumerate(records, start=1):
        content = dict(record)
        expected_hash = content.pop("record_hash", None)
        if (
            content.get("sequence") != index
            or content.get("previous_hash") != previous
            or record_digest(content) != expected_hash
        ):
            return False
        previous = expected_hash
    return True
