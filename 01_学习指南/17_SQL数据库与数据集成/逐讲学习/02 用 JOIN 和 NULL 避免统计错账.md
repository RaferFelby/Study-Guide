---
title: 第 2 讲：用 JOIN 和 NULL 避免统计错账
tags: [sql, join, null]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：用 JOIN 和 NULL 避免统计错账

> [!nav] 页面导航
> [[01_学习指南/17_SQL数据库与数据集成/00 SQL 数据库与数据集成学习地图#学习顺序|单元 17：SQL 数据库与数据集成]] · [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/01 建立关系表并查询工单|上一讲]] · [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/03 用子查询 CTE 与窗口函数排名|下一讲]]

## 要解决什么问题

工单只存product_id，要显示产品名需要连接产品表；一张工单有多条事件，连接后“工单数”可能突然增加；有些金额/产品未填写，NULL又影响统计。本讲用小表手算再运行，避免图表看似合理却数错。

**JOIN（连接）**按条件把两表行配对。**INNER JOIN**只保留匹配，**LEFT JOIN**保留左表全部行，右边无匹配时填NULL。NULL表示未知/缺少，不是0或空字符串。

## 一张工单为什么变两行

ticket1有opened/comment两个事件，ticket2有opened一个事件。连接结果：

| 工单 | 事件 |
|---|---|
| 1 | opened |
| 1 | comment |
| 2 | opened |

三行代表三次匹配，不是三个不同工单。COUNT(t.ticket_id)=3，COUNT(DISTINCT t.ticket_id)=2。DISTINCT去除重复值，只用于“不同工单数”；若求金额，SUM(DISTINCT amount)会把不同工单的相同金额错误合并，不能乱用它修JOIN重复。

工程demo打印 `(3,2)`。需要同时统计工单金额和事件数时，可先各表按工单聚合再连接，或分别计算，避免工单金额按事件复制。

## LEFT JOIN与过滤位置

```sql
SELECT p.name, COUNT(t.ticket_id) AS ticket_count
FROM products p
LEFT JOIN tickets t
  ON t.product_id = p.product_id AND t.tenant_id = :tenant_id
GROUP BY p.product_id
ORDER BY p.product_id;
```

p/t是表别名，让字段来源清楚；AS给结果列起名字。左边产品全保留，alpha产品工单数Storage3、Compute2、Analytics0。COUNT(t.ticket_id)忽略无匹配NULL；COUNT(*)会把那条左保留行计为1。

如果把`t.tenant_id=:tenant_id`移到WHERE，NULL行无法满足，Analytics可能消失。连接条件与连接后过滤职责不同，不要只根据“SQL更短”调整位置。

找无工单用户用LEFT JOIN后 `t.ticket_id IS NULL`，得到Carol。INNER JOIN找不到她，这是预期不同，不是数据丢了。

## NULL要用IS NULL

`amount_cents = NULL`不会像普通等号那样选中缺值；用IS NULL。NULL参与普通比较通常得到未知，WHERE仅保留真。`amount_cents > 0`也不会选NULL或0。

AVG(amount_cents)忽略NULL；COUNT(amount_cents)数非空；COUNT(*)数所有行。alpha金额1000、2000、NULL、4000、0、3000：已知总10000，5项平均2000；若把NULL当0，变6项平均约1666.67，含义不同。

0是明确填写零，不能与缺失混淆。COALESCE可给NULL替代值，但应由业务含义决定；不能为了“没有空格”把未知统一改0。

## 最小完整NULL实验

在示例工程创建 `inspect_null.py`：

```python
import sqlite3

connection = sqlite3.connect(":memory:")
try:
    connection.execute("CREATE TABLE amounts(value INTEGER)")
    connection.executemany("INSERT INTO amounts VALUES(?)", [(10,), (0,), (None,)])
    print(connection.execute("SELECT COUNT(*), COUNT(value), AVG(value) FROM amounts").fetchone())
    print(connection.execute("SELECT value FROM amounts WHERE value IS NULL").fetchall())
finally:
    connection.close()
```

预期 `(3,2,5.0)` 和 `[(None,)]`。Python None绑定到SQL NULL；返回时又变None。改成`value=NULL`预期空列表；通过反例理解三值逻辑，不要背一句“NULL不能等号”就结束。

## 分组与业务统计

GROUP BY按字段聚合；同一SELECT里非聚合字段应表达明确分组，否则某些数据库会拒绝，SQLite的宽松行为也可能挑任意值。当前按产品主键分组、名称是该产品固定属性，关系明确；复杂报表尽量列齐分组维度。

解决率用SUM(CASE WHEN status='resolved' THEN 1 ELSE 0 END)/COUNT(*)。CASE是SQL条件表达式；CAST AS REAL避免整数除法；NULLIF分母0时转NULL。空租户解决率未知，不能硬说0%或100%。

## 常见错误与练习

连接后金额翻倍：先看每个ID匹配多少行。零匹配变1：用了COUNT(*)数LEFT保留行。NULL平均不同：确认分母与业务含义。beta混入：关联条件和主查询均检查租户，不能只过滤最终显示。

**跟做：** 手算事件三行，再跑demo对照3/2。

**独立：** ticket1/2金额都1000，各有2/1事件，计算错误SUM、正确SUM和SUM(DISTINCT amount)，说明最后一种为何也错。

**迁移：** 设计“每用户工单数/事件数/金额”报表，先聚合事件再连接，并包含无工单用户。完成标准：每个业务实体只计一次，NULL和0含义明确。

> [!example]- 参考答案与解析
> 连接后SUM=3000，正确两工单SUM=2000，SUM(DISTINCT amount)=1000，误把两条相同金额去重。应该按工单ID明确聚合/连接粒度，而不是对金额去重。NULL题当前平均2000，非空样本5，所有工单6。

## 继续学习

> [!next] 下一步
> [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/03 用子查询 CTE 与窗口函数排名|下一讲：用子查询 CTE 与窗口函数排名]]

> [!info]- 练习与记录
> [[01_学习指南/17_SQL数据库与数据集成/示例工程/README#代码导航|查看源码]] · [[01_学习指南/17_SQL数据库与数据集成/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 17：SQL、数据库与数据集成|本单元完成清单]]
