import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from database import connect_writer, create_backup, initialize, restore_backup
from importing import import_rows, load_api_fixture, load_csv
from readonly import QueryLimitError, ReadOnlyService, authorize_read


@pytest.fixture
def database():
    with TemporaryDirectory(prefix="sql-test-", dir=Path(__file__).parent) as directory:
        path = Path(directory) / "work.db"
        connection = connect_writer(path)
        initialize(connection)
        rows = load_csv(Path(__file__).parents[1] / "fixtures/tickets.csv")
        import_rows(connection, rows)
        yield path, connection, rows
        connection.close()


def test_repeat_import_is_idempotent_and_source_version_updates(database):
    _, connection, rows = database
    assert import_rows(connection, rows) == {"inserted": 0, "updated": 0, "skipped": 7}
    api = load_api_fixture(Path(__file__).parents[1] / "fixtures/api_update.json")
    assert import_rows(connection, api) == {"inserted": 1, "updated": 1, "skipped": 0}
    assert import_rows(connection, api) == {"inserted": 0, "updated": 0, "skipped": 2}
    assert connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 8
    assert import_rows(connection, rows)["updated"] == 0


def test_same_version_changed_payload_conflicts_and_batch_rolls_back(database):
    _, connection, rows = database
    new = {**rows[0], "external_id": "NEW"}
    conflict = {**rows[1], "status": "open"}
    with pytest.raises(ValueError, match="冲突"):
        import_rows(connection, [new, conflict])
    assert connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 7


def test_foreign_key_prevents_cross_tenant_user_reference(database):
    _, connection, rows = database
    wrong = {**rows[0], "external_id": "WRONG", "user_id": 4}
    with pytest.raises(sqlite3.IntegrityError):
        import_rows(connection, [wrong])


def test_join_duplicates_null_and_unmatched_rows(database):
    path, connection, _ = database
    with connection:
        connection.executemany(
            "INSERT INTO events(ticket_id,event_type,created_at) VALUES(?,?,?)",
            [
                (1, "opened", "2026-10-01"),
                (1, "comment", "2026-10-02"),
                (2, "opened", "2026-10-02"),
            ],
        )
    counts = connection.execute(
        "SELECT COUNT(t.ticket_id),COUNT(DISTINCT t.ticket_id) FROM tickets t JOIN events e ON e.ticket_id=t.ticket_id"
    ).fetchone()
    assert tuple(counts) == (3, 2)
    service = ReadOnlyService(path, "alpha", max_rows=10)
    assert service.query("users_without_tickets")["rows"] == [{"name": "Carol"}]
    assert service.query("missing_amount")["rows"] == [{"external_id": "T-003"}]
    average = service.query("average_amount")["rows"][0]
    assert average == {"average_cents": 2000.0, "known_amounts": 5, "tickets": 6}
    products = service.query("product_counts")["rows"]
    assert products[-1] == {"name": "Analytics", "ticket_count": 0}


def test_ten_business_queries_have_expected_results(database):
    path, _, _ = database
    service = ReadOnlyService(path, "alpha", max_rows=10)
    assert len(service.query("open_tickets")["rows"]) == 3
    assert len(service.query("user_tickets", {"user_id": 1})["rows"]) == 3
    assert service.query("status_counts")["rows"] == [
        {"status": "open", "ticket_count": 3},
        {"status": "resolved", "ticket_count": 3},
    ]
    assert service.query("resolution_rate")["rows"] == [{"resolution_rate": 0.5}]
    assert service.query("latest_per_user")["rows"] == [
        {"user_id": 1, "external_id": "T-005"},
        {"user_id": 2, "external_id": "T-006"},
    ]
    assert {row["external_id"] for row in service.query("above_average")["rows"]} == {
        "T-004",
        "T-006",
    }


def test_bound_parameter_does_not_change_query_structure(database):
    path, _, _ = database
    service = ReadOnlyService(path, "alpha", max_rows=10)
    assert service.query("status_filter", {"status": "open' OR 1=1 --"})["rows"] == []
    assert all(
        not row["external_id"].startswith("B-")
        for row in service.query("status_filter", {"status": "open"})["rows"]
    )
    with pytest.raises(ValueError):
        service.query("open_tickets", {"tenant_id": "beta"})


def test_read_only_connection_and_authorizer_deny_writes(database):
    path, _, _ = database
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.set_authorizer(authorize_read)
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("DELETE FROM tickets")
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("ATTACH DATABASE ':memory:' AS other")
    finally:
        connection.close()


def test_row_limit_keyset_and_vm_budget(database):
    path, _, _ = database
    service = ReadOnlyService(path, "alpha", max_rows=2)
    first = service.query("keyset_page", {"after_id": 0})
    assert first["truncated"]
    last_id = first["rows"][-1]["ticket_id"]
    second = service.query("keyset_page", {"after_id": last_id})
    assert not {row["ticket_id"] for row in first["rows"]} & {
        row["ticket_id"] for row in second["rows"]
    }
    with pytest.raises(QueryLimitError):
        ReadOnlyService(path, "alpha", max_vm_steps=1).query("open_tickets")


def test_explain_uses_composite_index(database):
    _, connection, _ = database
    plan = connection.execute(
        "EXPLAIN QUERY PLAN SELECT external_id FROM tickets WHERE tenant_id=? AND status=? ORDER BY created_at DESC,ticket_id DESC",
        ("alpha", "open"),
    ).fetchall()
    assert any("idx_tickets_tenant_status_created" in row[3] for row in plan)


def test_backup_restore_matches_all_business_rows_and_rejects_overwrite(database):
    path, connection, _ = database
    backup = path.parent / "backup.db"
    restored = path.parent / "restored.db"
    create_backup(connection, backup)
    restore_backup(backup, restored)
    restored_connection = sqlite3.connect(restored)
    try:
        original = [
            tuple(row)
            for row in connection.execute("SELECT * FROM tickets ORDER BY ticket_id")
        ]
        assert (
            restored_connection.execute(
                "SELECT * FROM tickets ORDER BY ticket_id"
            ).fetchall()
            == original
        )
        assert (
            restored_connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        )
    finally:
        restored_connection.close()
    with pytest.raises(FileExistsError):
        create_backup(connection, backup)
    with pytest.raises(FileExistsError):
        restore_backup(backup, restored)


@pytest.mark.parametrize(
    "change",
    [
        {"priority": "0"},
        {"amount_cents": "-1"},
        {"source_version": True},
        {"created_at": "2026-10-01T09:00:00"},
    ],
)
def test_invalid_import_never_adds_row(database, change):
    _, connection, rows = database
    wrong = {**rows[0], "external_id": "BAD", **change}
    with pytest.raises((ValueError, TypeError, sqlite3.IntegrityError)):
        import_rows(connection, [wrong])
    assert connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 7
