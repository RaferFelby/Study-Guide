from contracts import AccessDeniedError, ToolContractError

ACCOUNT_DAYS = {"alice": 30, "bob": 50}


class AccountTool:
    def __init__(self, transient_failures=0):
        self.failures_remaining = transient_failures
        self.attempts = 0
        self.reads = 0

    def query(self, arguments, actor, enforce_owner):
        self.attempts += 1
        if set(arguments) != {"owner"} or arguments["owner"] not in ACCOUNT_DAYS:
            raise ToolContractError("工具只接受已知owner字段")
        if enforce_owner and arguments["owner"] != actor:
            raise AccessDeniedError("目标账户不属于当前用户")
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise TimeoutError("合成只读上游暂时失败")
        self.reads += 1
        return {"owner": arguments["owner"], "days": ACCOUNT_DAYS[arguments["owner"]]}
