"""固定模板+只读文件连接+授权回调+限行/VM预算；无生成SQL接口。"""

import sqlite3
from pathlib import Path
from time import monotonic

from queries import QUERY_TASKS


class QueryLimitError(RuntimeError):
    pass


def authorize_read(action, argument1, argument2, database_name, trigger_name):
    allowed = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_RECURSIVE,
    }
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


class ReadOnlyService:
    def __init__(
        self,
        path: Path,
        tenant_id: str,
        max_rows: int = 3,
        timeout_seconds: float = 0.1,
        max_vm_steps: int = 10000,
    ):
        if max_rows < 1 or timeout_seconds <= 0 or max_vm_steps < 1:
            raise ValueError("查询行数、时间和VM预算必须大于0")
        if not tenant_id.strip():
            raise ValueError("租户上下文不能为空")
        self.path = path
        self.tenant_id = tenant_id
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.max_vm_steps = max_vm_steps

    def query(self, name: str, arguments: dict | None = None) -> dict:
        if name not in QUERY_TASKS:
            raise ValueError("未允许的查询模板")
        _, sql, required = QUERY_TASKS[name]
        arguments = arguments or {}
        if set(arguments) != required:
            raise ValueError("查询参数不符合模板；租户由服务端提供")
        for key in ["user_id", "after_id"]:
            if key in arguments and (
                type(arguments[key]) is not int or arguments[key] < 0
            ):
                raise ValueError("用户/游标必须为非负整数")
        if "status" in arguments and not isinstance(arguments["status"], str):
            raise TypeError("status必须为字符串")
        return self._execute(sql, {**arguments, "tenant_id": self.tenant_id})

    def _execute(self, sql: str, parameters: dict) -> dict:
        connection = sqlite3.connect(
            self.path.resolve().as_uri() + "?mode=ro", uri=True
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.set_authorizer(authorize_read)
        deadline = monotonic() + self.timeout_seconds
        vm_steps = 0

        def stop_if_over_budget():
            nonlocal vm_steps
            vm_steps += 1
            return int(vm_steps >= self.max_vm_steps or monotonic() >= deadline)

        connection.set_progress_handler(stop_if_over_budget, 1)
        try:
            bounded_sql = "SELECT * FROM (" + sql + ") LIMIT :row_budget"
            cursor = connection.execute(
                bounded_sql, {**parameters, "row_budget": self.max_rows + 1}
            )
            rows = cursor.fetchmany(self.max_rows + 1)
            return {
                "rows": [dict(row) for row in rows[: self.max_rows]],
                "truncated": len(rows) > self.max_rows,
                "row_limit": self.max_rows,
            }
        except sqlite3.OperationalError as error:
            if "interrupted" in str(error):
                raise QueryLimitError("查询超过时间/VM步数预算") from error
            raise
        finally:
            connection.close()
