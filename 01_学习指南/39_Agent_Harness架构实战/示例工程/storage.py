"""单进程教学会话：状态、事件与本地笔记使用同一个 SQLite 事务。"""

import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from contracts import GOAL


@contextmanager
def connect(path: Path):
    with closing(sqlite3.connect(path)) as connection, connection:
        yield connection


def create_session(path: Path, backend: str, max_calls: int = 6) -> None:
    if type(max_calls) is not int or not 1 <= max_calls <= 20:
        raise ValueError("max_calls must be an integer in 1..20")
    path.parent.mkdir(parents=True, exist_ok=True)
    # x 模式拒绝覆盖已有会话，即使另一个进程刚刚创建了同名文件。
    with path.open("x"):
        pass
    state = {
        "version": 1,
        "goal": GOAL,
        "backend": backend,
        "max_calls": max_calls,
        "calls": 0,
        "status": "ready",
        "pending": None,
        "observations": [],
        "answer": None,
    }
    with connect(path) as connection:
        connection.execute(
            "CREATE TABLE session (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE events (sequence INTEGER PRIMARY KEY, kind TEXT, body TEXT)"
        )
        connection.execute(
            "CREATE TABLE notes (action_key TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        save(connection, state, "created", {"backend": backend})


def load(path: Path) -> dict:
    if not path.is_file():
        raise ValueError("session does not exist; use start first")
    with connect(path) as connection:
        row = connection.execute("SELECT body FROM session WHERE id=1").fetchone()
    state = json.loads(row[0])
    if state.get("version") != 1:
        raise ValueError("unsupported session version")
    return state


def save(connection, state: dict, kind: str, details: dict) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO session VALUES (1, ?)",
        (json.dumps(state, ensure_ascii=False),),
    )
    connection.execute(
        "INSERT INTO events(kind, body) VALUES (?, ?)",
        (kind, json.dumps(details, ensure_ascii=False)),
    )


def commit(path: Path, state: dict, kind: str, details: dict) -> None:
    with connect(path) as connection:
        save(connection, state, kind, details)


def inspect_session(path: Path) -> dict:
    state = load(path)
    with connect(path) as connection:
        events = connection.execute(
            "SELECT sequence, kind, body FROM events ORDER BY sequence"
        ).fetchall()
        notes = connection.execute(
            "SELECT body FROM notes ORDER BY action_key"
        ).fetchall()
    records = [
        {"sequence": row[0], "kind": row[1], "details": json.loads(row[2])}
        for row in events
    ]
    return {"state": state, "events": records, "notes": [row[0] for row in notes]}
