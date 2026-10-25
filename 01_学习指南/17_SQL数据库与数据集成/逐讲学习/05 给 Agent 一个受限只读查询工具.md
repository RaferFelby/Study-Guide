---
title: 第 5 讲：给 Agent 一个受限只读查询工具
tags: [sql, read-only, parameterization]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 5 讲：给 Agent 一个受限只读查询工具

> [!nav] 页面导航
> [[01_学习指南/17_SQL数据库与数据集成/00 SQL 数据库与数据集成学习地图#学习顺序|单元 17：SQL 数据库与数据集成]] · [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/04 理解事务索引与稳定分页|上一讲]] · [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/06 完成增量导入与备份恢复|下一讲]]

## 要解决什么问题

Agent需要读业务表，但不应凭用户输入改变SQL结构、选择其他租户或发DELETE。本讲先用固定查询模板和参数，给它一个有限、可验证的只读工具。

没有“模型生成任意SQL”接口，所以不用在字符串开头找SELECT来假装防护。若以后支持生成SQL，需专门解析、只读账户、表/函数限制、隔离和攻击测试；当前不能把模板测试说成生成SQL安全验证。

## 参数化查询怎样防结构改变

```python
sql = "SELECT external_id FROM tickets WHERE tenant_id=? AND status=?"
parameters = ("alpha", "open' OR 1=1 --")
```

第二项作为普通状态值绑定，不被当OR/注释解释。该状态不存在，结果为空。不能用f-string把它拼进SQL。

占位符用于**值**，不能任意绑定表名或ORDER方向。动态列/排序必须从可信白名单映射；当前模板名也只来自QUERY_TASKS。bounded_sql拼接的是作者固定SQL而非用户输入，结构来源不同。

## 权限与只读分层

ReadOnlyService(path,tenant_id)中的租户由服务端可信上下文提供，query参数不允许tenant_id。所有模板显式过滤该范围，用户传beta会在字段集合校验拒绝。

连接使用文件URI `mode=ro`，打开已有数据库只读；PRAGMA query_only=ON进一步限制写；authorizer只允许SELECT/READ/FUNCTION/RECURSIVE，拒绝DELETE、ATTACH等操作。模板限制还避免任意函数/表由模型选择。

SQLite没有服务器账户/角色，这不是PostgreSQL只读账户实测。生产服务端应使用最小权限数据库角色、行级/租户访问设计和受控连接，不能让客户端自行创建ReadOnlyService(path,"beta")就得到授权。当前context是演示输入。

## 完整受限查询实验

在示例工程创建 `inspect_readonly.py`：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from database import connect_writer, initialize
from importing import import_rows, load_csv
from readonly import ReadOnlyService

with TemporaryDirectory(dir=Path(__file__).parent) as directory:
    path = Path(directory) / "example.db"
    writer = connect_writer(path)
    try:
        initialize(writer)
        import_rows(writer, load_csv(Path(__file__).parent / "fixtures/tickets.csv"))
        service = ReadOnlyService(path, "alpha", max_rows=2)
        print(service.query("status_filter", {"status": "open' OR 1=1 --"})["rows"])
        print(service.query("open_tickets"))
    finally:
        writer.close()
```

预期第一项[]；第二项两条alpha/open，truncated=True、row_limit=2。临时目录在当前工程下，由标准库只清理本次新目录；不会删除已有数据库。

## 限行不等于查询便宜

服务包一层SELECT LIMIT max_rows+1，用多取一条判断truncated，再只返回max_rows。这样结果内存有界，但聚合/排序/子查询可能先处理大量行，LIMIT不能替代耗时预算。

set_progress_handler每个SQLite虚拟机步骤检查deadline和max_vm_steps，超限中断并转QueryLimitError。**VM步骤**是数据库内部执行指令，不是SQL行数或Python行数。当前每步回调易观察但有开销，生产可调粒度并测试误差。

deadline从建立连接后计算，约束VM执行；锁等待、文件打开和Python处理可能另花时间，不是硬总请求时限。真实服务还需锁等待timeout、取消、队列与外层预算。只读也可能昂贵，不自动等于安全无成本。

## 工具回传如何组织

结果rows/truncated/row_limit应通过上一单元ToolResult外壳回给Agent；超限/未允许模板/参数错误分别映射稳定错误码，避免向模型抛数据库堆栈。当前服务直接抛Python异常，便于学习；接入单元15runtime时在边界转换，不能在底层静默吞掉。

长结果被截断时，Agent应说明只展示部分或请求下一页，不假称“总共只有两条”。总数若需要应另用固定计数模板，不从限行列表长度推断。

## 常见错误与练习

URI打不开：确认数据库已存在和Path.resolve路径正确，mode=ro不创建新库。租户泄漏：每个模板检查WHERE/ON和子查询范围。只读失败仍显示成功：工具边界需要结构错误，不伪造空rows。SELECT字符串检查可绕过：当前不接受模型SQL，未来必须专门设计。

**跟做：** 运行注入/截断例子，解释为什么不是3条全显示。

**独立：** 将max_vm_steps设1，捕获QueryLimitError并给出用户说明；不要删除预算让测试“通过”。

**迁移：** 给Agent设计三个模板：按用户查工单、统计状态、分页；参数里不能有租户或任意SQL。完成标准：权限来自可信上下文、行数/时间边界明确，失败可被重规划。

> [!example]- 参考答案与解析
> 超限可说明“查询超过本次执行预算，未得到完整结果”，建议缩小范围/使用已有摘要，不自动无限重试。值绑定使恶意状态当文本，仍要最小权限与模板。COUNT模板统计当前租户全量，与被截断列表长度不同。

## 继续学习

> [!next] 下一步
> [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/06 完成增量导入与备份恢复|下一讲：完成增量导入与备份恢复]]

> [!info]- 练习与记录
> [[01_学习指南/17_SQL数据库与数据集成/示例工程/README#代码导航|查看源码]] · [[01_学习指南/17_SQL数据库与数据集成/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 17：SQL、数据库与数据集成|本单元完成清单]]
