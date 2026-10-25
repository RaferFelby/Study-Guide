"""把CSV/API示例统一到业务表；同版本同内容跳过，冲突拒绝。"""

import csv
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path


def parse_integer(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TypeError("整数字段必须是整数或整数字符串，不能是布尔值/小数")
    return int(value)


def load_api_fixture(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    rows = []
    for item in payload["items"]:
        rows.append(
            {
                "tenant_id": item["tenant"],
                "source_id": "helpdesk",
                "external_id": item["id"],
                "source_version": item["version"],
                "user_id": item["owner"],
                "product_id": item.get("product"),
                "status": item["state"],
                "priority": item["priority"],
                "amount_cents": item.get("amount_cents"),
                "created_at": item["created_at"],
            }
        )
    return rows


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def normalize_row(row: dict) -> dict:
    normalized = {
        "tenant_id": str(row["tenant_id"]),
        "source_id": str(row["source_id"]),
        "external_id": str(row["external_id"]),
        "source_version": parse_integer(row["source_version"]),
        "user_id": parse_integer(row["user_id"]),
        "product_id": parse_integer(row["product_id"])
        if row.get("product_id") not in {None, ""}
        else None,
        "status": str(row["status"]),
        "priority": parse_integer(row["priority"]),
        "amount_cents": parse_integer(row["amount_cents"])
        if row.get("amount_cents") not in {None, ""}
        else None,
        "created_at": str(row["created_at"]),
    }
    if not all(
        normalized[key].strip() for key in ["tenant_id", "source_id", "external_id"]
    ):
        raise ValueError("来源、外部ID和租户不能为空")
    timestamp = datetime.fromisoformat(normalized["created_at"])
    if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
        raise ValueError("时间必须有UTC时区")
    normalized["created_at"] = timestamp.isoformat(timespec="seconds")
    payload = {
        key: value for key, value in normalized.items() if key != "source_version"
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    normalized["payload_hash"] = hashlib.sha256(serialized).hexdigest()
    return normalized


def import_rows(connection: sqlite3.Connection, rows: list[dict]) -> dict[str, int]:
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    with connection:
        for row in rows:
            item = normalize_row(row)
            identity = (item["tenant_id"], item["source_id"], item["external_id"])
            previous = connection.execute(
                "SELECT source_version,payload_hash FROM tickets WHERE tenant_id=? AND source_id=? AND external_id=?",
                identity,
            ).fetchone()
            if previous is not None:
                if item["source_version"] < previous["source_version"]:
                    counts["skipped"] += 1
                    continue
                if item["source_version"] == previous["source_version"]:
                    if item["payload_hash"] != previous["payload_hash"]:
                        raise ValueError("同来源同版本内容冲突，不能静默覆盖")
                    counts["skipped"] += 1
                    continue
                connection.execute(
                    "UPDATE tickets SET source_version=:source_version,payload_hash=:payload_hash,user_id=:user_id,product_id=:product_id,status=:status,priority=:priority,amount_cents=:amount_cents,created_at=:created_at WHERE tenant_id=:tenant_id AND source_id=:source_id AND external_id=:external_id",
                    item,
                )
                counts["updated"] += 1
            else:
                connection.execute(
                    "INSERT INTO tickets(tenant_id,source_id,external_id,source_version,payload_hash,user_id,product_id,status,priority,amount_cents,created_at) VALUES(:tenant_id,:source_id,:external_id,:source_version,:payload_hash,:user_id,:product_id,:status,:priority,:amount_cents,:created_at)",
                    item,
                )
                counts["inserted"] += 1
    return counts
