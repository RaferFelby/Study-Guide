---
title: 第 3 讲：用子查询 CTE 与窗口函数排名
tags: [sql, cte, window-function]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 3 讲：用子查询 CTE 与窗口函数排名

> [!nav] 页面导航
> [[01_学习指南/17_SQL数据库与数据集成/00 SQL 数据库与数据集成学习地图#学习顺序|单元 17：SQL 数据库与数据集成]] · [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/02 用 JOIN 和 NULL 避免统计错账|上一讲]] · [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/04 理解事务索引与稳定分页|下一讲]]

## 要解决什么问题

找“高于本租户平均金额”的工单，需先算平均；找“每位用户最近一条”，全库LIMIT1不够。子查询、CTE和窗口函数把这些需求拆成明确步骤。

前置是WHERE/GROUP BY/ORDER BY/NULL。先会前两讲基础再学，不同时引入递归CTE或复杂帧窗口。

## 子查询把一个查询作为条件

```sql
SELECT external_id, amount_cents
FROM tickets
WHERE tenant_id = :tenant_id
  AND amount_cents > (
    SELECT AVG(amount_cents)
    FROM tickets
    WHERE tenant_id = :tenant_id
  )
ORDER BY amount_cents DESC, ticket_id;
```

括号中是子查询，返回当前租户平均2000；外层筛amount>2000，得T-004(4000)、T-006(3000)。内外都过滤tenant，不能把全公司平均拿给当前租户比较。

这表示逻辑关系，数据库实际执行/优化顺序由计划决定，不必说它一定每行重新跑平均。标量子查询应返回一个值；返回多行时不同数据库行为不同，不能依赖未定义选择。

## CTE为中间步骤命名

**CTE（公用表表达式）**用WITH给查询中的中间结果起名，便于分步阅读。它不是自动写入永久表，也不是一定缓存优化。

```sql
WITH averages AS (
  SELECT AVG(amount_cents) AS mean_cents
  FROM tickets
  WHERE tenant_id = :tenant_id
)
SELECT t.external_id, t.amount_cents
FROM tickets t, averages a
WHERE t.tenant_id = :tenant_id AND t.amount_cents > a.mean_cents;
```

averages只有一行，这里逗号FROM是交叉配对，每工单与同一平均值配对。为初学者尽量知道它的意义，不能把逗号连接随意用于两张多行表，否则产生行数乘积。可继续使用前面的子查询，CTE主要帮助组织长逻辑。

## 窗口函数保留每一行

GROUP BY把用户多条工单压成一行，难以同时保留最近工单全部字段。**窗口函数**对一组相关行计算排序/统计，但保留原行。ROW_NUMBER给组内顺序号。

```sql
WITH ranked AS (
  SELECT user_id, external_id,
    ROW_NUMBER() OVER (
      PARTITION BY user_id
      ORDER BY created_at DESC, ticket_id DESC
    ) AS position
  FROM tickets
  WHERE tenant_id = :tenant_id
)
SELECT user_id, external_id
FROM ranked
WHERE position = 1
ORDER BY user_id;
```

PARTITION BY user_id分各用户的窗口，ORDER BY决定组内先后，OVER说明在哪些行上计算。位置1就是每用户最近一条，结果Alice(T-005)、Bob(T-006)；Carol没有工单，所以不在ranked。若还要Carol，另外与users LEFT JOIN。

两个排序字段打破同时间平局。只按created_at，同时间可能任意选一个。ROW_NUMBER不同于RANK：每行唯一序号；RANK对并列可能同名次且跳号；本任务要一条，用ROW_NUMBER更明确。

## 完整窗口最小例子

在示例工程创建 `inspect_window.py`：

```python
import sqlite3

connection = sqlite3.connect(":memory:")
try:
    connection.execute("CREATE TABLE tickets(id INTEGER, owner TEXT)")
    connection.executemany("INSERT INTO tickets VALUES(?, ?)", [(1, "A"), (2, "A"), (3, "B")])
    sql = "SELECT id, owner, ROW_NUMBER() OVER(PARTITION BY owner ORDER BY id DESC) AS position FROM tickets ORDER BY owner, position"
    print(connection.execute(sql).fetchall())
finally:
    connection.close()
```

预期 `(2,A,1)、(1,A,2)、(3,B,1)`，行数仍3。窗口输出字段position不能在同层WHERE直接用，需要外层CTE/子查询筛。别在SQLite碰巧能运行的别名用法上建立跨库假设。

## 动手与常见错误

跑demo看above_average/latest_per_user；改个人最小例子的ORDER BY为升序，预测A中id1成为第一。窗口函数需要SQLite3.25+，共享版本满足，可用sqlite3.sqlite_version核对。

只写LIMIT1返回全库最新一条，不是每用户一条。把MAX(created_at)和external_id一起GROUP BY，可能得到不对应字段，不是稳妥方法。去掉租户过滤会将跨租户同user_id分组或泄露记录，先固定范围再排名。

## 练习与解析

**跟做：** 给三个最小行写partition/position，再执行核对。

**独立：** 每个产品金额最高一条，NULL忽略，同金额ticket_id较大优先，写窗口SQL。完成标准：分组与排序维度清楚。

**迁移：** 工单报表按每租户/每用户最近记录，设计同时间平局与无工单用户处理；不要默认同名用户是同一人。

> [!example]- 参考答案与解析
> 在当前租户且amount_cents IS NOT NULL的行上，`ROW_NUMBER() OVER(PARTITION BY product_id ORDER BY amount_cents DESC,ticket_id DESC)`，外层position=1。product_id NULL可形成一个“未指定产品”组，若不想显示要明确过滤，不偷偷忽略。窗口保留行，GROUP BY聚合压行，职责不同。

## 继续学习

> [!next] 下一步
> [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/04 理解事务索引与稳定分页|下一讲：理解事务索引与稳定分页]]

> [!info]- 练习与记录
> [[01_学习指南/17_SQL数据库与数据集成/示例工程/README#代码导航|查看源码]] · [[01_学习指南/17_SQL数据库与数据集成/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 17：SQL、数据库与数据集成|本单元完成清单]]
