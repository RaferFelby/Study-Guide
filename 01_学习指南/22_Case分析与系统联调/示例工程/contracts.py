from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    use_aliases: bool = False
    correct_argument_name: bool = False
    accept_json_fence: bool = False
    enforce_owner: bool = False
    max_attempts: int = 1

    def __post_init__(self):
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 2:
            raise ValueError("教学只读重试限定1或2次")


class ToolContractError(ValueError):
    pass


class AccessDeniedError(PermissionError):
    pass
