"""以短连接保存任务；每次方法调用完成一个明确事务。"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


class ConflictError(ValueError):
    pass


class JobStore:
    def __init__(self, path: Path):
        self.path = path
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    request_key TEXT NOT NULL, question TEXT NOT NULL,
                    status TEXT NOT NULL, result TEXT,
                    UNIQUE(owner, request_key)
                )
            """)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=2)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self, owner: str, request_key: str, question: str):
        with self.connect() as connection:
            # BEGIN IMMEDIATE使本机并发的“查重→插入”成为一个写事务。
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM jobs WHERE owner=? AND request_key=?",
                (owner, request_key),
            ).fetchone()
            if existing:
                if existing["question"] != question:
                    raise ConflictError("同一个幂等键不能提交不同问题")
                return dict(existing), False
            job_id = uuid4().hex
            connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?, 'pending', NULL)",
                (job_id, owner, request_key, question),
            )
        return self.get(owner, job_id), True

    def get(self, owner: str, job_id: str):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE owner=? AND job_id=?", (owner, job_id)
            ).fetchone()
        return dict(row) if row else None

    def claim_next(self):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE status='pending' ORDER BY rowid LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE jobs SET status='running' WHERE job_id=?", (row["job_id"],)
            )
        return dict(row)

    def finish(self, job_id: str, status: str, result: dict):
        with self.connect() as connection:
            # 取消先发生时，迟到的完成结果不能覆盖cancelled。
            connection.execute(
                "UPDATE jobs SET status=?, result=? WHERE job_id=? AND status='running'",
                (status, json.dumps(result, ensure_ascii=False), job_id),
            )

    def cancel(self, owner: str, job_id: str):
        with self.connect() as connection:
            connection.execute(
                "UPDATE jobs SET status='cancelled' WHERE owner=? AND job_id=? "
                "AND status IN ('pending', 'running')",
                (owner, job_id),
            )
        return self.get(owner, job_id)

    def recover_running(self):
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status='failed', result=? WHERE status='running'",
                (json.dumps({"code": "interrupted_by_restart"}),),
            )
        return cursor.rowcount
