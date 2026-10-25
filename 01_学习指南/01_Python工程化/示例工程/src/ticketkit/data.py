"""Lazy input with runtime validation; no full-dataset materialization."""

import json
from collections.abc import Generator, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class DataError(ValueError):
    """A record cannot be interpreted as a valid ticket."""


@dataclass(frozen=True, slots=True)
class Ticket:
    ticket_id: str
    status: Literal["open", "closed"]


def parse_ticket(value: object) -> Ticket:
    if not isinstance(value, dict):
        raise DataError("ticket must be an object")
    ticket_id: object = value.get("ticket_id")
    status: object = value.get("status")
    if not isinstance(ticket_id, str) or not ticket_id.strip():
        raise DataError("ticket_id must be a non-empty string")
    if status == "open":
        return Ticket(ticket_id, "open")
    if status == "closed":
        return Ticket(ticket_id, "closed")
    raise DataError("status must be open or closed")


def read_tickets(path: Path) -> Generator[Ticket, None, None]:
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                value: object = json.loads(line)
                yield parse_ticket(value)
            except (json.JSONDecodeError, DataError) as error:
                # Do not embed the entire record in logs or exception messages.
                raise DataError(f"invalid ticket at line {line_number}") from error


def generated_tickets(count: int) -> Iterator[Ticket]:
    if count < 0:
        raise ValueError("count must be non-negative")
    for index in range(count):
        yield Ticket(f"T{index:06d}", "open" if index % 2 == 0 else "closed")


def summarize(tickets: Iterable[Ticket]) -> dict[str, int]:
    totals = {"open": 0, "closed": 0}
    for ticket in tickets:
        totals[ticket.status] += 1
    return totals
