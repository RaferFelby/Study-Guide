"""受限查询模板；tenant_id只来自服务端上下文，模型不提供任意SQL。"""

QUERY_TASKS = {
    "open_tickets": (
        "当前租户有哪些未解决工单？",
        """SELECT external_id,status,created_at
FROM tickets
WHERE tenant_id=:tenant_id AND status='open'
ORDER BY created_at DESC,ticket_id DESC""",
        set(),
    ),
    "user_tickets": (
        "指定用户有哪些工单？",
        """SELECT t.external_id,p.name AS product,t.status
FROM tickets t
LEFT JOIN products p ON p.product_id=t.product_id
WHERE t.tenant_id=:tenant_id AND t.user_id=:user_id
ORDER BY t.ticket_id""",
        {"user_id"},
    ),
    "status_counts": (
        "每种状态有多少工单？",
        """SELECT status,COUNT(*) AS ticket_count
FROM tickets
WHERE tenant_id=:tenant_id
GROUP BY status
ORDER BY status""",
        set(),
    ),
    "product_counts": (
        "每个产品有多少工单，包含零工单产品？",
        """SELECT p.name,COUNT(t.ticket_id) AS ticket_count
FROM products p
LEFT JOIN tickets t ON t.product_id=p.product_id AND t.tenant_id=:tenant_id
GROUP BY p.product_id
ORDER BY p.product_id""",
        set(),
    ),
    "users_without_tickets": (
        "哪些用户没有工单？",
        """SELECT u.name
FROM users u
LEFT JOIN tickets t ON t.user_id=u.user_id AND t.tenant_id=u.tenant_id
WHERE u.tenant_id=:tenant_id AND t.ticket_id IS NULL
ORDER BY u.user_id""",
        set(),
    ),
    "average_amount": (
        "已填写金额的平均值和样本数？",
        """SELECT AVG(amount_cents) AS average_cents,COUNT(amount_cents) AS known_amounts,COUNT(*) AS tickets
FROM tickets
WHERE tenant_id=:tenant_id""",
        set(),
    ),
    "missing_amount": (
        "哪些工单未填写金额？",
        """SELECT external_id
FROM tickets
WHERE tenant_id=:tenant_id AND amount_cents IS NULL
ORDER BY ticket_id""",
        set(),
    ),
    "resolution_rate": (
        "解决率是多少？",
        """SELECT CAST(SUM(CASE WHEN status='resolved' THEN 1 ELSE 0 END) AS REAL)/NULLIF(COUNT(*),0) AS resolution_rate
FROM tickets
WHERE tenant_id=:tenant_id""",
        set(),
    ),
    "latest_per_user": (
        "每位有工单用户的最近一条？",
        """WITH ranked AS (SELECT user_id,external_id,ROW_NUMBER() OVER(PARTITION BY user_id
ORDER BY created_at DESC,ticket_id DESC) AS position
FROM tickets
WHERE tenant_id=:tenant_id)
SELECT user_id,external_id
FROM ranked
WHERE position=1
ORDER BY user_id""",
        set(),
    ),
    "above_average": (
        "哪些工单金额高于本租户平均？",
        """SELECT external_id,amount_cents
FROM tickets
WHERE tenant_id=:tenant_id AND amount_cents>(SELECT AVG(amount_cents)
FROM tickets
WHERE tenant_id=:tenant_id)
ORDER BY amount_cents DESC,ticket_id""",
        set(),
    ),
    "status_filter": (
        "按给定状态筛选（参数注入实验）",
        """SELECT external_id,status
FROM tickets
WHERE tenant_id=:tenant_id AND status=:status
ORDER BY ticket_id""",
        {"status"},
    ),
    "keyset_page": (
        "按工单ID读取下一页",
        """SELECT ticket_id,external_id
FROM tickets
WHERE tenant_id=:tenant_id AND ticket_id>:after_id
ORDER BY ticket_id""",
        {"after_id"},
    ),
}
