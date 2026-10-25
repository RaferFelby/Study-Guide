"""显式生成详细候选数据教材；不在导入时写文档。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/31_推理与工具数据构造"
MAP = "00 推理与工具数据构造学习地图"
LESSONS = [
    "01 把问题计划工具轨迹与答案放进一条样本",
    "02 生成候选数据并记录来源与修订",
    "03 分别校验结构轨迹与答案并安排人工抽检",
    "04 去重并按来源题族切分避免泄漏",
    "05 对齐对话模板并检查监督标签",
    "06 导出候选数据包并设计学习曲线实验",
]


def write(name, body, title=None):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    heading = title or path.stem
    path.write_text(
        f"---\ntitle: {heading}\ntags: [learning, dataset, tool-trace]\nupdated: 2026-10-12\n---\n\n# {heading}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(index, body):
    previous = (
        f"[[{LESSONS[index - 1]}|上一讲]]"
        if index
        else "[[../../30_MCP与工具生态/00 MCP与工具生态学习地图|前一单元]]"
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

只有“问题—答案”能教模型模仿回答，却不能说明工具怎么选、参数如何填、结果从哪里来。本讲把一条工具任务拆成可检查的数据。前置是 Python 字典/列表、[[../../15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|工具契约]] 和 [[../../10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图|对话与监督标签]]。陌生语法沿这些详细教程复习。

顺序：看任务 → 定字段 → 运行最小样本 → 区分计划、轨迹和答案。本工程合成数量相加，不涉及真实订单、金额或客户资料，不调用模型。

## 一条样本要保留哪些证据

我们的任务是：“合成订单00：1件和1件，共有多少件？”允许工具只有 add_units，它接收 left/right 两个整数，返回总数。左、右指两批数量，不是张量或左右边界。工具返回后，最终答案是“合成总数量为2件。”

| 字段 | 用途 | 例子 |
| --- | --- | --- |
| sample_id | 区分每一条样本 | sample-00-0 |
| source_id / family_id | 标记资料来源及同一题的改写族 | source-00 / family-00 |
| question | 用户实际问题 | 合成订单00的两批数量 |
| plan_summary | 简短、可核查的执行计划 | 调用加法工具并依据结果作答 |
| tool_calls | 准备执行的名称、参数和调用ID | call-1 / add_units / left=1,right=1 |
| tool_results | 观察到的结果及对应调用ID | call_id=call-1,total=2 |
| final_answer | 输出给使用者的最终回答 | 合成总数量为2件。 |
| provenance | 来源版本、生成方式、使用范围、修订 | v1 / fixed-addition-v1 |

ID 是身份标记，不是内容正确性的证明。source_id 相同的不同改写仍来自同一对象；family_id 用来把相关说法放在同一组，避免以后拆进训练和测试两边。

plan_summary 是为教学记录的简短计划，不是从模型抽取的隐含思维链。实际可监督的是可观测工具调用、结果与最终回答；不要捏造“真实模型内部推理”。计划写得流畅也不保证动作或答案正确。

## 最小示例与操作

在 VS Code 打开 `01_学习指南/31_推理与工具数据构造/示例工程`。左侧新建文件 `lesson_01.py`，保存：

```python
from data import make_raw_samples

sample = make_raw_samples()[0]
print(sample["sample_id"], sample["source_id"], sample["family_id"])
print(sample["question"])
print(sample["tool_calls"][0])
print(sample["tool_results"][0])
print(sample["final_answer"])
```

打开“终端 → 新建终端”，确认路径结尾是本工程；若当前在根目录，先用 `Set-Location '01_学习指南/31_推理与工具数据构造/示例工程'` 进入。运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe lesson_01.py
```

& 是 PowerShell 的执行运算符；三个 .. 返回工作区根，随后使用已有共享 Python。VS Code 也选择根 .venv，不创建单元环境。预期显示上述三个 ID、问题、left/right 均1、call_id 对应 call-1、total=2和最终2件。

## 逐步阅读代码

导入函数不生成文件；make_raw_samples 调用后才在内存返回候选列表。`[0]` 取第一条，`sample["tool_calls"][0]` 先取调用列表再取其第一项。这里限定一条调用和一条结果，未来多步任务不能照搬 `[0]` 忽略其余步骤。

工具调用与工具结果分开保存，便于发现“参数正确但结果错”“结果对应了另一调用”等问题。最终答案单独保存，便于检查是否真的根据结果作答，而不是只看它与参考答案相等。

当前脚本只生成数据，不执行未知工具。后续校验重放的是本工程固定 add_units 函数，不使用 eval，也不会把数据里的 name 当作任意可执行 Python。

## 动手与常见错误

在笔记画“question → tool_calls → tool_results → final_answer”，箭头旁写对应 ID 与 total。再说明 source/family 为什么需要独立保存。只复制 final_answer 会丢掉依据，复制 plan_summary 不能补回真实观察结果。

ModuleNotFoundError：确认练习脚本在本工程。KeyError：按表格核对英文键，不把中文解释写成键名。列表长度不同：本节只支持单步轨迹，不能随意删步骤来迎合示例。

## 练习与答案

### 跟做：对齐一次调用与结果

提示：比较 id 与 call_id。完成标准是指出对应关系，并手算1+1=2，确认答案与结果一致。

> [!example]- 参考答案与解析
> call-1 是工具调用身份，结果 call_id=call-1 指向它；total=2，最终回答2件。身份匹配和数值正确要分别检查。

### 独立：答案正确就够吗

把工具名想象成 send_order，但最终仍为2件。为什么不能作为正确工具样本？完成标准是说明工具允许范围和任务相关性。

> [!example]- 参考答案与解析
> send_order 不在允许工具中，而且可能有副作用；最终数值巧合正确不能证明轨迹合法。工具选择/参数/观察/答案是不同检查点。

### 迁移：多步资料查询

列出查询、计算、回答任务至少要增加哪些记录。完成标准是包括多次调用ID、结果对应、来源和失败终态。

> [!example]- 参考答案与解析
> 保留每一步名称与参数、对应结果及错误，记录引用资料版本，说明最后成功或拒绝。不能用一段漂亮计划代替缺失的执行证据。
""",
    )
    lesson(
        1,
        r"""
## 本讲要解决的问题与前置

批量写样本很快，但不知道来源、许可和生成方式就无法复核。本讲先理解规则生成，再修订一条失败副本并留下记录。前置是第1讲、Python循环、deepcopy与 [[../../02_测试与实验复现/00 测试与实验复现学习地图|可复现记录]]。

## 候选不等于已批准数据

make_sources 生成24个来源，每个来源两种问题说法，得到48条正常候选。随后加入2条仅首尾空白不同的重复和5条已知错误，所以原始总数55。加入坏例是为了验证清洗能力，不是往训练集故意塞错误。

provenance 中 origin=rule_generated_fixture、generator=fixed-addition-v1、generation_model=None。None 表示未调用生成模型，不表示模型名忘了填。usage_policy=local_teaching_only 是本工程合成资料的本机教学使用约定，不是任何外部数据集的许可证证明。

来源登记表有 source_id、输入数值、family_id、版本和使用范围。规则固定让你能复核；这批合成数据并不覆盖真实订单、自然语言问题或复杂工具环境。

## 最小示例：修副本，保留原错误

新建 `lesson_02.py`：

```python
from copy import deepcopy
from data import make_raw_samples, make_sources
from validation import SampleError, validate_sample

raw = make_raw_samples()
bad = raw[50]
try:
    validate_sample(bad, make_sources())
except SampleError as error:
    print("原始错误：", error)
fixed = deepcopy(bad)
fixed["sample_id"] = "corrected-answer-01"
fixed["final_answer"] = "合成总数量为2件。"
fixed["provenance"]["revision"] = 2
print("修订后：", validate_sample(fixed, make_sources())["fixture_answer_correct"])
print("原记录仍为：", bad["final_answer"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_02.py`。预期 answer_wrong、修订后 True、原记录仍为999件。索引50在本固定生成版本中是错误答案；真实数据应按 sample_id 查找，不依赖行号代表身份。

## 逐步解释修订

deepcopy 复制嵌套字典/列表，修改 fixed 不改变 bad。先验证原始错误，再改最终答案、换新ID、增加 revision；再次验证工具轨迹和来源仍匹配。只改答案不应顺便抹掉原错误。

这次修订是你自己的练习操作，不是已完成真人审核。把旧ID、新ID、改变字段、原因、操作者和日期写到独立修订记录。例如“bad-wrong_answer→corrected-answer-01；字段final_answer；核对两批1件及工具2件后改为2件”。未填写实际审核人时不能写“人工通过”。

生成记录与修订记录职责不同：origin 仍说明原样本由规则生成，revision 说明修改次数。若未来改用模型生成，另记录实际模型/版本、提示模板版本、生成参数、种子（若支持）、工具版本、时间和筛选方法，不填一个从未调用的模型名字。

## 如何扩展到模型生成而不混淆事实

真实模型生成方案可先写：输入来自哪里、能否使用、固定工具约定、最大样本/调用/费用、候选如何验错、如何留失败和抽检。这里没有外部 API、SDK、付费生成或模型下载；确需接入时先核对已有环境、说明安装与费用方案并获批。

模型生成的答案不能同时当唯一正确性参考。应使用独立可复核的工具/业务规则或人工标注；生成器和裁判同样出错时，自动分数可能显得漂亮。当前加法参考可直接重放固定规则，适合先理解流程。

## 动手：填写来源与许可登记

先查看 make_sources 的一条记录，再在笔记填“内容全为本工程合成、无外部原文、教学范围、生成器版本、未调用模型”。若未来引入外部数据，必须记录具体来源地址/版本、实际许可文字与授权依据、允许用途和限制、个人信息处理办法；不知道就标记待确认，不用本例 usage_policy 覆盖它。

## 常见错误与修复

`fixed = bad` 不会复制，会一起改变原始错误；用 deepcopy。为了通过校验把 provenance 删掉：丢来源的样本应拒绝。标“人工修订”却没有记录谁改什么：补真实修订记录，不能靠更高 revision 证明质量。

## 练习与答案

### 跟做：原始错误保留

完成标准是原999件未改变，副本2件通过固定校验，并解释 deepcopy 和 revision 用途。

> [!example]- 参考答案与解析
> 深复制避免覆盖原轨迹；新ID和revision把修改与原始生成分开。True仅证明固定任务检查通过，不证明实际真人已认可。

### 独立：来源版本错了

只把 source_version 改v2，预测结果并运行。提示：来源登记仍v1。完成标准是拒绝而不是静默使用。

> [!example]- 参考答案与解析
> source_version_or_usage_invalid；声明的版本与登记不同。先核对真实来源和修改范围，不通过删除版本检查放行。

### 迁移：模型生成200条

列出你必须保存的元数据与失败记录。完成标准是包含实际模型/提示/参数/工具版本、原始候选、许可、校验和人工复核状态。

> [!example]- 参考答案与解析
> 保存真实调用配置及原始输出，记录失败原因和修订链接；候选数和通过数分开，抽检待完成也写明。未调用就写计划，不伪造“生成完成”。
""",
    )
    lesson(
        2,
        r"""
## 本讲要解决的问题与前置

JSON能读回，不代表工具轨迹或答案正确。本讲把自动校验拆成三层，并为真人准备待填写的抽检表。前置是前两讲、try/except和工具输入检查。

## 三层校验各自回答什么

1. 结构：字段/类型/长度、来源、版本、调用与结果列表是否符合约定。
2. 轨迹：工具是否允许、参数是否匹配该来源、call_id是否对应、重放结果是否一致。
3. 固定答案：最终回答是否符合本合成加法任务的明确参考。

我们只接受两种已知问题模板，并按来源的数值校验问题。它不是通用自然语言事实裁判。general_semantics_verified=False 明确保留这个限制。plan_summary只做非空长度检查，计划语义仍需要人工看；不能把所有字段通过当作“推理完全正确”。

## 最小示例与预期

新建 `lesson_03.py`：

```python
from data import make_raw_samples, make_sources
from validation import clean_samples
from formatting import make_review_sheet

valid, rejected = clean_samples(make_raw_samples(), make_sources())
print("自动通过：", len(valid), "拒绝：", len(rejected))
for item in rejected:
    print(item["sample_id"], item["reason"])
sheet = make_review_sheet(valid)
print("抽检待办：", len(sheet["items"]), sheet["human_review_complete"])
print(sheet["items"][0]["decision"], sheet["items"][0]["reviewer"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_03.py`。预期自动通过50、拒绝5：answer_wrong、tool_result_wrong、call_result_unmatched、tool_not_allowed、source_unknown；抽检8条，完成False，decision=pending、reviewer为空。

## 逐步讲解与错误区分

clean_samples 逐条检查，捕获已知 SampleError，把 sample_id 和原因放进 rejected，保留原始输入供复核。不捕获所有异常冒充“跳过坏数据”，程序实现错误应暴露。

answer_wrong 表示答案与已验证结果不符；tool_result_wrong 表示记录结果不是重放得到的值；call_result_unmatched 表示观察结果属于另一调用。三种不能混成“格式错”。工具名称不允许时不会动态执行名称；来源未知时不会猜一个替代来源。

数值使用 type(value) is int 而不简单 isinstance(..., int)，是因为 Python 的 bool 是 int 的子类，True不应被当作1件。范围0～30是当前合成工具约定，不是所有业务的通用限制。

## 人工抽检怎么做

make_review_sheet 优先从不同题族各取一条，生成8条待办。这是方便教学查看，不是随机统计代表性保证；真实批次还应按失败类型、长度、来源、工具和修订等风险分层选样。

逐条阅读问题、计划、调用/结果、答案与来源：问题是否有歧义、计划是否匹配、是否绕权限、是否引用错误来源、答案是否遗漏条件、文本是否包含不应进入训练的信息。写 decision=accept/reject、真实reviewer、具体reason；拒绝要定位字段并保留修订链。不能只写“看起来不错”。

当前没有真人签署抽检结果，表保持pending，报告human_review_complete=False。你完成真实抽检后保存自己的记录；本程序没有自动读取审批表并放行训练，不把手改一个布尔量当审批。

## 动手：有正确数字的坏轨迹

找到bad-bad_call_id，它的最终数字可以仍是2，但call_id不对应。按三层检查指出是哪一层先失败。再阅读 plan_summary：如果改成不相关计划而其他记录不变，当前自动规则可能仍通过，所以人工复核不可省略。

## 常见错误与修复

把“自动通过50”写成“清洗后50”：还未去重。把抽检表8条写成“人工通过8条”：当前全pending。工具结果错误时只改答案：先重放工具并核对参数，不能一起伪造结果。

## 练习与答案

### 跟做：五类拒绝原因

完成标准是把每个坏例对应到来源、工具、调用关联、观察数值或答案，不只记住5这个数量。

> [!example]- 参考答案与解析
> source_unknown是来源问题；tool_not_allowed是工具允许范围；call_result_unmatched是关联；tool_result_wrong是观察数值；answer_wrong是最终回答。各自修复方式不同。

### 独立：计划语义盲区

假设计划写“直接发货”，调用仍add_units，最终2件。提示：检查当前规则是否读懂计划。完成标准是指出可能自动通过，但人工应拒绝或修订。

> [!example]- 参考答案与解析
> plan_summary仅做类型/长度检查，不理解其语义。人工需对照目标和动作，记录计划不匹配；不能宣称重放数字就验证了全部推理。

### 迁移：为复杂资料任务选抽检

给出至少三类高风险样本。完成标准是说明为何要选，不声称固定8条足够。

> [!example]- 参考答案与解析
> 优先权限边界、多次工具错误、长输入/截断、跨来源引用和人工修订样本，再覆盖普通成功。抽检规模依据风险及发现率调整，不由“500条数据”自然决定。
""",
    )
    lesson(
        3,
        r"""
## 本讲要解决的问题与前置

同一题换句话说，不能一份训练、一份测试；改个ID也不能躲过去重。本讲规范化重复内容，再把来源、题族及重复关系一起用于切分。前置前三讲、Python集合及 [[../../26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图|按来源隔离数据]]。

## 去重与分组不是同一件事

fingerprint 是内容指纹，本例用稳定JSON表示规范化问题、调用、结果和答案。normalize_text做Unicode NFKC、英文大小写归一和空白规范化；保留数字，不把1件与9件洗成同一题。它不是语义向量或万能近重复检测。

实际删除重复还要求来源、题族、计划及生成/修订元数据一致。相同内容但不同依据先保留，否则删掉一条会丢失来源关联或矛盾证据。留下的相同内容会在后续分组连到一起，不跨集合出现。

两种问题说法不一定有相同指纹，但同source_id/family_id仍属于一组。分组把“相同来源、相同题族、相同规范化内容”任一关系连接起来，并合并传递关系：A与B同来源，B与C同题族，则A/B/C整体不能拆开。[分组验证的官方说明](https://scikit-learn.org/stable/modules/cross_validation.html#group-shuffle-split)。本工程用标准库手写小样本演示，不调用sklearn。

## 最小示例与操作

新建 `lesson_04.py`：

```python
from data import deduplicate, make_raw_samples, make_sources
from validation import clean_samples
from splitting import check_leakage, split_samples

valid, _ = clean_samples(make_raw_samples(), make_sources())
unique, duplicates = deduplicate(valid)
print("去重后：", len(unique), "移除：", len(duplicates))
splits = split_samples(unique)
for name, samples in splits.items():
    print(name, len(samples), len({item["family_id"] for item in samples}))
print("跨集合发现：", check_leakage(splits))
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_04.py`。预期48条、移除2；train28条/14组，dev10条/5组，test10条/5组；发现列表为空。

## 逐步理解切分与用途

valid有50条，因为含2条重复。deduplicate保留首条并记录removed/kept映射，原始数据仍在raw中，不覆盖。`_` 表示这个示例暂时不用拒绝列表，不表示程序没有记录失败。

split_samples先按sample_id稳定排序，再把完整连通组用seed17打乱。24组取前60%整数14组作为train，到80%整数19组的中间5组作dev，剩余5组作test；每组2条，所以28/10/10。组不可拆，比例不会严格等于60/20/20。这些比例和种子是教学选择。

train用于拟合，dev用于调超参数或筛方案，test留到方案固定后验收。固定seed控制重复切分，不保证真实模型训练跨环境完全可复现。测试样本不应该再用于改训练数据或选答案模板。

check_leakage在切分后独立检查sample_id、source_id、family_id和内容指纹是否跨集合。没有发现只表示这四种规则未发现重叠，不证明未知语义近重复或真实公开基准污染不存在。

## 动手：故意制造泄漏

在自己的练习脚本复制一个train样本放到dev副本中，再运行check_leakage，应报告ID/来源/题族/指纹重叠。使用deepcopy保护原切分，完成后保留失败报告，不用删掉检查器“修复”。

真实项目还需识别同文档切块、同订单改写、同代码问题变体、不同名称但同一事件等关系。先定义family_id，按关系合并；公共评测题进入训练后，即使换ID，也污染验收。若泄漏关系在切分后才发现，应重新分组切分，并废弃受污染的旧评测结论。

## 常见错误与修复

先按行随机切分再去重：相关改写可能已跨集合。只比sample_id：换名可逃过。去掉所有数字去重：会合并不同数量任务。重复内容来源冲突时直接保留第一条：丢证据；先保留关联，交人工核对。

本分组实现两两扫描，适合几十条教学数据；大数据要用索引/连接关系或成熟工具并验证边界，不用这段代码宣称百万行性能。

## 练习与答案

### 跟做：解释50→48→三份

完成标准是说明去重与分组的不同，能手算14+5+5=24组及28+10+10=48条。

> [!example]- 参考答案与解析
> 删除的是2条同依据重复，保留两种改写；每个来源题族完整进入一个集合。组数取整导致实际比例变化，不能拆组只为凑比例。

### 独立：同题换ID

只改复制样本的sample_id再放dev，哪些检查仍能发现？完成标准是列出至少source/family/fingerprint。

> [!example]- 参考答案与解析
> ID不同不再命中ID重复，但其他三种关系仍重叠。若同时伪造这些字段，规则不能保证识别，需要真实来源治理及人工近重复检查。

### 迁移：一个文档有20块

是否随机分到train/test？提示：看共享来源。完成标准是整份文档/相关族隔离，并说明评估用途。

> [!example]- 参考答案与解析
> 不能把同来源切块当独立新资料，按文档或相关事件组切分。否则模型见过相邻内容，测试可能夸大新来源能力。
""",
    )
    lesson(
        4,
        r"""
## 本讲要解决的问题与前置

结构化样本怎样成为一段可训练输入？工具结果是不是也应该作为模型要模仿的输出？本讲把轨迹变成五条消息，检查标签覆盖。前置是 [[../../10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图|token与mask]]、[[../../26_SFT与LoRA全流程/逐讲学习/01 整理指令数据并只监督答案|监督范围]]；若后一个链接尚不熟，可先返回单元26地图。

## 消息、模板、token三层分开

to_messages生成system→user→assistant工具调用→tool观察→assistant最终答案。system是应用约定，user是问题，assistant是待学习行为，tool是外部观察。本例用assistant内容中的JSON表示调用，是教学中间格式，不是任何模型API或MCP线上请求格式。

encode_training_sample用自定义[role]、[end]文本拼接，每个UTF-8字节一个教学ID。它不是真实LLM Tokenizer，[end]也不是真实模型EOS特殊token。输入仍是顺序序列，不能把这里的0～255字节ID直接喂给真实模型。

真实模型必须使用它自己的chat template、工具格式和Tokenizer；不同模型格式不同，不能只改role字符串就完成适配。[官方对话模板说明](https://huggingface.co/docs/transformers/chat_templating)。本工程未安装Transformers/TRL、未下载模型。

## 最小示例与操作

新建 `lesson_05.py`：

```python
from data import make_raw_samples
from formatting import encode_training_sample, to_messages

sample = make_raw_samples()[0]
print([item["role"] for item in to_messages(sample)])
encoded = encode_training_sample(sample)
print("输入字节：", len(encoded["input_ids"]))
print("监督字节：", sum(value != -100 for value in encoded["labels"]))
for span in encoded["spans"]:
    print(span["role"], span["supervised"])
print("真实模型可用：", encoded["real_model_compatible"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`。本生成器首条样本预期输入348字节、监督132字节；角色五条，只有两条assistant为True，真实模型可用False。模板内容改变时字节数会改变，应该核对范围而非追求数字不变。

## 逐步讲解labels与跨度

每条消息先拼header，再拼body和教学结束文本。header全部标签设-100；system/user/tool正文也设-100；assistant正文与结束文本复制实际ID作为标签。-100是“训练损失忽略这个位置”的常用约定，不是输入token，也不意味着模型看不到这些内容。

工具结果仍进入input_ids，所以最后回答可以依据它；只是这里不要求模型学习伪造工具观察。两段assistant分别监督“选择工具与参数”和“最终答案”。plan_summary保存在候选审计记录，不进入当前训练模板，也不宣称学到了隐藏思维链。

spans记录每段正文的start/end边界，区间含start、不含end。校验标签时逐段检查，比只看监督数大于0更可靠。真实因果训练还要对齐下一token预测的位移；本节只准备未位移输入/标签，没有模型或损失计算，复习单元26的训练过程。

## 动手：检查超长轨迹

本例最大2048字节，超过即拒绝，不自动切掉末尾工具观察或最终答案。可在自己的脚本传maximum_bytes=10，预期明确报超限。把上限盲目增大不会让真实显存无限增加，也不会修复真实Tokenizer不匹配。

真实模板适配至少核对：消息role顺序、调用ID/结果关系、参数序列化、特殊token、是否重复加BOS/EOS、训练与生成模板差异、assistant监督范围、padding和截断。保留一条渲染前后样本，能从token范围追溯到消息。

## 常见错误与修复

把-100放input_ids：混淆输入与标签。只监督最终答案：可能没有教工具选择；这也可以是另一任务设计，但必须说明。监督tool观察：可能让模型学习伪造结果，不应默认开启。字节数叫LLM token数：当前只是教学计量。

单元26的微型训练器使用固定词表和单轮任务，不支持本单元这些工具多轮样本；不能把train.jsonl直接交给它并称兼容。需要模型与数据适配后另行验证。

## 练习与答案

### 跟做：指出两个监督段

完成标准是assistant调用与最终回答为True，其他为False，解释tool依然作为输入可见。

> [!example]- 参考答案与解析
> 监督的是要模型生成的行为；观察结果由工具提供，保留上下文但不当输出目标。屏蔽标签不等于屏蔽注意力或删除输入。

### 独立：模板改一行

system文本增加一句话，哪些量会变化？提示：看输入与监督定义。完成标准是输入字节增加，assistant监督内容不因system增长而增加。

> [!example]- 参考答案与解析
> system增加未监督输入，后续位置跨度右移；当前assistant文本不变，监督字节数相同。应检查新span边界，不能用旧索引硬切。

### 迁移：真实模型格式

列出接入前要核对的项目。完成标准是明确Tokenizer/模板版本、工具格式、监督/截断及实际渲染检查，不只写“转成messages”。

> [!example]- 参考答案与解析
> 使用模型训练时兼容的Tokenizer和模板，核对工具调用与观察格式、特殊ID与labels，检查至少正常/错误/长样本。当前real_model_compatible=False，未完成适配不能改成True冒充验证。
""",
    )
    lesson(
        5,
        r"""
## 本讲要解决的问题与前置

数据包导出了是不是可以开始训练？48条或500条是否够用？本讲检查可复核产物，并制定用学习曲线判断数量的方法。前置前五讲、文件读写及train/dev/test用途。

## 最小示例：生成自己的新目录

工程新建 `lesson_06.py`：

```python
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from pipeline import write_dataset

with TemporaryDirectory(dir=Path.cwd()) as folder:
    output = Path(folder) / "candidate-data"
    report = write_dataset(output)
    print(report["raw"], report["unique"], report["split_sizes"])
    print(report["stage"], report["human_review_complete"])
    sheet = json.loads((output / "review_sheet.json").read_text(encoding="utf-8"))
    print("待抽检：", len(sheet["items"]))
    print("完整候选：", len((output / "candidates.jsonl").read_text(encoding="utf-8").splitlines()))
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_06.py`。预期55/48、28/10/10，candidate_only_pending_human_review/False，抽检8、完整候选48。TemporaryDirectory用于作者/跟做演示，with结束清理；要保存自己的学习包，使用下面CLI新目录。

```powershell
& ..\..\..\.venv\Scripts\python.exe pipeline.py --output-dir report-my-01
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

--output-dir指定新目录，以工程当前路径为基准。已存在拒绝覆盖，改新名称；无需删除旧学习记录。tests限定本工程，-q精简测试输出。作者当前28项测试通过，Ruff检查通过；它们与人工复核是不同证据。

## 数据包各文件的职责

| 文件 | 查看什么 |
| --- | --- |
| raw.jsonl | 原始55条，包括已知错误和重复 |
| candidates.jsonl | 48条完整候选，含计划、轨迹及逐条provenance |
| sources.json | 来源/题族/数值/版本/使用范围 |
| train/dev/test.jsonl | 分组后的messages中间格式，仍标候选 |
| report.json | 拒绝/重复映射、数量、泄漏、摘要和未完成状态 |
| review_sheet.json | 8条待真人填写的抽检任务 |

JSONL是每行一个完整JSON对象，不能把所有行一次json.loads当单个数组。UTF-8便于保留中文。训练消息中间格式不含完整审计字段，所以要连同candidates和sources交接，不只保留train文件。

dataset_sha256是对稳定排序内容生成的摘要，检测当前候选是否变化；不证明来源可信或许可充分。保留生成器版本、切分种子17、规则和原始包。只提交源码与教材，生成报告目录在.gitignore中，可另按自己的归档要求保存。

## 学习曲线怎么决定需要多少数据

学习曲线是“训练数据量变化时，固定验证任务质量怎样变化”的对照。不是画一条假想曲线再当实验，也不是只看训练loss降低。当前未训练模型，learning_curve_measured=False，没有数量充分性的结论。

未来实际实验可从当前train的14个来源组按固定顺序取4/8/14组，对应8/16/28条，形成嵌套训练子集。dev与test始终保留同一5组/5组，不从它们补训练样本。至少记录相同基座/模板、训练预算、种子、实际更新/费用、dev正确率、工具轨迹合法率及失败类型；再重复若干种子观察波动。

数据量变大时固定总更新与固定每样本训练次数是两种不同实验，会影响结论。先明确比较协议；模型、学习率或工具版本一起变时不能把收益全归因于样本数。方案只用dev筛选，最终test在决定后一次验收，避免反复追着测试集改数据。

若质量仍增加且成本可接受，可优先补真实失败类型；若停滞，检查数据覆盖/标签/模型能力，不盲目复制同类题到500条。少量样本可能不稳定，大量同质合成样本也不保证泛化。

## 当前未完成的实践与交接

这份包完成自动规则、候选去重、分组切分、教学模板/标签和抽检待办；没有真实人工签署、模型生成、真实Tokenizer适配、训练或学习曲线。实际接入模型需先选择匹配环境和获批数据，说明下载/依赖方案，再完成适配验证，不擅自安装。

自己的单元验收页分“已运行”“人工待办”“模型实验待办”：记录一条正常样本、五类拒绝、重复映射、分组数量、泄漏失败示例、监督范围、许可/来源登记和未完成项。作者测试不能自动完成C21-01的真人抽检，也不能完成C21-04的实际学习曲线。

## 常见错误与修复

目录存在报错：选择新目录，不覆盖。把train.jsonl称已批准训练集：stage仍候选。把review_sheet存在称抽检完成：decision仍pending。把48条或500条当通用充分数：需要固定验证和真实实验。把生成模型字段None改成热门模型名：未调用就不能填。

## 练习与答案

### 跟做：核对包与状态

完成标准是找到八个文件、核对55/48/28/10/10、8条pending和未训练状态，能说明各文件职责。

> [!example]- 参考答案与解析
> raw保原始，candidates保审计，sources保来源，三份messages保候选切分，report保过程，review_sheet保真人待办；总文件实际是8个（前三个、三份切分、report和review_sheet）。不能因为文件名叫train就跳过批准与格式适配。

### 独立：识别无效数量实验

训练8条用模型A，28条用模型B，B结果更好，能归因样本量吗？完成标准是指出变量混淆并给修正方案。

> [!example]- 参考答案与解析
> 不能，模型变化也是解释。固定基座/模板/评估与训练协议，使用嵌套来源组、记录预算和多个种子，再比较dev；最终test不参与挑数据量。

### 迁移：真实工具数据扩充

提出下一批数据计划而不编造实验结果。完成标准是依据失败类型、来源许可、合法轨迹、人工抽检和固定评估，不只写目标500条。

> [!example]- 参考答案与解析
> 优先补现有合法任务中的具体失败类型，保留来源和独立参考，重复自动规则与人工抽检，按题族隔离。验证覆盖提升后再投入训练，记录成本、无改善和限制；目标数量应由学习曲线与风险决定。

## 后续

[[../参考工程验证记录|作者结果与未完成范围]] · [[../示例工程/README|代码导航]]。下一单元规划：推理时策略，待编写。
""",
    )
    write(
        f"{MAP}.md",
        r"""
## 从第1讲开始

打开 [[逐讲学习/01 把问题计划工具轨迹与答案放进一条样本|第1讲]]，在VS Code示例工程运行lesson_01.py。完成判断：能把问题、简短计划、调用ID/参数、观察和最终答案分开，指出来源与题族。

## 六讲顺序

1. [[逐讲学习/01 把问题计划工具轨迹与答案放进一条样本|01 一条完整样本]]
2. [[逐讲学习/02 生成候选数据并记录来源与修订|02 生成、来源与修订]]
3. [[逐讲学习/03 分别校验结构轨迹与答案并安排人工抽检|03 自动校验与真人待办]]
4. [[逐讲学习/04 去重并按来源题族切分避免泄漏|04 去重、分组与泄漏]]
5. [[逐讲学习/05 对齐对话模板并检查监督标签|05 模板与监督标签]]
6. [[逐讲学习/06 导出候选数据包并设计学习曲线实验|06 交接与数量实验]]

## 前置与应用

[[../15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|工具契约]]、[[../10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图|Tokenizer与标签]]、[[../26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图|数据隔离与训练]]。陌生概念在正文补充或沿链接复习。

Obsidian阅读，VS Code运行；根共享.venv、标准库与已有pytest/Ruff，无新依赖。[[示例工程/README|源码导航]] · [[参考工程验证记录|作者结果]]。

## 产物与真实状态

55条合成原始样本，5条拒绝、2条重复，48条候选按来源/题族分为28/10/10，8条真人抽检待办。简短计划是可读记录，不是模型隐含思维链；教学字节模板不能直接给真实模型。

没有真实人工签署、模型生成、外部数据许可核验、真实Tokenizer适配、训练或学习曲线。示例完成不代表这些实践完成；按 [[../我的学习记录|自己的实际学习记录]] 填结果，未完成保持未勾选。

[[../../00 从这里开始|学习首页]]。下一单元规划：推理时策略，待编写。
""",
    )
    write(
        "示例工程/README.md",
        r"""
## 先运行

VS Code打开本目录，选择根共享解释器，PowerShell运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe pipeline.py --output-dir report-my-01
```

新目录拒绝覆盖。标准库运行，无模型/API/下载/真实资料/新依赖。候选55→自动通过50→去重48→train28/dev10/test10；8条抽检待办，无真人签署、训练或学习曲线。

## 代码导航

- [data.py](./data.py)：合成来源/候选/坏例、文本规范化、内容指纹及保留不同依据的去重。
- [validation.py](./validation.py)：字段、来源/版本、固定工具重放、调用关联、已知问题模板和答案检查。
- [splitting.py](./splitting.py)：来源/题族/指纹传递分组、固定seed切分、四类跨集合泄漏检查。
- [formatting.py](./formatting.py)：五消息模板、UTF-8字节输入和assistant监督标签、8条待真人抽检表。
- [pipeline.py](./pipeline.py)：候选数据包、摘要与未完成状态，不覆盖旧目录。
- [test_dataset.py](./tests/test_dataset.py)：错误、去重保据、传递分组、泄漏、标签、抽检和导出测试。
- [conftest.py](./tests/conftest.py)：仅本工程测试的源码目录。
- [requirements.txt](./requirements.txt)：标准库，测试/格式工具沿用共享环境。

## 结果文件

新目录包含raw.jsonl、candidates.jsonl、sources.json、train/dev/test.jsonl、report.json、review_sheet.json，共8个文件。完整候选保留逐条来源/计划/轨迹；三份messages仍标candidate_only_pending_human_review。原始错误与重复记录不删除，报告保存拒绝原因与removed/kept映射。

## 检查命令

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

作者28项测试通过；首条教学模板输入348字节/监督132字节，两段assistant监督。不是LLM token/EOS/真实模型格式；超长拒绝不静默截断。单元26训练器不能直接读取本多轮工具数据。

## 边界与教材

只校验固定加法和两种问题模板，plan_summary语义未自动验证；不是通用事实裁判。内容指纹不保证语义近重复全检，分组算法适合小规模教学，不宣称大数据性能。usage_policy是合成教学范围，不证明外部许可。人工表pending不代表已抽检；数量充分性需实际学习曲线。

[[../00 推理与工具数据构造学习地图|六讲正文]] · [[../参考工程验证记录|作者结果与待办]]。
""",
        "推理与工具数据示例工程代码导航",
    )
    print("已写入单元31六讲、学习地图和代码导航")


if __name__ == "__main__":
    main()
