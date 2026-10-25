"""规划机制详细教材；真实模型策略对照与确定性回放明确分开。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/29_规划工作流与重新规划"
MAP = "00 规划工作流与重新规划学习地图"
LESSONS = [
    "01 把业务目标拆成有输入输出的步骤",
    "02 用DAG依赖安排并行与执行顺序",
    "03 保存检查点并从已完成步骤继续",
    "04 根据失败反馈有限修复计划",
    "05 对照固定流程串行观察与先规划策略",
    "06 在发布前暂停并完成规划验收",
]


def write(name, body, title=None):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {title or path.stem}\ntags: [learning, planning, workflow]\nupdated: 2026-10-12\n---\n\n# {title or path.stem}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(index, body):
    previous = (
        f"[[{LESSONS[index - 1]}|上一讲]]"
        if index
        else "[[../../28_记忆与上下文管理/00 记忆与上下文管理学习地图|前一单元]]"
    )
    following = (
        f"[[{LESSONS[index + 1]}|下一讲]]" if index < 5 else f"[[../{MAP}|返回地图]]"
    )
    write(
        f"逐讲学习/{LESSONS[index]}.md",
        f"[[../{MAP}|单元地图]] · {previous} · {following}\n\n" + body,
    )


if __name__ == "__main__":
    lesson(
        0,
        r"""
## 本讲要解决的问题与前置

“整理退款咨询说明”需要资料、工单、草稿和检查；发布还需明确确认。本讲把一句目标变成可检查步骤。前置：Python列表/字典/函数、[[../../14_Agent运行原理与状态机/00 Agent 运行原理与状态机学习地图|状态与结束]]、[[../../15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|工具输入输出]]。不熟先返回对应详细课次。

快速顺序：明确验收 → 看四步输入输出 → 运行计划 → 看执行边界。本例标准库、合成工具，没有LLM、外部发送或通用自主规划。

## 概念与直觉：目标不是步骤列表

目标描述成功条件：根据当前模拟政策和合成工单形成带两个来源的说明，经过固定检查。plan是结构化步骤及依赖；每个节点有id（身份）、tool（允许函数）、needs（依赖ID）、approval（确认门）。计划存在不等于任务已完成。

像菜谱先准备材料再烹饪，但实际还要检查来源、有效期和权限。政策过期或工单非法时，即使按列表走完也不能说验收成功；类比不能替代输入校验。

## 最小示例与操作

VS Code打开本单元示例工程，选择根共享.venv，新建lesson_01.py：

```python
from workflow import make_plan

plan = make_plan()
for node in plan:
    print(node["id"], "工具：", node["tool"], "依赖：", node["needs"])
```

工程终端运行 `& ..\..\..\.venv\Scripts\python.exe lesson_01.py`。三个..回工作区根，共享解释器不新建环境。预期policy/ticket依赖[]，draft依赖policy/ticket，review依赖draft。

## 逐步讲解：每步解决什么

make_plan只返回字典列表，不调用工具。load_policy返回kind/source/text/is_current；load_ticket返回kind/source/text；draft_note使用两者生成草稿及两来源；review_note检查来源数量和当前标记。TOOLS白名单限制名称，资料中的文字不会变成新函数。

检查器是固定规则，不是模型事实核验或真人审核。is_current来自合成场景，不表示真实政策有效。发布默认不在普通说明任务中；需要任务明确要求、检查通过和确认门，不能在“写草稿”函数里悄悄发出去。

现在必须掌握步骤输入输出、依赖和停止条件；模型动态生成计划留后续接入，当前固定数据方便理解机制。阅读workflow.py的make_plan与execute_tool，对照每个tool名称。

## 动手与常见错误

写一张四行表：每步输入、输出、可能错误。政策不可用/过期，工单非法，草稿缺来源，检查失败都要有停止路径。找不到模块时确认脚本在本工程，不把不同单元的同名模块放进全局导入路径。

### 跟做：解释无依赖步骤

完成标准是指出policy/ticket并说出来源相互独立。

> [!example]- 参考答案与解析
> 两个读取可先准备；draft要等两者，review要等draft。无依赖不代表无权限或无错误校验。

### 独立：发布依赖

发布只依赖draft够不够？

> [!example]- 参考答案与解析
> 不够，还需要review通过与确认门。本工程publish.needs为draft/review，缺检查依赖会拒绝。草稿存在并不意味着可发布。

### 迁移：报销流程

写读取票据、查询政策、生成单、审核、提交的关系。

> [!example]- 参考答案与解析
> 票据/政策独立读取，单依赖两者，审核依赖单与规则，提交依赖审核及授权。费用/账户/票据合法性由业务系统校验，不用模型计划当凭证。
""",
    )

if __name__ == "__main__":
    lesson(
        1,
        r"""
## 本讲要解决的问题与前置

依赖决定顺序，无依赖步骤可以并行。本讲运行DAG并拒绝环。前置上讲节点字段、[[../../16_并行工具异常处理与可靠性/00 并行工具与可靠性学习地图|并行与异常]]。

## DAG、就绪节点与图

DAG是有向无环图：箭头表示结果依赖，不可绕回自身。A等B、B等A时谁也无法开始，执行前就应拒绝。每轮找未完成且needs全在completed中的节点，叫就绪节点；本例最多同时执行2个。

```mermaid
flowchart LR
    P[读取政策] --> D[写草稿]
    T[读取工单] --> D
    D --> R[检查草稿]
```

如果当前阅读器不显示图，也可按“policy/ticket→draft→review”理解。图描述依赖，不代表网络或GPU结构。

## 最小示例与操作

工程新建lesson_02.py：

```python
from demo import load_scenarios
from workflow import run_workflow

scenario = load_scenarios()[0]
state = run_workflow("plan_execute", scenario)
for event in state["trace"]:
    if event["event"] == "dispatch":
        print("本轮节点：", event["nodes"])
print(state["status"], state["attempts"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_02.py`，预期[policy,ticket]、[draft]、[review]，completed/4。只是该固定合成任务完成，不能写成真实业务交付。

## 逐步讲解

validate_plan核对字段、ID唯一、工具白名单、依赖存在和发布门，再计算依赖可达集合；不能完成所有节点就报环。`set(needs) <= completed_ids`表示依赖集合的每个元素都具备，不是比较数字大小。

ThreadPoolExecutor(max_workers=2)设线程上限，submit提交函数，as_completed按实际完成次序取结果。结果顺序可能变，应按节点ID使用，不将第一个结果硬当政策。主线程写状态，工作线程只拿依赖副本。

作者测试让两个读取工具在Barrier汇合；如果串行，第一个等不到第二个就超时。Barrier是等待指定线程数量都到达的同步点，仅测试并行，不是业务函数必要步骤。当前工具很小，没有真实上游网络，不用这个演示声称加速比例。

## 动手：构造环再恢复

复制make_plan结果，把policy.needs改[review]，validate_plan应拒绝；恢复后成功。再把draft依赖改missing，应拒绝不存在ID。不能删依赖绕过问题，因为会改变业务语义。

常见错误：草稿提前运行读不到资料；无环验证遗漏导致等待；用列表位置当身份；线程无限开；吞掉失败继续拼接空结果。真实工具还需资源/时间界限，线程取消不能强杀不可中断调用，复习单元16。

### 跟做：解释三轮

完成标准是2个并行读取、1个草稿、1个检查。

> [!example]- 参考答案与解析
> width只是上限，后两轮各只有一个就绪节点，不为凑并行运行依赖没满足的步骤。

### 独立：环为何没有开始点

用policy→review→draft→policy说明。

> [!example]- 参考答案与解析
> 三者各等另一未完成结果，即使ticket独立完成，剩余也无法启动。必须修正设计，不在运行时无限重试。

### 迁移：两个工具改同一订单

输入独立就能并行吗？

> [!example]- 参考答案与解析
> 还可能副作用冲突，需要事务/幂等/资源依赖。图要反映业务约束，不只看函数参数。
""",
    )

if __name__ == "__main__":
    lesson(
        2,
        r"""
## 本讲要解决的问题与前置

重启后不想重做已完成步骤，但也不能忘预算和来源。本讲保存可信检查点再恢复。前置DAG、completed/errors与文件读写；读save_checkpoint/load_checkpoint。

## 检查点的内容与限制

保存当前plan、completed成果、errors、attempts、replans、trace、策略、场景摘要、schema版本和预算。仅存“下一步发布”不足以证明草稿、检查和依据一致。

JSON不执行代码，但不明文件仍可能伪造业务状态；这里只加载本工程可信生成文件，没有防篡改签名或认证。SHA摘要检测场景内容变化，不证明来源合法。恢复需相同代码/场景/预算，不能通过重启自动增加调用次数。

## 最小示例：暂停后继续一个模拟步骤

工程新建lesson_03.py：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from demo import load_scenarios
from workflow import run_workflow, load_checkpoint

scenario = load_scenarios()[-1]
with TemporaryDirectory(dir=Path.cwd()) as folder:
    path = Path(folder) / "state.json"
    waiting = run_workflow("plan_execute", scenario, checkpoint_path=path)
    restored = load_checkpoint(path, "plan_execute", scenario)
    resumed = run_workflow("plan_execute", scenario, state=restored,
                           checkpoint_path=path, simulated_approval=True)
    print(waiting["status"], waiting["attempts"])
    print(resumed["status"], resumed["attempts"])
    print(resumed["completed"]["publish"]["status"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_03.py`，预期awaiting_approval/4→completed/5，发布标记simulated_only_no_external_send。True是合成测试确认，不是真人批准，不触发外部写入。

## 逐步讲解

先完成四步，到发布门暂停；写同目录.next.json后replace成state.json，避免读半写文本。每个工具结果和终态更新都保存，路径属于示例自己拥有的临时目录，结束自动清理。

恢复按completed的ID跳过已完成步骤，仅新增publish。默认最多8次工具尝试、1次修复，这些是当前教学预算；恢复改20会拒绝，失败尝试也计数。状态不是随便重置0的计数器。

工具已执行但结果未落盘时崩溃，恢复可能重做。读取和内存草稿风险有限，真实发送/付款需外部幂等ID、事务或人工核查；检查点不自动保证“恰好一次”。长期任务还需重新确认来源时间/版本，不凭旧is_current永远有效。

## 动手与常见错误

把load策略改fixed，或场景policy改stale后加载旧文件，均应拒绝。恢复预算变20应拒绝。不要手改JSON冒充批准。不同工具版本也需重新验证已有成果，不把可读回当可安全续跑。

### 跟做：解释4→5

完成标准是原四步不重复，只多一个模拟publish。

> [!example]- 参考答案与解析
> completed按节点保存；本例没有真实副作用，只验证暂停/状态读取/继续机制。

### 独立：预算为什么保存

若每次恢复清零attempt，会怎样？

> [!example]- 参考答案与解析
> 可无限重启绕过上限。次数和修复预算必须和计划一起恢复，实际模型还要保留时间/token/费用预算。

### 迁移：消息已发但本地崩溃

如何决定再发？

> [!example]- 参考答案与解析
> 查询外部幂等请求ID的结果或人工核查，确认后更新状态；无法确认时暂停。仅凭本地未完成再发可能重复。
""",
    )

if __name__ == "__main__":
    lesson(
        3,
        r"""
## 本讲要解决的问题与前置

主资料失败时，继续等、盲目重试或改方案分别意味着什么？本讲有限修复计划。前置检查点和工具错误；读repair_plan与run_workflow的failed分支。

## 重试与重新规划

重试重复同一调用，适合暂时网络问题且有预算/幂等；重新规划改变步骤或依赖，例如用已允许的备用来源取代失败主来源。本例不反复重试主来源，而是最多修复一次。

修复不是扩大权限。只有活动失败恰为policy、备用来源允许且预算未用完才替换。工单非法、检查失败、多来源都失败时交给人，不用别的工具偷偷完成发布。

## 最小示例与操作

工程新建lesson_04.py：

```python
from demo import load_scenarios
from workflow import run_workflow

scenario = next(item for item in load_scenarios() if item["id"] == "primary_down")
state = run_workflow("plan_execute", scenario)
print(state["status"], state["attempts"], state["replans"])
for event in state["trace"]:
    if event["event"] in {"failed", "repair"}:
        print(event)
print(state["completed"]["draft"]["sources"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_04.py`，预期completed、5尝试、1修复，保留policy失败记录、repair复用ticket，草稿来源含simulated-approved-backup/v1。

## 逐步讲解

第一波policy失败、ticket成功，两次都计attempt。repair复制当前plan，移除policy，加backup；draft依赖中的policy改backup，ticket不重做。重新validate_plan后才执行。backup、draft、review再三次，总计5。

errors仍保留旧policy记录；判断当前失败只看活动plan中的ID，因此旧失败不再阻塞已修复路径，但不会从日志消失。修复记录写明新增/移除/复用，让人能解释最终结果从哪里来。

如果backup也down，第三次尝试失败，只有1次修复，needs_human，不会再不断生成新备用名称。若maximum_attempts=4，只完成backup/draft，review未运行，budget_exhausted；有草稿不等于完整任务成功。

## 动手与失败排查

把场景换both_down，预期needs_human/3/1，draft不存在；把allow_backup改False，只有初始2次并停止。资料stale同样不能用于草稿，会尝试允许的当前备用来源。

常见错误：失败不计预算；修复后仍用旧依赖；把失败日志删掉；复用来源已经失效的旧成果；无限添加备用工具；把needs_human叫程序崩溃。交给人是明确终态，检查失败原因与范围再决定新任务。

### 跟做：解释5次

完成标准是失败主来源也算一次，ticket只一次。

> [!example]- 参考答案与解析
> policy、ticket、backup、draft、review共5，旧失败保留。没有再调用policy，也没有重做ticket。

### 独立：为什么不能修工单失败

缺工单时能拿一个别人的工单替代吗？

> [!example]- 参考答案与解析
> 不可，那改变业务对象和用户范围。当前修复规则只允许相同政策的批准备用来源，工单问题需修输入或人工确认。

### 迁移：资料版本更新

新政策到达后哪些成果应失效？

> [!example]- 参考答案与解析
> 旧政策结果及依赖它的draft/review；独立工单可保留但仍核对时效。若保留旧草稿仅改source标签，会造成内容来源不一致。
""",
    )

if __name__ == "__main__":
    lesson(
        4,
        r"""
## 本讲要解决的问题与前置

并非所有任务都需要动态规划。本讲比较固定流程、观察后串行策略和先规划执行，并明确回放能证明什么。前置第4讲修复；读compare_strategies与run_workflow的width选择。

## 三种方式与概念边界

固定工作流预先规定步骤与失败分支；本例fixed不修复。观察后策略每次执行一个动作，收到结果再决定允许的下一动作；本例react_policy用固定规则串行选择及修复，演示ReAct交替观察/行动思想，没有LLM推理。

真实ReAct将语言模型的任务判断与工具行动交替；[ReAct论文](https://arxiv.org/abs/2210.03629)是概念依据。本回放不是该论文完整实现，也不能用其结果给真实ReAct模型排名。

Plan-and-Execute先形成结构化步骤/依赖，再执行，必要时重新规划；本例plan_execute可并行读取和有限修复。[Plan-and-Solve论文](https://arxiv.org/abs/2305.04091)讨论先制定计划再求解的提示思路，并不等同于本工程DAG服务。不要把所有名字相似的流程当同一算法。

## 最小示例与操作

工程新建lesson_05.py：

```python
from demo import compare_strategies

report = compare_strategies()
print(report["scope"])
for item in report["strategies"]:
    print(item["strategy"], item["completed"], "/", item["n"],
          "工具尝试：", item["tool_attempts"], "状态：", item["status_counts"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`。固定1/6、16次；串行观察3/6、22次；先规划3/6、23次。scope明确policy回放，不是真实模型策略基准。currency_cost为None，未调用LLM，不把未知真实费用写0。

## 逐步解释分母与成本

六个合成Case：正常、主来源故障、双来源故障、主来源过期、工单非法、需要发布确认。普通对照不模拟批准，发布Case为awaiting_approval，不算完整发布成功；单列其状态，这种暂停不是不该存在的错误。

fixed在主故障/过期不能自动恢复；另外两规则恢复这两个场景。plan比串行多一次工具尝试，是双来源故障时已并行读取工单，而串行先发现两个政策源失败就停止；这不是模型更聪明或更浪费的泛化结论。

工具尝试包含失败，反映本固定任务的工作量；真实成本还包含规划/修复模型调用、输入输出token、工具费、延迟和人工时间。tiny工具计时可记录但没有吞吐排名意义。两动态规则回放质量相同，不能断言哪个真实模型更好。

## 真实模型对照的具体协议

若之后接入已有获批模型接口，先固定同一任务集、工具/权限、最大调用/修复/token预算、成功判定和可重复条件。记录各次模型选择、结构化参数、工具结果、来源与终态；分别跑固定提示流程、ReAct式选择、先规划再执行，并报告失败Case、样本量、费用及等待确认。

当前未执行真实LLM对照，覆盖台账与验证记录会保留这一限制。接入涉及新SDK、凭据、外部费用或下载时先提出具体方案获得批准，不擅自更改环境。模型产生计划也要经过同样白名单/依赖/权限校验。

## 动手与练习

打开六个results，手数completed/needs_human/awaiting_approval，确认每策略合计6。不要只留下成功场景再改分母。给自己目标选方式：输入稳定流程清楚可固定；路径不确定才考虑受控动态选择。

### 跟做：解释确认Case

完成标准是分母含它、状态单列，不把未批准发布记成功。

> [!example]- 参考答案与解析
> 等待确认是正确边界行为，但若目标包括发布，完整任务还未结束；性能报告需区分等待与错误，不能随意删除这条Case。

### 独立：成功率提高但调用变多

能直接采用吗？

> [!example]- 参考答案与解析
> 还要看价值、成本、延迟和新增风险，当前回放只测固定规则的工具次数，没有模型费用。不能用1/6→3/6推导真实业务收益。

### 迁移：简单固定审批

为什么不必引入自主Agent？

> [!example]- 参考答案与解析
> 步骤和权限已知时固定流程更容易核查，动态模型可能增加成本与不可预测性。只有出现明确决策需求并通过对照才扩展。
""",
    )

if __name__ == "__main__":
    lesson(
        5,
        r"""
## 本讲要解决的问题与前置

计划会执行不等于有权发布。本讲检查确认门、审核先决条件，完成自己的验收报告。前置五讲及 [[../../21_Agent安全与执行边界/00 Agent安全与执行边界学习地图|执行权限边界]]。

## 确认应在什么位置

可以先准备可检查的草稿、来源和固定检查，再在实际副作用前等待。审批者应看到具体操作/对象/内容/来源/影响，而不是批准模糊“以后都自动处理”。确认不能修复无效资料，也不能赋予原本缺少的业务权限。

本例发布是内存标记，simulated_approval为测试开关，不对应真实登录审批；没有发邮件、更新工单或支付。生产必须从可信审批记录取得授权并绑定当前成果版本，不能从模型输出或自由填写body取得。

## 最小示例与操作

工程新建lesson_06.py：

```python
from demo import demonstrate_resume, load_scenarios
from workflow import run_workflow

print(demonstrate_resume())
scenario = load_scenarios()[-1]
scenario["review_passed"] = False
state = run_workflow("plan_execute", scenario, simulated_approval=True)
print("检查失败后的状态：", state["status"])
print("是否发布：", "publish" in state["completed"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_06.py`。第一部分模拟awaiting_approval→completed；检查失败后needs_human、publish不存在，即使模拟批准True也不会越过检查失败。

## 逐步讲解与测试导航

确认门判断发生在提交publish给线程池之前；未批准时没有该工具尝试。发布函数还核对review.passed和draft.is_current，避免只凭门开就送无效成果。未知工具、缺审核依赖、循环计划都应在执行前拒绝。

VS Code读tests/test_workflow.py：并行重叠、政策故障/过期修复、双源失败停止、允许范围/预算、review失败阻发布、检查点恢复不重复读取、策略/场景不匹配与六Case对照。运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
```

tests限定本单元，-q精简输出。测试依赖已有共享pytest，缺包先检查并提出安装方案，不创建单元环境。作者实际21项通过，自己运行与独立扩展另记。

## 动手：完成一页规划报告

写目标/步骤输入输出、DAG依赖、允许工具与来源、并行上限、尝试/修复预算、检查点内容、一个失败与修复链、复用/失效成果、确认门及审批来源、六Case成功/终态/工具次数、真实LLM与外部发布未执行。

自己的独立练习可以增加“备用来源也过期”或“审核失败且模拟批准”的Case，先写预期不发布再运行。状态needs_human/budget_exhausted/awaiting_approval都要保留原因，不强行改成completed来凑成功率。

## 常见错误与练习

把simulated_approval当用户实际授权；旧审批复用于新草稿；检查器叫真人评审；恢复清零预算；动态修复扩工具权限；完成草稿就记发布成功。逐项检查数据、状态、调用记录和审批证据。

### 跟做：检查失败仍批准

完成标准是needs_human且无publish节点结果。

> [!example]- 参考答案与解析
> 确认门和内容/权限校验是不同条件；模拟批准不能让失败资料通过。不要删除review依赖绕开。

### 独立：让旧草稿失效

写出政策变化后应清除哪些completed结果。

> [!example]- 参考答案与解析
> 政策及依赖它的draft/review/publish授权；独立工单可在核对时效后复用。审批绑定旧内容时不能自动跟随新稿。

### 迁移：真实外部执行

最少需要哪些批准证据与恢复措施？

> [!example]- 参考答案与解析
> 可信审批者、操作对象与内容版本、当前权限、幂等请求ID、执行结果与回滚/核查方案。外部结果不明时暂停，不能因为图走到最后就自动再执行。

## 后续

[[../参考工程验证记录|作者机制验证与未测范围]]。下一单元规划：MCP与工具生态，待编写。
""",
    )

if __name__ == "__main__":
    write(
        f"{MAP}.md",
        r"""
## 从哪里开始

打开 [[逐讲学习/01 把业务目标拆成有输入输出的步骤|第1讲]]，在VS Code示例工程运行lesson_01.py，先看节点ID、工具和依赖。第一步完成判断：能区分目标验收与步骤，并说明草稿/检查/发布的不同。

## 六讲顺序

"""
        + "\n".join(
            f"{i + 1}. [[逐讲学习/{name}|{name}]]" for i, name in enumerate(LESSONS)
        )
        + r"""

## 前置与操作

[[../14_Agent运行原理与状态机/00 Agent 运行原理与状态机学习地图|状态机]]、[[../16_并行工具异常处理与可靠性/00 并行工具与可靠性学习地图|并行边界]]、[[../21_Agent安全与执行边界/00 Agent安全与执行边界学习地图|权限]]。Obsidian阅读，VS Code运行，根共享.venv，标准库、不新增依赖。

## 产物与边界

DAG并行、来源失败的有限计划修复、检查点与预算恢复、三种确定性规则六Case回放、模拟发布确认门。未跑真实LLM ReAct/Plan-and-Execute成功率/费用对照，未执行外部发送。不要把回放结果当真实模型基准。

[[示例工程/README|代码导航]] · [[参考工程验证记录|作者验证]] · [[../../00 从这里开始|学习首页]]。自己亲自操作、解释和独立练习再记录进度。

下一单元规划：MCP与工具生态，待编写。
""",
    )

if __name__ == "__main__":
    write(
        "示例工程/README.md",
        r"""
## 先运行

VS Code打开本目录，选择根共享解释器：

```powershell
& ..\..\..\.venv\Scripts\python.exe demo.py --output report-my-01.json
```

报告必须是新文件，已存在拒绝覆盖。仅合成政策/工单和标准库线程，无LLM、外网、真实发布或新包。六Case回放固定1/6与16次、串行观察3/6与22次、先规划3/6与23次；模拟恢复4→5次，外部发送始终不存在。真实LLM对照待执行。

## 代码导航

- [workflow.py](./workflow.py)：计划/依赖校验、合成工具、线程调度、有限修复、状态与预算检查点、确认门。
- [demo.py](./demo.py)：六Case策略回放、临时检查点恢复与模拟批准，报告scope明确。
- [scenarios.json](./fixtures/scenarios.json)：正常/主故障/双故障/过期/坏工单/发布待确认六场景。
- [test_workflow.py](./tests/test_workflow.py)：实际并行重叠、修复复用与预算、发布门、恢复匹配、坏计划与对照分母。
- [requirements.txt](./requirements.txt)：运行标准库，测试工具为共享环境已有包。

## 验证与学习导航

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

[[../00 规划工作流与重新规划学习地图|详细六讲]] · [[../参考工程验证记录|作者结果]]。模拟批准不是真人授权；检查点只读自己可信文件，不提供防篡改签名或真实副作用恰好一次。失败、等待批准与预算终态都保留，LLM费用为未测，不填0。
""",
        "规划工作流示例工程代码导航",
    )

if __name__ == "__main__":
    print("已写入单元29六讲、地图与代码导航")
