"""显式编写推理时策略教材；合成采样与真实LLM实验分开。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/32_推理时策略"
MAP = "00 推理时策略学习地图"
LESSONS = [
    "01 从单次回答理解温度与候选采样",
    "02 用答案投票理解Self-Consistency及其失败",
    "03 用Best-of-N区分结果验证与过程验证",
    "04 给候选步骤输出与时间设置预算",
    "05 在固定题集报告质量覆盖率与成本",
    "06 根据对照停用无收益策略并准备真实实验",
]


def write(name, body, title=None):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    heading = title or path.stem
    path.write_text(
        f"---\ntitle: {heading}\ntags: [learning, inference, sampling]\nupdated: 2026-10-12\n---\n\n# {heading}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(index, body):
    previous = (
        f"[[{LESSONS[index - 1]}|上一讲]]"
        if index
        else "[[../../31_推理与工具数据构造/00 推理与工具数据构造学习地图|前一单元]]"
    )
    following = (
        f"[[{LESSONS[index + 1]}|下一讲]]" if index < 5 else f"[[../{MAP}|返回地图]]"
    )
    write(
        f"逐讲学习/{LESSONS[index]}.md",
        f"[[../{MAP}|单元地图]] · {previous} · {following}\n\n" + body,
    )


def main():
    lesson(
        0,
        r"""
## 本讲要解决的问题与前置

同一个问题问多次可能得到不同回答。怎样控制随机性，又怎样判断更多回答是否值得？本讲先理解单次采样和温度，不急着添加投票或验证器。

前置是Python列表/函数、[[../../05_数学概率与优化/00 数学概率优化学习地图|概率与指数]]、[[../../11_LLM_API与Prompt/00 LLM API 与 Prompt 学习地图|生成参数]]。后面使用字典、循环与异常；陌生语法先回单元01详细讲解。当前示例标准库，无模型/API/下载/GPU。

顺序：分清训练与推理 → 理解候选分数 → 运行温度示例 → 固定种子观察单次结果。

## 推理时计算是什么

训练改变参数；推理在参数固定时生成回答。增加采样次数、验证候选或搜索步骤，可以花更多推理时间尝试提高结果，但没有自动更新模型，也不保证更正确。

本例不运行语言模型，而是对五类**合成候选**按分数采样：correct（正确轨迹）、wrong（错误数字）、bad_steps（最终数字对但步骤错）、loop（重复步骤）、long（过长文本）。这些标签只供生成器造固定测试情形，选择函数不会读取kind或评测参考答案。

任务是合成数量相加，task包含id/left/right/logits；第一题2+3=5。已经能直接用程序相加时，真实应用优先考虑普通函数。这里故意模拟不可靠生成，是为了理解选择策略，不是为了证明需要模型计算加法。

## 温度如何改变分布

logits指候选的未归一化分数；不是已经加到1的概率。温度T>0时，分数除以T再softmax，得到总和1的采样概率。T低时更集中在高分候选；T高时更平坦。更随机不等于更聪明，候选本来都错时不会变成正确。

本工程T=0明确选择最高分候选，平分时取第一个；这是演示的贪心约定。真实模型服务的参数范围及T=0行为需按实际接口核对；我们在“候选类型”层采样，真实LLM通常在每个token层采样，二者不能直接对应质量。

## 最小示例与操作

在VS Code打开 `01_学习指南/32_推理时策略/示例工程`，新建并保存lesson_01.py：

```python
from sampling import evaluation_tasks, probabilities
from strategies import run_strategy

logits = [2, 1, 0, -1, -2]
print("低温：", [round(value, 3) for value in probabilities(logits, 0.5)])
print("高温：", [round(value, 3) for value in probabilities(logits, 2)])
task = evaluation_tasks()[0]
result = run_strategy(task, "single", count=1, seed=17)
print(result["answer"], result["attempts"], result["status"])
print(result["scope"], result["llm_tokens"])
```

打开“终端→新建终端”，确认当前目录为示例工程。根目录进入可用 `Set-Location '01_学习指南/32_推理时策略/示例工程'`。运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe lesson_01.py
```

&让PowerShell执行指定程序，三个..返回工作区根；使用根共享.venv，不创建单元环境。预期低温约[0.865,0.117,0.016,0.002,0.0]，高温约[0.429,0.26,0.158,0.096,0.058]；第一题seed17输出5、1、answered。scope为synthetic_candidate_sampler_not_llm，LLM token为None。

## 逐步读代码与数值稳定

probabilities先检查五个有限分数及温度范围。计算前减去最大分数，再除温度取exp，避免很大正数导致指数溢出；对所有分数减同一常数不改变归一化概率。round只用于显示，实际采样使用未四舍五入的概率，所以打印0.0不一定是真正零概率。

random.Random(seed)创建本次局部随机源，不依赖别的脚本改过全局随机状态。seed相同让本工程抽样可重复；真实GPU/服务模型不一定因同一seed逐字重复。run_strategy返回答案和成本，answered只表示有选出的答案，不表示已经正确。

## 动手与排查

改变seed并记录单次结果；别只保存成功的一次。再把温度设0，解释为何每次都取最高分。负温度、NaN、True都应拒绝，不能用无限分数或无限采样绕过规则。

ModuleNotFoundError：检查脚本是否在本工程。None答案：看status、failures和stop_reason，不把弃权打印成0。输入logits长度错：本例固定五类，不是通用词表模型。

## 练习与答案

### 跟做：解释低温和高温

完成标准是指出最高分概率变小、低分概率变大，并说明“更随机”不证明更正确。

> [!example]- 参考答案与解析
> 升温使分布平坦，候选多样性可能增加，也可能更多抽到错误/循环/过长。概率分数属于合成候选，不是对真实答案正确性的校准。

### 独立：单次answered意味着什么

若answered且答案6，第一题2+3能算成功吗？完成标准是区分选择终态与正确性评分。

> [!example]- 参考答案与解析
> 不能；answered表示返回了一个整数，正确性要按任务参考另评。None与错误整数也应分开记录。

### 迁移：改变真实接口温度

列出实验前后要固定及记录的项目。完成标准是同模型/题集/提示/预算、实际参数、种子支持、费用和失败都记录。

> [!example]- 参考答案与解析
> 温度只是一个变量；固定其他条件并对同一题重复，保存全部结果。不能用一次更好回答推断总体质量提高，接口支持范围需核对实际版本。
""",
    )
    lesson(
        1,
        r"""
## 本讲要解决的问题与前置

单次可能碰巧错，多次答案一致是否更可靠？本讲做答案投票，并观察相关错误怎样让更多样本更糟。前置第1讲、字典/列表/Counter计数；阅读selection.py的majority_answer与strategies.py的vote分支。

## Self-Consistency的概念与本例范围

Self-Consistency可理解为“多次生成后看最终答案一致性”：原论文从多条推理路径的最终答案聚合，而不是只取一条贪心路径。[原始论文](https://arxiv.org/abs/2203.11171)。它依赖候选多样性与正确答案的出现情况，不承诺所有任务都提高。

本工程只演示合成候选的整数答案投票，没有LLM、多条真实推理路径或论文完整复现。多个错误也可能一致；同一个生成器偏差导致的重复错误，不是独立专家的共识。

当前answer必须是整数，便于直接按值计数。真实答案可能有单位、同义表达、格式差异，必须先定义稳定的提取/规范化规则，否则同一答案被拆成多票；不能规范化掉关键数值或条件。

## 最小示例与操作

新建lesson_02.py：

```python
from sampling import evaluation_tasks, make_candidate
from selection import majority_answer
from strategies import run_strategy

task = evaluation_tasks()[0]
correct = make_candidate(task, "correct")
wrong = make_candidate(task, "wrong")
print("平票：", majority_answer([correct, wrong]))
print("错误多数：", majority_answer([wrong, wrong, correct]))
single = run_strategy(task, "single", 1, seed=17)
vote = run_strategy(task, "vote", 5, seed=17)
print("单次与五次投票：", single["answer"], vote["answer"])
print("尝试数：", single["attempts"], vote["attempts"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_02.py`。预期平票None、错误多数6、单次5而投票6、尝试1/5。这个固定seed案例已经说明增加样本可能把原来正确回答改错。

## 逐步解释计数、平票与失败

Counter按answer累计票数，找最大票数；有多个最大答案时返回None，不读取参考答案打破平票。None是明确弃权，不能为了提高成功率偷偷挑正确项。

run_strategy先对每次生成做格式、步骤上限、重复状态和完成检查；循环/超长候选不能投票。但生成失败仍计attempts和字节成本。过滤失败后的有效候选数可能小于请求数，应报告，不从费用中删掉失败。

本投票不做数学正确性验证，因此wrong和bad_steps的完成候选仍可能入票。bad_steps最终数字对，也不说明路径正确。投票选择的是答案一致性，不自动验证步骤和权限。

## 什么时候更多票不解决问题

固定题集第三题几乎只生成同一个错误答案。重复五次不会产生正确路径，只增加一致的错票。第一题seed17单次正确，但后四次的样本让错票胜出；这不是编码故障，是选择规则与生成分布的共同结果。

若把温度设0并重复同一确定性输出，通常只有重复，不新增证据。真实模型多次输出的相关性、问题偏差和答案提取质量都需对照，不能把N次当N个互不相关的证据。

## 动手与常见错误

手数三个明确候选的票，再用函数核对；把平票写成弃权。随后读取evaluation结果中vote的失败与错误，不能只保留投票改善的题。长文本不因出现很多相同数字就多计票，每个有效候选只一票。

错误：参考答案参与平票选择；丢掉失败尝试成本；五次确定性同输出称多样推理；选择过程中看到kind=correct就取它。当前kind只用于合成生成，真实选择不能有这个后门。

## 练习与答案

### 跟做：解释5变6

完成标准是指出单次与多次使用同一任务和seed，投票聚合了更多候选，但多数可能错。

> [!example]- 参考答案与解析
> 第一个候选给5，后续的分布偏向错误6，多数6胜出；增加计算不是单调提高质量。比较必须保留这一退化。

### 独立：四个答案分成2比2

先写预期，再构造两个correct/两个wrong调用majority_answer。完成标准是None及平票原因。

> [!example]- 参考答案与解析
> 没有唯一最高票数，弃权。若要另一平票规则，应预先固定并报告，不能按评测参考临时选择。

### 迁移：文本答案归一

“5件”“总数5”“五件”如何处理？完成标准是规则一致、保留单位/条件，无法可靠解析时弃权。

> [!example]- 参考答案与解析
> 可定义受控任务格式及数值/单位提取，把等价表达归同类；语义含糊或单位不同不强合并。需要验证提取器，不能用模糊相似就当同答案。
""",
    )
    lesson(
        2,
        r"""
## 本讲要解决的问题与前置

既然多数可能错，可以让验证器从N个候选挑更好的一个吗？最终数字正确是否足以证明步骤正确？本讲区分Best-of-N、结果验证和过程验证。前置第2讲和 [[../../31_推理与工具数据构造/逐讲学习/03 分别校验结构轨迹与答案并安排人工抽检|校验分层]]。

## 三个概念分开

Best-of-N是先生成N个候选，再按预先固定评分选择一个；不一定投票。Verifier是验证器，可用明确规则、外部执行结果或训练的模型评分。PRM是Process Reward Model，过程奖励模型，通常学习评价中间步骤，和只评价最终结果的方式不同。[过程监督论文](https://arxiv.org/abs/2305.20050)。

本例结果验证检查answer等于输入left+right；过程验证逐个比较add和finish两个固定步骤。它们是精确加法规则，不是经过训练的PRM，不返回校准正确概率，也不是通用复杂推理裁判。

因此这个玩具验证器能算出答案，真实数量任务直接用加法函数更简单。我们保留它是为了看清“评分—选择—拒绝”的程序机制，不能把此处提升归因于语言模型更会推理。

## 最小示例与操作

新建lesson_03.py：

```python
from sampling import evaluation_tasks, make_candidate
from selection import outcome_score, process_scores, verified_score
from strategies import run_strategy

task = evaluation_tasks()[0]
bad = make_candidate(task, "bad_steps")
print("结果检查：", outcome_score(task, bad))
print("各步检查：", process_scores(task, bad))
print("综合检查：", verified_score(task, bad))
result = run_strategy(task, "best_of_n", 5, seed=17)
print(result["answer"], result["attempts"], result["verifier_calls"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_03.py`。预期结果1、步骤[0,1]、综合0；Best-of-N输出5、生成5次、验证5次。最终数字对却中间加法错的候选被拒绝。

## 逐步讲解评分与选择

bad_steps的add.result为6，finish.result和answer为5。只看answer能通过；看每步发现第一步不符。verified_score取结果和各步分数的最小值，任何一项0就拒绝。这是当前二步固定任务的规则，不是所有PRM必须用min。

只有格式/预算允许的完整候选进入验证；生成成本和验证成本分别计。选择取最高分，最高分必须1才返回答案；全部0时弃权，不“总得选一个”。同分时保留先出现者，不用参考标签打破同分。

生成任务只允许id/left/right/logits，不允许reference字段。评测参考在选择后评分，不发给选择函数。验证器能依据题目输入算数学结果，这是可执行任务规则，与读取测试答案标签不同；但规则覆盖范围必须说明。

## 学习型PRM还需要什么

真实PRM需步骤数据、标注定义、模型训练与独立验证，分数可能有误、受长度或表面格式影响。仅替换verified_score名字为prm_score不会让规则变成训练模型。过程分数高也可能奖励投机或错误步骤，要检查失败样本和分布外情况。

本单元未训练/下载PRM，也未执行真实LLM验证器。接入需匹配模型与模板、批准数据/依赖/费用，并单独报告生成和验证调用的token及延迟；不能只计算生成费用。

## 动手与常见错误

把所有候选设为wrong的测试题交Best-of-N，预期None，验证调用仍5。查评分函数为何不接受bad_steps；再写一个仅按文本长度评分的假设，解释它为什么可能偏爱冗长错误。没有正确候选时，再好的选择器也无法创造一个已有候选之外的正确答案。

错误：把规则分数1解释成100%真实概率；验证成本忽略；直接把测试参考喂给排序器；全部失败仍返回最高分文本；把步骤字符串存在当步骤正确。

## 练习与答案

### 跟做：结果对、步骤错

完成标准是1/[0,1]/0，并用2+3=5解释add.result=6的问题。

> [!example]- 参考答案与解析
> 最终数字巧合正确不能修复中间错误。当前综合规则要求所有检查通过；对更复杂任务需重新定义合法步骤，而不是机械套两步模板。

### 独立：所有候选验证0

预期status和answer是什么？提示：看选择阈值。完成标准是abstained/None，失败成本保留。

> [!example]- 参考答案与解析
> 最高分仍未达1则不返回答案，避免强行选择明显未通过项。生成5次和验证5次仍消耗预算，不能把弃权记为免费。

### 迁移：资料问答验证器

提出三项可检查条件与不能证明的范围。完成标准是来源授权/引用对应/内容支持，明确规则或模型的盲区。

> [!example]- 参考答案与解析
> 可验证来源范围、引用片段与版本、答案是否有支持；事实语义和完整性可能需人工/独立模型复核。评分不应因文风长短就判断正确，权限仍在执行层校验。
""",
    )
    lesson(
        3,
        r"""
## 本讲要解决的问题与前置

多采样和验证不能无限运行。本讲为次数、步骤、输出、总字节及时间设界限，并把停止原因和失败费用留在报告。前置前三讲、字典复制和 [[../../16_并行工具异常处理与可靠性/00 并行工具与可靠性学习地图|超时与取消]]。

## 六个预算的含义

DEFAULT_LIMITS包括候选5次、单候选8步、模拟输出512字节、总8192字节、实际程序2秒和模拟服务0.2秒。数字是教学选择；真实任务要按资源和容错要求制定。

生成前先预留问题输入字节和最大输出，余额不足不开始下一次。候选返回后检查步数、重复步骤、完成状态；超长标output_limit，重复相同步骤标loop_detected，失败仍计attempt。验证另占字节与模拟0.002秒，不能只预算生成。

字节预算是本合成后端的计量，不是LLM token预算。long候选由本地先构造固定合成文本，再模拟截流/失败，512是演示的输出计费上限；不证明真实模型会在512字节停止生成或取消请求。

## 最小示例与操作

新建lesson_04.py：

```python
from sampling import evaluation_tasks
from strategies import DEFAULT_LIMITS, run_strategy

loop_task = evaluation_tasks()[3]
limits = {**DEFAULT_LIMITS, "maximum_candidates": 2}
result = run_strategy(loop_task, "vote", 5, limits=limits)
print(result["attempts"], result["answer"], result["stop_reason"])
print(result["failures"], result["total_bytes"] > 0)
small = {**DEFAULT_LIMITS, "maximum_total_bytes": 100}
limited = run_strategy(evaluation_tasks()[0], "vote", 5, limits=small)
print(limited["attempts"], limited["stop_reason"], limited["total_bytes"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_04.py`。预期2、None、candidate_budget，两次loop_detected且成本>0；小字节余额预期0、byte_budget、0。请求5次不等于实际执行5次。

## 逐步解释代码和边界

`{**DEFAULT_LIMITS, "maximum_candidates": 2}`先复制默认字典的各项，再覆盖这一项，不改全局默认值。星号展开只是字典合并语法，其他五项保留。不能只传一个字段让程序猜剩余预算，validate_limits要求完整预算。

循环候选六次重复同一add状态；这里按完全相同的步骤记录判断重复。一般业务可能合法重复请求，必须结合状态是否推进与任务语义定义，不能把任意同名工具第二次调用都叫死循环。

最大步骤在候选生成返回后检查，不是生成过程中逐步强制停止；真实流式生成/Agent工具循环应在每步前检查预算，并能取消实际后端。这个有限采样器每次生成必定很快，不能直接包装不可中断真实调用就声称硬超时。

## 两种时间不要混在一起

wall_seconds是time.perf_counter测到的本机实际运行时间，包含本段候选/选择程序；simulated_seconds是固定0.01+输出字节×0.00001及验证0.002秒的模型化服务时间，没有实际等待。这两者都不是LLM真实延迟。

实际截止时间在生成/验证前后检查。超时返回的候选会被丢弃，并记录late_candidate/late_verification；程序检查不能强行中断一个卡住的函数。测试用可控时钟证明迟到结果未被接受，不伪造真实网络取消验证。

部分候选已可用但后续预算耗尽时，当前策略可以对已有有效候选做选择，并保留stop_reason；这不是“完成全部N次”。如果业务要求完整采样，应另定拒绝规则。Best-of-N不使用未验证的最后候选。

## 动手与错误排查

把maximum_steps改1，正常两步候选应step_limit。把maximum_simulated_seconds改0.001，应生成前停止。零/负/无限预算与bool次数拒绝，不用无上限while循环替代。

成本预留可能保守：余额不足最大输出时，即使实际短答案也可能停止，这是当前保护选择。不要为“多跑一次”悄悄扣掉失败成本；记录真实未测费用为None，而不是0。

## 练习与答案

### 跟做：失败仍花预算

完成标准是两次循环均计attempt、成本>0、停止原因candidate_budget，而不是正确完成5次。

> [!example]- 参考答案与解析
> 生成已发生，即使不能投票仍有模拟输入输出成本。上限检查不因失败而重置，否则可无限失败重试。

### 独立：未验证候选

生成后剩余额不足验证时能用答案吗？完成标准是Best-of-N不选未评分项，保留已花生成费用。

> [!example]- 参考答案与解析
> 不能；verification_budget停止，这一项未进入scored。其他已验证项可按预先固定规则选择，无项则弃权。

### 迁移：真实服务硬超时

列出除了检查时钟还需要什么。完成标准是后端超时/流式限制/合作取消及失效连接处理，写操作另查幂等。

> [!example]- 参考答案与解析
> 每次请求设置实际超时与输出上限，流式/步骤中检查，支持合作取消并清理自有资源；不能用线程join超时假装杀掉任务。真实写操作响应不明时查询执行状态，不自动重复。
""",
    )
    lesson(
        4,
        r"""
## 本讲要解决的问题与前置

“Best-of-N答出的都对”可能只是它拒绝了多数问题。怎样同时报告质量、覆盖率、成本和时间？本讲用固定六题、三种seed配对比较。前置前四讲及 [[../../19_Agent评估体系/00 Agent 评估体系学习地图|分母与失败]]。

## 固定实验协议

每策略用同六个合成题、seed17/18/19、温度1.0和同预算。single生成1次，vote和best_of_n请求5次。候选序列由相同局部seed驱动，N=5的首项与N=1配对；验证额外成本单独记录。

18是六题重复三种seed的运行数，不是18个独立问题。循环、过长、相关错误都在题集中保留；不能因为难题不回答就从分母删除。此处没有训练或用dev调配置，也不声称是真实test基准；test-ID只是固定合成夹具名字。

## 最小示例与操作

新建lesson_05.py：

```python
from evaluation import compare

report = compare()
print(report["unique_tasks"], report["seeds"])
for item in report["summaries"]:
    print(item["strategy"], item["correct"], "/", item["n"],
          "回答", item["answered"], "次数", item["attempts"],
          "验证", item["verifier_calls"], "字节", item["total_bytes"])
    print("模拟秒", round(item["simulated_seconds"], 5),
          "真实LLM token", item["llm_tokens"], "费用", item["currency_cost"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`。预期结果见下表；本机wall_seconds会随负载变化，不能要求和作者小数相同。

| 策略 | 正确/全部运行 | 返回答案 | 生成尝试 | 验证调用 | 总教学字节 | 模拟服务秒 |
| --- | --- | --- | --- | --- | --- | --- |
| single N=1 | 5/18 | 12/18 | 18 | 0 | 4518 | 0.22248 |
| vote N=5 | 3/18 | 12/18 | 90 | 0 | 22590 | 1.11240 |
| best_of_n N=5 | 6/18 | 6/18 | 90 | 60 | 32955 | 1.23240 |

## 分母怎么解释

整体正确率为正确数/全部18次，弃权算未正确。覆盖率为answered/18，说明多少次返回答案。已回答正确率则为correct/answered，三者用途不同：Best-of-N是6/18整体、6/18覆盖、6/6已回答正确；不能只展示100%隐藏2/3弃权。

当前correct只看最终数字相等，不是所有策略轨迹均正确的统计。Best-of-N另要求规则步骤通过；single/vote可能选择最终对但步骤错的样本。真实报告需要单独增加轨迹、来源、权限和任务完成指标。

Best-of-N验证60次不是90次，因为循环/过长在验证前被筛掉，但其生成费用仍在90次中。费用字段None表示真实LLM收费未测，字节不是token；不能把32955字节按API单价计算账单。

## wall时间和成本的实际限制

作者一次本机循环总耗时大约0.00079/0.00213/0.00224秒，这是Python小程序，不是模型吞吐。simulated_seconds来自固定演示公式，不是真实等待。微秒级测量受噪声影响，不能用它给生产策略排性能名次。

真实实验应记录每次生成/验证模型的输入、输出、计费token、实际延迟、重试、超时和工具费用，按实际接口计量。选择参考标签在run_strategy返回后才加入correct，不能当验证器输入。

## 动手：追踪退化与弃权

打开完整report的runs，按task_id/seed配对single和vote，找第一题seed17从5变6。再找Best-of-N对相关错误/循环/过长的弃权。需要定位具体失败而不是只说平均提高。

如果测试只保留能输出的12次，single看起来5/12，但这是条件指标，必须同时给18的总体分母。种子重复不增加独立题数，样本极小，不能报告可靠业务收益或统计显著性。

## 练习与答案

### 跟做：算三个指标

用Best-of-N算整体正确、覆盖和回答内正确率。完成标准是三项都写分母。

> [!example]- 参考答案与解析
> 6/18≈33.3%，6/18≈33.3%，6/6=100%。最后一项不能代替前两项，拒绝了12次，仍消耗生成与验证预算。

### 独立：五倍投票值得吗

仅按本配置结果写结论。完成标准是3/18低于5/18、字节4518→22590，并限制为合成配置。

> [!example]- 参考答案与解析
> 此配置投票无收益且退化，成本约五倍，应停用它的默认采用。不能因此证明Self-Consistency在所有真实模型上无效。

### 迁移：真实token费用报告

列出必须新增的实测字段。完成标准是生成和验证分开、失败/重试包含、模型/版本/题数/预算固定。

> [!example]- 参考答案与解析
> 保存各调用输入输出/计费token及实际价目依据、端到端延迟和失败，记录唯一问题数与重复运行数。当前None字段留未测，不能用UTF-8字节充当真实token。
""",
    )
    lesson(
        5,
        r"""
## 本讲要解决的问题与前置

有了对照，怎样决定保留哪种策略，怎样准备真正模型实验而不捏造结论？本讲完成本单元验收，明确停用、限定采用和待测。前置前五讲及 [[../../20_可观测性可靠性与成本/00 可观测性可靠性与成本学习地图|成本与限制]]。

## 先写具体采用条件

本配置vote正确数下降且生成五倍，因此停用这项默认五次投票配置。Best-of-N提升1/18总体正确，但教学字节约7.3倍、覆盖率更低；只说明规则过滤有条件收益，不能据此上线真实模型方案。

可写决策：“在当前固定合成对照中保留单次基线；拒绝默认投票；Best-of-N作为规则验错教学保留，真实收益/费用待测”。停用无收益方案是完整的实验结论，不是学习失败，也不是对方法的普遍否定。

## 最小示例：让程序展示不采用证据

新建lesson_06.py：

```python
from evaluation import compare

single, vote, best = compare()["summaries"]
print("投票是否改善：", vote["correct"] > single["correct"])
print("投票成本倍数：", vote["total_bytes"] / single["total_bytes"])
print("Best-of-N正确增加：", best["correct"] - single["correct"])
print("Best-of-N覆盖：", best["answered"], "/", best["n"])
print("真实LLM费用已测吗：", best["currency_cost"] is not None)
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_06.py`。预期False、5.0、增加1、6/18、费用已测False。不要因其中“增加1”就忽略规模、弃权和额外成本。

## 保存完整报告与运行测试

在工程终端用新文件名：

```powershell
& ..\..\..\.venv\Scripts\python.exe evaluation.py --output report-my-01.json
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

--output指定以当前工程为基准的新JSON文件，已存在拒绝覆盖，改新名字。tests只跑本单元，-q简化输出；Ruff分别检查规则和格式，不替代运行。作者当前27项示例测试通过；你的学习验收还需独立解释和练习。

报告保留所有runs、温度/seed、预算、失败、停止原因、生成/验证字节、模拟/实际本机时间和未测LLM费用。不要删掉失败再计算成功率。源码和范围从 [[../示例工程/README|代码导航]] 进入。

## 真实模型实验的可执行计划

1. 明确任务和模型：用已获批数据，固定提示/模型/Tokenizer版本，工具允许范围与成功标准；不直接把合成test-ID当真实业务集。
2. 先定义dev调策略、最终保留test的用途。用dev选择N、温度、答案提取和验证阈值，test在方案固定后验收；不得反复追着test改配置。
3. 比较单次、N次投票与Best-of-N，尽量共享候选序列，记录唯一题数和多次种子。生成器/验证器不同要分别记录，不把规则分数叫学习PRM。
4. 实测生成与验证的输入/输出/计费token、调用延迟、端到端延迟、失败/重试和费用；设置每次与全任务的token/时间/调用上限，实际后端需要取消和流式限制。
5. 对照正确率、覆盖率、有效轨迹及具体失败类型；当提升不支持额外成本或风险，记录并停用。若采用，只在验证过的范围保留基线回退。

当前没有模型接口、SDK安装、权重下载、API key或费用。接入前先核对共享环境，给出模型/依赖版本、安装位置、CPU/CUDA或远程选择、下载规模/费用和回归影响，获批后执行。不能通过把report.scope改成real_llm完成实验。

## 交付自己的单元报告

写问题/固定题集/策略/温度/N、生成与验证规则、预算与实际执行次数、整体/条件质量、覆盖率、两个时间尺度、教学字节/真实token未测、一个退化/弃权Case、采用/拒绝条件与下一步。

C22-01和C22-02当前只做合成策略机制对照；真实LLM质量、延迟和token费用仍待实践。C22-03已提供有界示例，但实际后端硬取消未实现。不要把作者测试当真实生产实验或个人已掌握。

## 常见错误与练习

错误：更多采样必更好；验证器永远正确；100%条件正确率掩盖低覆盖；模拟秒当实测延迟；字节当token；没有正确候选却强选；只写采用不记录退化。

### 跟做：写不采用投票的结论

完成标准是质量/成本数字、具体范围和保留基线，不只一句“投票不好”。

> [!example]- 参考答案与解析
> 固定六题三seed的合成配置中，vote3/18低于single5/18，字节五倍，所以停用当前默认vote配置并保留single。真实模型方法是否有效尚未测，不扩大结论。

### 独立：只看6/6能采用吗

提示：同时看覆盖和总体。完成标准是拒绝直接上线，并提出实测收益/成本条件。

> [!example]- 参考答案与解析
> 6/6仅针对答出的六次；总体6/18、12次弃权和更高成本都要保留。需业务可接受覆盖率、真实质量和费用再决定。

### 迁移：真实实验无收益

若多次采样质量相同但费用更高，你交付什么？完成标准是可复核结果、停用条件和未来针对失败的计划。

> [!example]- 参考答案与解析
> 交付固定协议、所有运行和失败、质量/成本对照，停用额外采样，保留基线与限制。以后按新证据再试，不为证明方法有用隐去无改善结果。

## 后续

[[../参考工程验证记录|作者结果与真实未测范围]]。下一单元规划：DPO与偏好优化，待编写。
""",
    )
    write(
        f"{MAP}.md",
        r"""
## 从第1讲开始

打开 [[逐讲学习/01 从单次回答理解温度与候选采样|第1讲]]，在VS Code运行lesson_01.py。第一步完成判断：能区分温度、候选概率、单次输出和正确性；说明本例不是LLM。

## 六讲顺序

1. [[逐讲学习/01 从单次回答理解温度与候选采样|01 单次与温度]]
2. [[逐讲学习/02 用答案投票理解Self-Consistency及其失败|02 投票及其退化]]
3. [[逐讲学习/03 用Best-of-N区分结果验证与过程验证|03 Best-of-N与验证]]
4. [[逐讲学习/04 给候选步骤输出与时间设置预算|04 预算与停止]]
5. [[逐讲学习/05 在固定题集报告质量覆盖率与成本|05 质量、覆盖与成本]]
6. [[逐讲学习/06 根据对照停用无收益策略并准备真实实验|06 采用判断与真实计划]]

## 前置与工程

[[../05_数学概率与优化/00 数学概率优化学习地图|概率]]、[[../19_Agent评估体系/00 Agent 评估体系学习地图|评测分母]]、[[../31_推理与工具数据构造/00 推理与工具数据构造学习地图|轨迹与校验]]。陌生概念沿详细教程复习。

Obsidian读讲解，VS Code读 [[示例工程/README|代码导航]]。标准库、根共享.venv与已有pytest/Ruff，不增加依赖、不使用GPU/模型接口。

## 实际产物与边界

五类合成候选采样、整数投票、精确规则验证、有界执行、固定六题三seed对照。single5/18、vote3/18、best_of_n6/18；vote成本五倍却退化，Best-of-N低覆盖且验证另有成本。

没有LLM真实推理路径、学习PRM、真实token/费用/延迟；模拟服务秒与本机程序秒分开。时钟检查不强杀真实阻塞后端。[[参考工程验证记录|作者验证]]不替代自己的练习和真实实验。

[[../../00 从这里开始|学习首页]] · [[../我的学习记录|记录实际学习结果]]。下一单元规划：DPO与偏好优化，待编写。
""",
    )
    write(
        "示例工程/README.md",
        r"""
## 先运行

VS Code打开本目录，使用工作区根共享Python：

```powershell
& ..\..\..\.venv\Scripts\python.exe evaluation.py --output report-my-01.json
```

新文件不覆盖。只生成合成候选，不用模型/API/下载/真实数据，不安装依赖。

## 代码导航

- [sampling.py](./sampling.py)：五类候选、候选层温度softmax、固定六题和局部随机源。
- [selection.py](./selection.py)：完整/循环/步数检查、答案投票、固定加法结果与步骤验证。
- [strategies.py](./strategies.py)：single/vote/best_of_n、次数/字节/实际及模拟时间预算，失败成本与弃权。
- [evaluation.py](./evaluation.py)：六题×三seed配对，选择后评分，报告全部运行且不覆盖文件。
- [test_strategies.py](./tests/test_strategies.py)：温度/平票/错误多数/步骤错、预算/迟到结果、失败成本和对照分母。
- [conftest.py](./tests/conftest.py)：只为本工程测试加入源码目录。
- [requirements.txt](./requirements.txt)：运行标准库，测试/格式使用共享环境已有工具。

## 实际固定结果

N=1 single5/18、回答12、尝试18、字节4518；N=5 vote3/18、回答12、尝试90、字节22590；N=5 best_of_n6/18、回答6、尝试90、验证60、字节32955。18是六题三seed，不是18独立题。全分母包含循环/长输出/弃权。

生成模拟0.01+输出字节×0.00001秒，验证每次模拟0.002秒；wall_seconds仅本机Python耗时。字节不是真实LLM token，费用None为未测；规则验证不是学习PRM。当前投票配置无收益应停用，不能扩大到所有真实方法。

## 检查命令

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

作者27项示例测试通过。时钟检查前后丢弃迟到结果，但不强行中断真实后端；long在本机先造固定文本再模拟超限，不证明真实流式截流。真实接入须另验证超时/取消/token预算、Tokenizer和模型费用。

## 教学入口

[[../00 推理时策略学习地图|六讲正文]] · [[../参考工程验证记录|作者实际范围]]。[Self-Consistency论文](https://arxiv.org/abs/2203.11171) · [过程监督论文](https://arxiv.org/abs/2305.20050)。本工程只是机制教学，不是论文实验复现。
""",
        "推理时策略示例工程代码导航",
    )
    print("已写入单元32六讲、地图与代码导航")


if __name__ == "__main__":
    main()
