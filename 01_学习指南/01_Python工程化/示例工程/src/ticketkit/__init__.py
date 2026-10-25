"""Public interface for the learning package. Importing does not run the demo."""

from .config import Config
from .data import Ticket, generated_tickets, read_tickets
from .resilience import TransientError, retry, timed

__all__ = [
    "Config",
    "Ticket",
    "TransientError",
    "generated_tickets",
    "read_tickets",
    "retry",
    "timed",
]
