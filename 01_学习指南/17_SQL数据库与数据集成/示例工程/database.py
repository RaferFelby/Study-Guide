import sqlite3
from pathlib import Path


def connect_writer(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version == 1:
        return
    if version != 0:
        raise ValueError("不支持该数据库版本")
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    connection.executescript(schema)
    with connection:
        connection.executemany(
            "INSERT INTO users VALUES (?, ?, ?)",
            [
                (1, "alpha", "Alice"),
                (2, "alpha", "Bob"),
                (3, "alpha", "Carol"),
                (4, "beta", "Dora"),
            ],
        )
        connection.executemany(
            "INSERT INTO products VALUES (?, ?)",
            [(1, "Storage"), (2, "Compute"), (3, "Analytics")],
        )


def create_backup(connection: sqlite3.Connection, path: Path) -> None:
    if path.exists():
        raise FileExistsError("备份目标已存在，不覆盖")
    target = sqlite3.connect(path)
    try:
        connection.backup(target)
    finally:
        target.close()


def restore_backup(backup_path: Path, restored_path: Path) -> None:
    if restored_path.exists():
        raise FileExistsError("恢复目标已存在，不覆盖")
    source = sqlite3.connect(backup_path.resolve().as_uri() + "?mode=ro", uri=True)
    target = sqlite3.connect(restored_path)
    try:
        source.backup(target)
    finally:
        source.close()
        target.close()
