"""单操作者 SQLite 经验记录：追加创建与撤回，按任务开始时点读取。"""

import argparse
import json
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict
from pathlib import Path

from experience_transfer import UnitExperience


def require_order(value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError("任务顺序必须是正整数")


def require_text(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("编号、版本与说明必须是非空文字")


def create_store(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x"):
        pass
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE store_meta (version INTEGER NOT NULL);
            INSERT INTO store_meta VALUES (1);
            CREATE TABLE entries (
                entry_id TEXT PRIMARY KEY,
                source_task_id TEXT NOT NULL,
                available_after INTEGER NOT NULL CHECK(available_after > 0),
                rule_version TEXT NOT NULL,
                evidence_note TEXT NOT NULL
            );
            CREATE TABLE revocations (
                entry_id TEXT PRIMARY KEY REFERENCES entries(entry_id),
                after_task INTEGER NOT NULL CHECK(after_task > 0),
                reason TEXT NOT NULL
            );
            """
        )


@contextmanager
def connect_store(path: Path, *, readonly: bool):
    if not path.is_file():
        raise ValueError("经验库不存在；请先执行 init")
    mode = "ro" if readonly else "rw"
    uri = path.resolve().as_uri() + f"?mode={mode}"
    with closing(sqlite3.connect(uri, uri=True)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        if connection.execute("SELECT version FROM store_meta").fetchall() != [(1,)]:
            raise ValueError("不支持的经验库版本")
        connection.execute("BEGIN" if readonly else "BEGIN IMMEDIATE")
        yield connection


def check_append_order(connection: sqlite3.Connection, after_task: int) -> None:
    last_order = connection.execute(
        """SELECT MAX(position) FROM (
               SELECT available_after AS position FROM entries
               UNION ALL SELECT after_task AS position FROM revocations
           )"""
    ).fetchone()[0]
    if last_order is not None and after_task < last_order:
        raise ValueError("不能补写到已记录事件之前；请记录真实的可用时点")


def add_entry(
    path: Path, entry_id: str, experience: UnitExperience, evidence_note: str
) -> None:
    require_order(experience.available_after)
    for value in (
        entry_id,
        experience.source_task_id,
        experience.rule_version,
        evidence_note,
    ):
        require_text(value)
    if experience.status != "active":
        raise ValueError("新增经验必须是 active；撤回请使用 revoke")
    with connect_store(path, readonly=False) as connection:
        check_append_order(connection, experience.available_after)
        if connection.execute(
            "SELECT 1 FROM entries WHERE entry_id=?", (entry_id,)
        ).fetchone():
            raise ValueError("经验编号已存在，不覆盖旧记录")
        connection.execute(
            "INSERT INTO entries VALUES (?, ?, ?, ?, ?)",
            (
                entry_id,
                experience.source_task_id,
                experience.available_after,
                experience.rule_version,
                evidence_note,
            ),
        )


def revoke_entry(path: Path, entry_id: str, after_task: int, reason: str) -> None:
    require_order(after_task)
    require_text(entry_id)
    require_text(reason)
    with connect_store(path, readonly=False) as connection:
        check_append_order(connection, after_task)
        if not connection.execute(
            "SELECT 1 FROM entries WHERE entry_id=?", (entry_id,)
        ).fetchone():
            raise ValueError("经验编号不存在")
        if connection.execute(
            "SELECT 1 FROM revocations WHERE entry_id=?", (entry_id,)
        ).fetchone():
            raise ValueError("该经验已有撤回记录")
        connection.execute(
            "INSERT INTO revocations VALUES (?, ?, ?)", (entry_id, after_task, reason)
        )


def load_snapshot(path: Path, before_task: int) -> list[dict]:
    """重建指定任务开始前的记录；保留 revoked 项供解释，不自动选用。"""
    require_order(before_task)
    with connect_store(path, readonly=True) as connection:
        rows = connection.execute(
            """SELECT entry_id, source_task_id, available_after, rule_version, evidence_note
               FROM entries WHERE available_after < ? ORDER BY available_after, entry_id""",
            (before_task,),
        ).fetchall()
        revoked = dict(
            connection.execute(
                "SELECT entry_id, reason FROM revocations WHERE after_task < ?",
                (before_task,),
            ).fetchall()
        )
    snapshot = []
    for entry_id, source_task_id, available_after, rule_version, evidence_note in rows:
        status = "revoked" if entry_id in revoked else "active"
        experience = UnitExperience(
            source_task_id, available_after, rule_version, status
        )
        snapshot.append(
            {
                "entry_id": entry_id,
                "experience": asdict(experience),
                "evidence_note": evidence_note,
                "revocation_reason": revoked.get(entry_id),
            }
        )
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    add = commands.add_parser("add")
    add.add_argument("--id", required=True)
    add.add_argument("--source-task", required=True)
    add.add_argument("--after-task", required=True, type=int)
    add.add_argument("--rule", required=True)
    add.add_argument("--evidence", required=True)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("--id", required=True)
    revoke.add_argument("--after-task", required=True, type=int)
    revoke.add_argument("--reason", required=True)
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--before-task", required=True, type=int)
    args = parser.parse_args()
    if args.command == "init":
        create_store(args.db)
        print("经验库已创建")
    elif args.command == "add":
        experience = UnitExperience(args.source_task, args.after_task, args.rule)
        add_entry(args.db, args.id, experience, args.evidence)
        print("经验已记录")
    elif args.command == "revoke":
        revoke_entry(args.db, args.id, args.after_task, args.reason)
        print("撤回事件已记录")
    else:
        print(
            json.dumps(
                load_snapshot(args.db, args.before_task), ensure_ascii=False, indent=2
            )
        )


if __name__ == "__main__":
    main()
