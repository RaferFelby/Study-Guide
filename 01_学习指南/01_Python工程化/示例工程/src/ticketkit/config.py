"""Validate external configuration once, at the application boundary."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


class ConfigError(ValueError):
    """Configuration is present but invalid."""


@dataclass(frozen=True, slots=True)
class Config:
    attempts: int = 3
    # repr=False prevents accidental disclosure through repr(config).
    # It does NOT protect deliberate printing or dataclasses.asdict().
    api_token: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Config":
        values = os.environ if env is None else env
        try:
            attempts = int(values.get("TICKETKIT_ATTEMPTS", "3"))
        except ValueError as error:
            raise ConfigError("TICKETKIT_ATTEMPTS must be an integer") from error
        if attempts < 1:
            raise ConfigError("TICKETKIT_ATTEMPTS must be at least 1")
        token = values.get("TICKETKIT_API_TOKEN") or None
        return cls(attempts=attempts, api_token=token)
