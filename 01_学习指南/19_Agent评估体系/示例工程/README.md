---
title: 单元 19 示例工程导航
tags: [code, evaluation, agent]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 19 示例工程

> [!nav] 页面导航
> [[01_学习指南/19_Agent评估体系/00 Agent 评估体系学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/19_Agent评估体系/逐讲学习/01 把用户需求变成可判定任务|从第一讲开始：把用户需求变成可判定任务]]

60条固定合成任务：10服务×6场景，按服务分dev/test各30。规则baseline/guarded对照、分层与适用分母、配对回归/分组bootstrap、模拟成本、示例裁判一致性；无真实LLM/外部调用。

## 运行

本目录VS Code终端使用根共享环境：

```powershell
..\..\..\.venv\Scripts\python.exe evaluate.py --split test --output report-test-01.json
..\..\..\.venv\Scripts\python.exe judging.py
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

报告不覆盖已有文件；换新文件名。预期任务10/30→30/30，安全20/30→30/30；答案/检索10/10，两版本均1；调用35→20，模拟单位165→120；无退步。judging示例6/8一致、kappa0.5、争议下标1/6，非真实人工/模型评分。

## 代码导航

- [cases.json](./fixtures/cases.json)：固定60条、gold/轨迹契约、待人工审核属性。
- [dataset.py](./dataset.py)：构造/检查；已有数据拒绝重生成覆盖。
- [agents.py](./agents.py)：只读input的规则系统，模拟越权/超时/冲突行为。
- [metrics.py](./metrics.py)：各层指标、None分母、配对分组bootstrap、一致率/Kappa。
- [evaluate.py](./evaluate.py)：SHA、场景报告、逐题变化/退步、成本/门槛。
- [judging.py](./judging.py)：示例标签一致性与位置偏好检测逻辑。
- [test_evaluation.py](./tests/test_evaluation.py)：数据切分、场景契约、安全反例、分母/配对/裁判边界。
- [requirements.txt](./requirements.txt)：标准库运行，测试工具沿用共享环境。

## 限制

合成模板单一，仅五test组；不是50～100条真实高质量业务集。未人工独立标注、未调用真实LLM/裁判、未测自然语言逐句忠实度或真实费用。规划指标用终态代理；轨迹/越权是模拟，没有外部写。bootstrap整齐退化不是泛化确定性证明。门槛是教学项目选择，不代表生产部署审批。

[[01_学习指南/19_Agent评估体系/00 Agent 评估体系学习地图|返回地图]]。
