"""合成偏好记忆：显式确认、用户隔离、版本/到期、删除；SQLite标准库。"""

import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

ALLOWED_KEYS = {"preferred_language", "answer_style", "context_goal"}


def utc_timestamp(value):
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("时间需为带时区的datetime")
    return value.astimezone(timezone.utc).isoformat()


def validate_owner(owner):
    if not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,32}", owner):
        raise ValueError("用户范围需明确、长度1至32")


class MemoryStore:
    def __init__(self, path):
        self.path = path
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    owner TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
                    source TEXT NOT NULL, source_time TEXT NOT NULL,
                    updated_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                    confidence REAL NOT NULL, version INTEGER NOT NULL,
                    PRIMARY KEY (owner, key)
                );
                CREATE TABLE IF NOT EXISTS events (
                    owner TEXT NOT NULL, key TEXT NOT NULL, version INTEGER NOT NULL,
                    kind TEXT NOT NULL, happened_at TEXT NOT NULL
                );
            """)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def write(
        self,
        owner,
        key,
        value,
        source,
        source_time,
        now,
        confirmed=False,
        confidence=0.95,
        ttl_days=30,
    ):
        validate_owner(owner)
        if confirmed is not True:
            raise ValueError("长期写入需要明确用户确认，猜测不写为事实")
        if key not in ALLOWED_KEYS:
            raise ValueError("仅存三类已说明的个人偏好，不存政策/凭据/系统权限")
        if (
            not isinstance(value, str)
            or not 1 <= len(value.strip()) <= 200
            or not isinstance(source, str)
            or not 1 <= len(source) <= 100
        ):
            raise ValueError("value/source需为规定范围的非空文本")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("confidence需0至1有限数；本例为标签，不是校准概率")
        if type(ttl_days) is not int or not 1 <= ttl_days <= 365:
            raise ValueError("ttl_days需1至365整数")
        source_stamp, stamp = utc_timestamp(source_time), utc_timestamp(now)
        if source_stamp > stamp:
            raise ValueError("来源时间不能晚于当前时间")
        expires = utc_timestamp(now + timedelta(days=ttl_days))
        with self.connect() as connection:
            # 先锁写事务再读取版本，防止并发写者基于相同旧版本更新。
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT * FROM memories WHERE owner=? AND key=?", (owner, key)
            ).fetchone()
            if previous and (
                stamp < previous["updated_at"] or source_stamp < previous["source_time"]
            ):
                raise ValueError("旧时间记录不能覆盖较新确认")
            if (
                previous
                and previous["value"] == value.strip()
                and previous["source"] == source
                and previous["source_time"] == source_stamp
                and previous["confidence"] == confidence
                and stamp < previous["expires_at"]
            ):
                return {"status": "unchanged", "version": previous["version"]}
            version = previous["version"] + 1 if previous else 1
            connection.execute(
                """INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner,key) DO UPDATE SET value=excluded.value,
                source=excluded.source, source_time=excluded.source_time,
                updated_at=excluded.updated_at, expires_at=excluded.expires_at,
                confidence=excluded.confidence, version=excluded.version""",
                (
                    owner,
                    key,
                    value.strip(),
                    source,
                    source_stamp,
                    stamp,
                    expires,
                    confidence,
                    version,
                ),
            )
            connection.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                (
                    owner,
                    key,
                    version,
                    "created" if previous is None else "updated",
                    stamp,
                ),
            )
        return {
            "status": "created" if previous is None else "updated",
            "version": version,
        }

    def retrieve(self, owner, now, minimum_confidence=0.8):
        validate_owner(owner)
        stamp = utc_timestamp(now)
        if (
            isinstance(minimum_confidence, bool)
            or not isinstance(minimum_confidence, (int, float))
            or not math.isfinite(minimum_confidence)
            or not 0 <= minimum_confidence <= 1
        ):
            raise ValueError("检索置信度阈值需0至1")
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM memories WHERE owner=? AND expires_at>? AND updated_at<=? AND confidence>=? ORDER BY key",
                (owner, stamp, stamp, minimum_confidence),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, owner, key=None):
        validate_owner(owner)
        if key is not None and key not in ALLOWED_KEYS:
            raise ValueError("删除键需为已支持偏好")
        condition = "owner=?" if key is None else "owner=? AND key=?"
        parameters = (owner,) if key is None else (owner, key)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM memories WHERE " + condition, parameters
            )
            removed = cursor.rowcount
            connection.execute("DELETE FROM events WHERE " + condition, parameters)
        return removed

    def event_count(self, owner):
        validate_owner(owner)
        with self.connect() as connection:
            return connection.execute(
                "SELECT count(*) FROM events WHERE owner=?", (owner,)
            ).fetchone()[0]
