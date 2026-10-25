import pytest

from reprokit.data import InvalidTicket, count_statuses


def test_count_statuses_returns_both_categories() -> None:
    rows = [{"status": "open"}, {"status": "closed"}, {"status": "closed"}]

    assert count_statuses(rows) == {"open": 1, "closed": 2}


@pytest.mark.parametrize("row", [{}, {"status": "pending"}, {"status": 3}])
def test_count_statuses_rejects_invalid_rows(row: dict[str, object]) -> None:
    with pytest.raises(InvalidTicket):
        count_statuses([row])


def test_count_statuses_accepts_empty_input() -> None:
    assert count_statuses([]) == {"open": 0, "closed": 0}
