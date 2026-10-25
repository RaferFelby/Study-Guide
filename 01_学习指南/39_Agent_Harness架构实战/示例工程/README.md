---
title: Agent Harness 示例工程导航
tags: [code, harness]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# Agent Harness 示例工程导航

> [!nav] 页面导航
> [[01_学习指南/39_Agent_Harness架构实战/00 Agent Harness架构实战学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/39_Agent_Harness架构实战/逐讲学习/01 把模型工具状态连接成完整系统|从第一讲开始：把模型工具状态连接成完整系统]]

## 从哪里运行

VS Code 打开本目录，使用工作区共享 `.venv`。标准库即可，无需安装包。学习入口见 [[01_学习指南/39_Agent_Harness架构实战/00 Agent Harness架构实战学习地图|单元 39：Agent Harness架构实战]]。

```powershell
..\..\..\.venv\Scripts\python.exe demo.py start --db results/first.db
..\..\..\.venv\Scripts\python.exe demo.py step --db results/first.db
..\..\..\.venv\Scripts\python.exe demo.py step --db results/first.db
..\..\..\.venv\Scripts\python.exe demo.py show --db results/first.db
```

此时等待确认；按第 3 讲阅读待保存文字后提供 `--approve`。再 step 得最终回答。新会话拒绝覆盖；取消用 `cancel`；`--crash-after-tool` 故意在本地事务提交后抛异常。只保存虚构学习笔记，没有外部业务写入。

## 代码导航

- [contracts.py](./contracts.py)：目标、动作约定、SHA256、上下文、固定句式解析与分项验收。
- [backends.py](./backends.py)：规则与可选本地 Ollama JSON 后端。
- [storage.py](./storage.py)：SQLite 状态、事件与笔记事务。
- [runtime.py](./runtime.py)：预算、动作校验、确认、提交、恢复与终止。
- [demo.py](./demo.py)：逐步命令入口。
- [delegation.py](./delegation.py)：确定性研究／检查角色交接，不是多个模型。
- [quality_examples.py](./quality_examples.py)：七个内存案例，分开观察执行、答案与笔记质量。
- [evaluate.py](./evaluate.py)：读取实际笔记，只读复核新旧会话，不改写历史。
- [contrast_lab.py](./contrast_lab.py)：四套手工配置的费用计算对照、处理轨迹与已知答案检查，不调用模型。
- [experience_transfer.py](./experience_transfer.py)：人工经验卡的时间、状态、版本与单位范围检查，保留当前预算后进行新任务试跑。
- [experience_store.py](./experience_store.py)：独立 SQLite 经验文件、追加创建／撤回与任务开始前的只读快照。
- [test_experience_store.py](./tests/test_experience_store.py)：严格时点、禁止回填、事务回滚、只读、历史撤回和试跑衔接。
- [test_harness.py](./tests/test_harness.py)：正常、失败、批准、恢复与预算测试。
- [test_quality.py](./tests/test_quality.py)：错误数字、否定、来源、缺失与不一致证据的检查。
- [test_contrast_lab.py](./tests/test_contrast_lab.py)：对照算术、漏项、配置退步、输入边界和报告拒绝覆盖。
- [test_experience_transfer.py](./tests/test_experience_transfer.py)：经验范围、未来与自身排除、撤回、预算保持、候选独立于评价答案和迁移失败。

## 结果核验

第 6 讲后完成 [[01_学习指南/39_Agent_Harness架构实战/逐讲学习/07 分开检查执行完成与答案正确|结果核验详细课]]。在本目录运行：

```powershell
..\..\..\.venv\Scripts\python.exe quality_examples.py
..\..\..\.venv\Scripts\python.exe evaluate.py --db results/first.db
```

第一条只用内存夹具；第二条需先完成自己的会话。笔记与答案采用固定句式 `30 天内申请退款 [policy-v1]`；字段合法不等于任务正确。新终态报告在 `state.evaluation`，会核对实际数据库行与动作摘要。相同意思的自由改写可能不能通过此格式；这不是通用语义评委。

原动作 JSON、命令与数据库表结构保留，旧终态不会重跑或改写。旧会话可用 `evaluate.py` 复核，原 `completed` 只代表当时规则。`verify_final` 保留布尔入口，但现在须提供来自数据库的 `notes` 证据才能通过；省略证据返回 False。正式运行由 `runtime.py` 调用详细评估函数。

## 保存经验并重建历史

完成迁移练习后，按 [[01_学习指南/39_Agent_Harness架构实战/选修专题/06 保存经验并按历史时点读取|持久化补充课]]执行 init、add、snapshot、revoke。示例入口为 `..\..\..\.venv\Scripts\python.exe experience_store.py --db results/experience-first.db init`；`--db` 在子命令前。经验库与退款会话库分开，已有路径拒绝覆盖。

只读快照按任务序号重建，保留撤回前的历史；它不证明人工声明的时点或证据真实，也没有自动反思、语义检索和生产审计。

## 检查与限制

完成对照后继续 [[01_学习指南/39_Agent_Harness架构实战/选修专题/05 检查经验范围并在新任务上试跑|经验迁移练习]]。在本目录运行 `..\..\..\.venv\Scripts\python.exe experience_transfer.py`，加 `--output results/transfer-first.json` 保存七个独立情景的报告。它使用人工卡片与固定规则，不读取旧报告、自动反思或建立持久经验库。预算练习脚本按正文创建，与源码平级。

论文专题后可完成 [[01_学习指南/39_Agent_Harness架构实战/选修专题/04 用本地对照实验检查配置修改|本地配置对照实验]]。在本目录运行 `..\..\..\.venv\Scripts\python.exe contrast_lab.py` 查看四套配置；加 `--output results/contrast-first.json` 保存输入、配置、轨迹和检查结果，已有同名文件拒绝覆盖。实验使用手工候选与已知答案，不实现自动改进；正文的零费用与未知单位练习由学习者创建独立脚本。

Harness² 论文专题的两个练习文件由你按正文在本目录创建：`lesson_harness2_budget.py` 计算执行次数，`lesson_harness2_scores.py` 核对读表算术。完整最小代码分别见 [[01_学习指南/39_Agent_Harness架构实战/选修专题/02 跟着对照试跑理解配置改进流程|预算练习]]与 [[01_学习指南/39_Agent_Harness架构实战/选修专题/03 核对Harness平方的实验与应用边界|分数练习]]。它们只需标准库；现有 `runtime.py` 未实现论文的递归配置搜索，原测试也不构成论文复现。

```powershell
..\..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

tests 在 `results/test-*` 创建唯一数据库或对照报告并保留排错证据，默认不会删除历史。每个数据库只允许单操作者；本课没有认证、签名、多租户、分布式锁或 OS 沙箱。只读自己可信的数据库。真实模型教程不要求运行，详见第 2 讲；实际作者范围见 [[90_参考与维护/单元验证/39 Agent_Harness架构实战验证记录|验证记录]]。
