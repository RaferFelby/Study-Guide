import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from database import connect_writer, create_backup, initialize, restore_backup
from importing import import_rows, load_api_fixture, load_csv
from queries import QUERY_TASKS
from readonly import ReadOnlyService


def main() -> None:
    # 唯一临时目录位于工程内；只清理本次程序自己创建的目录。
    with TemporaryDirectory(prefix="sql-demo-", dir=Path(__file__).parent) as directory:
        path = Path(directory) / "work.db"
        connection = connect_writer(path)
        try:
            initialize(connection)
            rows = load_csv(Path(__file__).parent / "fixtures/tickets.csv")
            print("首次导入：", import_rows(connection, rows))
            print("重复导入：", import_rows(connection, rows))
            with connection:
                connection.executemany(
                    "INSERT INTO events(ticket_id,event_type,created_at) VALUES(?,?,?)",
                    [
                        (1, "opened", "2026-10-01"),
                        (1, "comment", "2026-10-02"),
                        (2, "opened", "2026-10-02"),
                    ],
                )
            service = ReadOnlyService(path, "alpha", max_rows=10)
            sample_arguments = {
                "user_tickets": {"user_id": 1},
                "status_filter": {"status": "open"},
                "keyset_page": {"after_id": 3},
            }
            for name, (question, _, _) in QUERY_TASKS.items():
                print(
                    name,
                    question,
                    service.query(name, sample_arguments.get(name))["rows"],
                )
            duplicate_counts = connection.execute(
                "SELECT COUNT(t.ticket_id),COUNT(DISTINCT t.ticket_id) FROM tickets t JOIN events e ON e.ticket_id=t.ticket_id WHERE t.tenant_id=?",
                ("alpha",),
            ).fetchone()
            print("JOIN后行数/不同工单数：", tuple(duplicate_counts))
            plan = connection.execute(
                "EXPLAIN QUERY PLAN SELECT external_id FROM tickets WHERE tenant_id=? AND status=? ORDER BY created_at DESC,ticket_id DESC",
                ("alpha", "open"),
            ).fetchall()
            print("查询计划：", [tuple(row) for row in plan])
            print(
                "API夹具增量：",
                import_rows(
                    connection,
                    load_api_fixture(
                        Path(__file__).parent / "fixtures/api_update.json"
                    ),
                ),
            )
            backup_path = Path(directory) / "backup.db"
            restored_path = Path(directory) / "restored.db"
            create_backup(connection, backup_path)
            restore_backup(backup_path, restored_path)
            restored = sqlite3.connect(restored_path)
            try:
                print(
                    "恢复工单数：",
                    restored.execute("SELECT COUNT(*) FROM tickets").fetchone()[0],
                )
            finally:
                restored.close()
        finally:
            connection.close()


if __name__ == "__main__":
    main()
