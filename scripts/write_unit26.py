"""本次教材正文写入器；不执行训练、不修改学习者进度。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/26_SFT与LoRA全流程"
LESSONS = [
    "01 整理指令数据并只监督答案",
    "02 按来源切分并理解拼接边界",
    "03 手写LoRA看懂秩缩放与冻结",
    "04 运行CPU和GPU训练并恢复状态",
    "05 比较Base与两组LoRA的保留集表现",
    "06 保存适配器合并权重并决定是否采用",
]
MAP = "00 SFT与LoRA全流程学习地图"


def write(name, body, title=None):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {title or path.stem}\ntags: [learning, pytorch, sft, lora]\nupdated: 2026-10-11\n---\n\n# {title or path.stem}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(index, body):
    previous = (
        f"[[{LESSONS[index - 1]}|上一讲]]"
        if index
        else "[[../../25_岗位分析项目表达与投递复盘/00 岗位分析项目表达与投递复盘学习地图|前一单元]]"
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

我们希望模型收到 `route red item 0 answer :` 后，输出 `tag = R` 并结束。SFT是监督微调：给模型成对的输入和正确输出，用误差更新参数。本例先训练一个会复制颜色的微型Base，再用LoRA学习新输出格式；Base表示微调前的同一份权重，不意味着它已经是通用大语言模型。

需要会字典、列表、函数调用和张量。若还不能解释 `tensor.shape`，先返回 [[../../06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|张量与训练基础]]；因果注意力、下一token预测复习 [[../../08_Transformer从零实现/00 Transformer 从零实现学习地图|小语言模型]]。本讲补充token、监督位置，不默认你理解数据框架。

快速顺序：先理解字段 → 运行一条数据 → 观察labels → 检查三种格式 → 做练习。源码见 [[../示例工程/README|代码导航]]，主要读 `data.py`。

## 概念与直觉：格式不同，监督目标要相同

token是模型使用的离散片段。本例用空格切词，`red`是一个token；真实中文模型往往使用子词切分，不能照搬这里的切分方式。词表是片段到整数编号的表，本例预定义94个token，包含两个颜色、80个ID以及特殊符号，不从测试集学习词表。

原始记录有 `instruction`（要做的动作）、`input`（具体输入）、`output`（答案）、`source_group`（来源组）。这是Alpaca风格的单轮教学数据。messages风格使用角色为user、assistant的消息；ShareGPT风格在本例只支持一轮human、gpt。真实数据可能多轮且字段不同，必须先核对格式，不能因为名字相同就直接接入。

EOS是“回答结束”的特殊token，PAD是“把短样本补齐”的token。它们用途不同。训练模型预测EOS，推理时才能知道停止；PAD没有业务答案含义，不应计入损失。

## 最小示例：查看真正被监督的位置

在VS Code打开本单元 `示例工程` 文件夹，新建 `lesson_01.py`。右下角选择工作区根目录共享 `.venv` 的解释器，粘贴：

```python
import torch
from data import make_records, normalize_record, make_batch

record = make_records()[0]
row = normalize_record(record)
inputs, labels = make_batch([row], torch.device("cpu"))
print(row)
print("输入形状：", tuple(inputs.shape))
print("监督标签：", labels[0].tolist())
```

在该文件夹的PowerShell终端执行 `& ..\..\..\.venv\Scripts\python.exe lesson_01.py`。`&`是执行程序，后面路径从当前工程回到工作区共享解释器；最后一个参数是要运行的文件。

正常结果：prompt含6个token，answer为 `tag = R <eos>`，输入形状 `(1, 9)`，标签为 `[-100, -100, -100, -100, -100, 10, 11, 12, 1]`。数字由固定词表决定，R为12、EOS为1。

## 逐步讲解：为什么长度10变成9

1. `make_records`生成320条本地合成数据，没有读取用户隐私或联网下载。
2. `normalize_record`把不同字段格式转换成prompt/answer两串token，并在答案末尾加EOS。
3. 完整序列是6个提示token加4个答案token，长度10。输入取前9个位置；标签取后9个位置，让每个输入位置预测下一个token。
4. 提示的第0～4位置预测的仍是提示，标签设为-100。它不是词表编号，而是交叉熵函数的“忽略该位置”约定。位置5是冒号，应该预测首个答案 `tag`，因此不能一口气忽略6个位置。
5. 模型仍能读取提示参与计算，只是不因“复述提示”获得训练奖励。loss mask只决定哪里计算误差；attention mask决定能看哪些位置，两者不是同一件事。

本例对右侧补齐位置也填-100。因果注意力让有效位置不能看后面的PAD；只对真实答案统计误差。它不实现左补齐生成和任意长度批量解码。

## 动手：把相同样本改成messages格式

复制 `record` 的内容到一个新字典，字段改为 `messages` 和 `source_group`。两条消息分别是user的 `route red item 0 answer :` 和assistant的 `tag = R`。调用 `normalize_record`，与原结果比较，必须相等。不要在答案里手写EOS，因为转换器已经添加一次。

对真实数据清理时先核对授权、空文本、重复、过长样本、角色次序、隐私信息和来源；这里仅验证固定字段、非空与重复，未提供通用隐私脱敏器。长度超过模型16位置时会明确失败，不能截断后悄悄丢掉整个答案。

## 常见错误与排查

- 找不到torch：先确认选择根目录共享解释器，并运行 `& ..\..\..\.venv\Scripts\python.exe -c "import torch; print(torch.__version__)"`。若仍缺失，记录报错再提出安装方案，不使用全局pip。
- 不认识token：先读错误中的词，再检查固定词表。本例不能接受任意自然语言；改数据规则时需要同步词表及模型词表大小，不能仅删除未知词。
- labels全部-100：检查位移与提示边界；没有监督token会被拒绝，loss=0不表示学得很好。
- messages角色倒置：转换器拒绝，先修数据，不跳过错误记录后宣称数据已清理。

## 练习与完成标准

### 跟做：数监督位置

打印 `(labels != -100).sum().item()`。提示：比较产生布尔张量，sum统计True，item取Python数字。完成标准是结果4，并能说出EOS为什么也计入。

> [!example]- 参考答案与解析
> 结果4，分别预测tag、=、R、EOS。若只有3，通常漏了结束标记；若9，通常没有屏蔽提示。

### 独立：构造ShareGPT风格记录

用conversations、from/value字段改写同一个样本。完成标准是归一化结果与原始instruction格式完全相等，来源仍为item-00。

> [!example]- 参考答案与解析
> conversations含 `{"from": "human", "value": "route red item 0 answer :"}` 和 `{"from": "gpt", "value": "tag = R"}`；外层还保留source_group。输入不同格式不会改变监督语义。本例拒绝多轮，不能据此声称已经处理了完整ShareGPT数据集。

### 迁移：真实对话如何决定监督范围

假设输入包含system、user、assistant三种角色，写出谁提供上下文、谁是本次监督答案。完成标准包括loss与attention的区分，以及先核对模型聊天模板。

> [!example]- 参考答案与解析
> system与user可作为上下文；本次指定assistant内容为监督答案。先使用目标模型匹配的聊天模板标记角色与结束位置，再生成监督mask。多轮中是否监督所有assistant轮次是数据方案选择，不能简单假定“最后N个字符就是答案”。
""",
    )

if __name__ == "__main__":
    lesson(
        1,
        r"""
## 本讲要解决的问题与前置

同一个工单改写成四种提问，如果其中三条进入训练、一条进入测试，可能测到记忆而非泛化。本讲按来源组切分，并解释padding、packing的边界。前置是上一讲的prompt、answer、labels；先不要优化速度。

阅读顺序：看320条如何生成 → 检查来源隔离 → 看补齐 → 思考拼接的注意力 → 做练习。源码仍是 `data.py` 的 `make_records`、`split_records`、`make_batch`。

## 概念与直觉：按原始来源分组

每个item是一个虚构来源组。每组包含red/blue两色与route/classify两种任务，共4条。80组产生320条：00～49为训练，50～64为验证，65～79为测试；分别200、60、60条。

训练集用于更新权重；验证集用于选rank等方案；测试集保留到方案固定后作一次报告。本例组ID在测试中没出现过，但颜色和输出规则都出现过，因此是有限的组合迁移，不是跨行业、跨语言或真实复杂推理。

“抽屉”类比：同一来源的改写放进同一个抽屉，分配的是抽屉。实际机制是记录source_group并验证集合交集为空；类比不意味着不同抽屉内容一定独立，真实来源之间仍可能复制文本。

## 最小示例与操作

在VS Code的示例工程新建 `lesson_02.py`：

```python
from data import make_records, split_records

splits = split_records(make_records())
for name, rows in splits.items():
    groups = {row["source_group"] for row in rows}
    print(name, len(rows), len(groups))
train_groups = {row["source_group"] for row in splits["train"]}
test_groups = {row["source_group"] for row in splits["test"]}
print("训练测试交集：", train_groups & test_groups)
```

在工程终端运行 `& ..\..\..\.venv\Scripts\python.exe lesson_02.py`。预期依次为 `train 200 50`、`validation 60 15`、`test 60 15`，交集 `set()`。集合推导式逐条取来源名并自动去重；`&`在这里是集合交集，和PowerShell执行符属于不同语言。

## 逐步讲解与数据审计

`split_records`先归一化，再用prompt的tuple检查完全相同的输入。tuple是不可变序列，可放进集合查重。接着解析item编号，验证必须是item-00至item-79，再按照固定编号分配。最后检查三个集合非空及来源组互斥。

这不是普遍适用的“按ID越小越早”规则，只是可解释的合成实验协议。真实时间序列应按时间防止未来信息泄漏；真实用户数据可按用户隔离；选择依据来自生成过程，不是看哪种切分得分高。

`dataset_digest`把规范化序列化后的原始记录做SHA-256，报告中保存摘要。它用于发现本次数据是否改变，不证明数据真实、正确或获得授权。修改输出一字符也应产生不同摘要。

## Padding与packing：省空间不等于语义正确

padding是在一行末尾补PAD，使矩形批次能放进张量。本例每条独立成行，右补齐，监督位置按真实答案保留，补齐标签-100。

packing是把多条短样本装进一条长序列，减少补齐浪费。假设A长度6、B长度4，简单拼成长度10；如果只用普通因果注意力，B能看见A内容。这可能是设计允许的串联预训练，也可能违反要求的独立指令隔离。EOS表示文本边界，但不会自动阻止注意力跨样本。

若要求隔离，需让位置满足“两者在同一来源段、且key不在query之后”才能可见：`same_segment and key_position <= query_position`。同时每段重建监督mask、处理位置编号与结束标记，并确认训练库真正支持这些语义。本例不启用packing，因此没有把这种优化写成已实现功能。

在纸上画4×4可见表：前2位置是A，后2位置是B。普通下三角允许B看A；隔离后的两块2×2下三角只允许各自段内。先能解释表，再学习框架packing选项。[TRL官方SFT文档](https://huggingface.co/docs/trl/en/sft_trainer)可作为后续接入参考；本工程未安装或运行TRL。

## 动手操作与预期结果

把一条记录复制到原列表末尾，再调用切分，应报“重复输入需先清理”。然后撤销复制。修改item-00为item--1应报来源范围错误；恢复后重新运行必须回到200/60/60。

常见错误：把验证集和测试集合并调参；只检查行数不检查来源；把EOS当注意力屏障；修改记录却沿用旧报告摘要。排查从来源清单与划分规则开始，不能靠随机种子掩盖泄漏。

## 练习与完成标准

### 跟做：解释320条

不看源码写出乘法。完成标准是说明每个因子的业务含义。

> [!example]- 参考答案与解析
> 80个来源组×2种颜色×2种任务=320。训练50组×4=200。每组都在同一集合，不是将320行独立随机分配。

### 独立：写一个切分审计清单

至少包括重复、来源交集、集合大小、答案监督、数据摘要。完成标准是对每项写出检查失败时怎样处理。

> [!example]- 参考答案与解析
> 重复先核对来源与标签冲突；交集不空重做按组分配；空集合调整合法划分；监督为空修正mask；摘要改变重新生成相应报告。不能删除失败样本却保留原分母。

### 迁移：同一客户多个工单

你希望判断新客户表现，应按工单还是客户切分？完成标准是同时说出适用目标和剩余风险。

> [!example]- 参考答案与解析
> 按客户分组，更接近新客户目标；同一模板跨客户复制仍可能泄漏。若目标是老客户未来工单，则可按时间并保留客户相关统计边界。没有单一切分能替所有业务目标负责。
""",
    )

if __name__ == "__main__":
    lesson(
        2,
        r"""
## 本讲要解决的问题与前置

模型已经会一些基础任务，我们希望调整少量参数学习指定格式，而不是更新全部权重。本讲把LoRA写成一个小线性层，再接入Transformer。前置：上一讲的切分、[[../../05_数学概率与优化/00 数学概率优化学习地图|矩阵乘法与梯度]]、[[../../06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|参数与优化器]]。矩阵形状不熟时先复习，不需要现在掌握低秩证明。

快速顺序：先看线性层 → 看A/B形状 → 运行初始化比较 → 查看冻结 → 修改rank。本讲读 `model.py` 的LoRALinear与add_lora。

## 概念与直觉：只学习一个受限制的增量

线性层可写作 `y = x Wᵀ`，这里PyTorch的权重W形状是 `[输出维度, 输入维度]`。LoRA把更新写成 `ΔW = (alpha / rank) B A`，A形状 `[rank, 输入维度]`，B形状 `[输出维度, rank]`。计算时先把x投影到rank维，再投影回输出维；原W冻结，只训练A和B。

rank是中间维度，限制增量矩阵最多有多少独立方向；它不是“模型等级”或准确率。alpha控制增量缩放。本例选择alpha等于rank，缩放恒为1，使rank2与rank8比较时不同时改变缩放。真实项目可分别调这两个参数，但需记录方案。

dropout是训练时随机把部分分支输入设为0、缩放保留值的正则化方法，用来降低对局部模式的依赖。本实验默认为0，恢复训练测试用0.2检查随机状态；它不保证消除过拟合。target modules表示注入适配器的层，本例选q_proj、v_proj、lm_head，分别影响注意力查询、值表示和最终词表分数。

“小补丁”类比帮助记住基础权重不动，但实际增量是矩阵乘积，训练仍需前向、反向和保存激活；不是修改几句提示词。[LoRA原论文](https://arxiv.org/abs/2106.09685)说明了这种低秩参数化方法。

## 最小示例：为什么初始输出完全相同

VS Code工程内新建 `lesson_03.py`：

```python
import torch
from torch import nn
from model import LoRALinear

torch.manual_seed(1)
base = nn.Linear(3, 2, bias=False)
adapted = LoRALinear(base, rank=1, alpha=1).eval()
inputs = torch.tensor([[1.0, 2.0, 3.0]])
print("A形状：", tuple(adapted.lora_a.shape))
print("B形状：", tuple(adapted.lora_b.shape))
with torch.no_grad():
    print("初始差值：", (base(inputs) - adapted(inputs)).abs().max().item())
print("Base可训练：", base.weight.requires_grad)
```

工程终端执行 `& ..\..\..\.venv\Scripts\python.exe lesson_03.py`。预期A为 `(1, 3)`，B为 `(2, 1)`，差值0.0，Base可训练False。

## 逐步讲解与接入顺序

`nn.Linear(3,2,bias=False)`输入3个数输出2个数，不使用额外偏置。A随机初始化，B全零，因此初始BA全零，输出等于Base。不能把A、B都设零：那会使两个因子的首步梯度都被另一因子的零阻断。

`eval()`关闭dropout训练行为；`no_grad()`只关闭这段比较的梯度记录，它们用途不同。`requires_grad=False`才明确冻结Base。执行 `add_lora` 时先冻结全模型，然后替换目标层，新的A/B默认可训练；优化器只接收这些可训练参数。

微型模型原始15008个参数。rank2新增508个，rank8新增2032个；总参数分别15516和17040。少量训练参数不代表Base不占内存，因为前向仍必须读取它。模型没有真实预训练语言知识，没有下载权重。

计算508的过程：两个32→32层各有 `2×(32+32)=128` 个增量参数，32→94词表头有 `2×(32+94)=252` 个；128+128+252=508。rank8按相同公式是2032。这里还没有优化器状态、梯度或激活内存。

## 动手：看到真正发生更新的参数

在工程README的CPU实验命令运行完后，读 `training.py`：优化器接收 `[parameter for parameter in model.parameters() if parameter.requires_grad]`。这个筛选逐个保留允许训练的参数，不为冻结权重维护AdamW状态。独立查看 `named_parameters()` 的名称与requires_grad：只有lora_a、lora_b应为True。

先不要为了“更多层更强”把embedding加入targets。本工程只支持已列出的三个线性层，错误名称会拒绝；真实模型的模块路径需要自己检查，不能套用另一个架构的名字。

## 常见错误与排查

- rank为0或超过层维度：检查正整数和最小输入输出维度，本例拒绝。
- 输出一开始就变了：检查B是否为零、dropout与模式、是否意外改了Base；同一输入在eval下比较。
- Base也更新：检查requires_grad及优化器参数列表，不能只相信文件名叫lora。
- 重复注入：不要在同一模型连续调用add_lora；从原始Base复制开始。
- CPU/GPU混用：模型和输入需放同一设备；适配器初始化继承Base设备和dtype。

## 练习与完成标准

### 跟做：计算参数数目

计算3→2层rank1新增多少参数。完成标准是区分原W与新增A/B。

> [!example]- 参考答案与解析
> 原W有2×3=6个；A有1×3=3个，B有2×1=2个，新增5个。若带偏置，Base偏置也保留，但本例不训练它。

### 独立：解释alpha=8、rank=2

写出增量缩放，并说明能否断言质量更高。

> [!example]- 参考答案与解析
> 缩放4。相同A/B时增量扩大4倍，但优化动态也改变，可能不稳定，不能从缩放直接推导质量。需同数据、固定评估协议比较。

### 迁移：只改lm_head会怎样

不用运行，先写假设、对照与判断指标。完成标准含“尚未测量”的标记。

> [!example]- 参考答案与解析
> 假设格式任务只改输出头已足够；与固定rank的q/v/head配置比较，保持训练数据、更新数和种子规则，记录验证质量、loss、参数量和耗时。结果未运行前不能写成有效结论。
""",
    )

if __name__ == "__main__":
    lesson(
        3,
        r"""
## 本讲要解决的问题与前置

这一讲亲自运行微调，理解设备、精度、梯度累积及恢复。前置是第3讲冻结参数和 [[../../06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|训练闭环]]；PyTorch基本顺序仍是train→清梯度→前向→损失→反向→更新。新概念按下面顺序加入，不需要先安装训练框架。

## 第一步：确认共享环境

在VS Code打开本单元示例工程，终端当前目录必须为该工程。执行：

```powershell
& ..\..\..\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

CUDA是NVIDIA GPU计算平台。本次作者环境torch2.14.0+cu130，CUDA可用，RTX5070Laptop约7.93GiB；你的输出可不同。CPU环境可以完成机制学习，不因False就学习失败；要跑本讲GPU路径需兼容GPU及对应PyTorch。不要为了这一讲自行升级驱动或替换共享依赖，先记录原因和明确安装方案。

## 第二步：先完成CPU全流程

```powershell
& ..\..\..\.venv\Scripts\python.exe train.py --device cpu --precision fp32 --output-dir report-my-cpu-01
```

`--device cpu`明确使用CPU；fp32表示32位浮点计算；output-dir是从当前工程起算的结果目录。必须使用新目录，已有目录会报FileExistsError，保留旧实验并换新名字。训练200次Base更新、每组LoRA250次更新，种子与数据摘要写入report.json。完整结果在终端打印，权重与状态另存文件。

运行时先训练复制颜色任务的Base，再冻结它分别训练rank2、rank8。生成式评估从提示开始逐个预测，不把正确答案偷偷作为生成输入。作者结果是Base0/60、两组60/60；这是合成规则任务，不保证跨设备字节一致或真实业务同样提升。

## 梯度累积、warmup与裁剪

微批次是一次前向/反向的少量样本。本例每微批最多16条，积累2个微批再更新一次，一般有效批量32，但最后批只有8条时并非每次都32。不能把更新数与样本数混为一谈。

累积按有效监督token加权：若两个微批分别有8和4个答案token，合并损失应为 `(loss_sum_1 + loss_sum_2)/12`，不能各平均后简单除2。源码把各自损失和除以本组总token数，再反向累积。

warmup是前期逐步增加学习率：第1次尝试0.002，第10次0.02，此后保持0.02。这里没有学习率下降调度器；恢复时需要全局attempt编号才能继续同一计算。裁剪将训练参数梯度的整体范数限制为1，降低巨大更新风险；它不能修复错误标签或非有限loss。

## 第三步：真实GPU路径

确认CUDA True后运行新目录：

```powershell
& ..\..\..\.venv\Scripts\python.exe train.py --device cuda --precision bf16 --output-dir report-my-cuda-01
```

BF16和FP16都使用16位浮点，但指数与有效精度分配不同；硬件支持需检查。本例BF16使用autocast自动选择适合低精度的运算，参数仍以FP32保存。CPU低精度路径明确不支持，不能用这个限制推断所有PyTorch CPU都不能低精度。

FP16可用 `--precision fp16` 单独实验。它还启用GradScaler，把loss放大后反向，再在裁剪前unscale，降低过小梯度下溢风险。顺序是scale/backward→unscale一次→clip→scaler.step→update。某次非有限梯度可使scaler跳过更新；history的applied记录是否真正执行。attempt计数是尝试数，不能全部叫成功更新。BF16不使用该scaler。

小模型GPU可能更慢：作者CPU两组各约1.1秒，GPU BF16各约3.2秒，模型太小，设备调度开销明显。这只是这一次训练循环墙钟，不是大型模型吞吐排名。计时前后CUDA同步，避免只计发出操作的时间。[PyTorch2.14 AMP示例](https://docs.pytorch.org/docs/2.14/notes/amp_examples.html)是本例接口依据。

## 检查点与恢复的最小示例

在新建 `lesson_04.py` 中粘贴下面的可运行CPU示例。它在自己创建的临时目录保存训练状态，运行结束清理该目录：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import torch
from checkpoint import save_training_state, load_training_state
from data import TOKENS, make_batch, make_records, split_records
from model import TinyLM, add_lora
from training import train_updates

device = torch.device("cpu")
model = add_lora(TinyLM(len(TOKENS)), rank=2)
optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad])
batches = [make_batch(split_records(make_records())["train"][:4], device)]
first = train_updates(model, batches, optimizer, 2, device)
config = {"device": "cpu", "batch_order": "fixed", "accumulation": 2}
with TemporaryDirectory(dir=Path.cwd()) as folder:
    path = Path(folder) / "state.pt"
    save_training_state(path, model, optimizer, first["scaler"], 2, config)
    start = load_training_state(path, model, optimizer, first["scaler"], config)
    second = train_updates(model, batches, optimizer, 2, device,
                           start_attempt=start, scaler=first["scaler"])
    print("最后尝试编号：", second["history"][-1]["attempt"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_04.py`，预期最后编号4。状态包含模型、优化器、scaler、已完成attempt、配置、CPU/CUDA随机状态；只能在一次完整累积与更新尝试后保存。本例批次固定循环，attempt也决定数据位置；使用随机DataLoader时还需保存采样器/数据顺序等额外状态。

这段示例验证能恢复并继续编号；“4次连续=2次保存+2次恢复”的等价由tests中的独立模型测试验证，包含dropout和优化器状态。只声称本机同环境CPU测试精确一致，不声称跨GPU、版本或分布式训练等价。

## 常见错误与练习

CUDA不可用：检查当前共享解释器和torch版本，再明确用CPU或提交安装方案。OOM是显存不足，先降低微批和序列长度、检查遗留模型；不要用empty_cache假装释放仍被引用的张量。loss非有限：停止，检查数据、学习率、精度和梯度，不吞掉异常继续写成功。

### 跟做：看学习率

打开report.json的history，查第1与10次lr。完成标准是0.002和0.02，并说明这是本例选择，不是通用最佳值。

> [!example]- 参考答案与解析
> lr=0.02×min(attempt/10,1)。恢复时从已完成2开始，下一条编号3使用0.006，而不是重新从0.002开始。

### 独立：恢复遗漏会怎样

分别解释遗漏优化器、随机状态、数据位置的风险。

> [!example]- 参考答案与解析
> AdamW历史动量不同；dropout后续掩码不同；批次顺序不同。即使当前权重相同，后续轨迹也会不同。只保存模型权重用于推理不能支持等价恢复声明。

### 迁移：累积组大小不同

两个微批有4和12个监督token，平均loss分别2和1，求合并平均。

> [!example]- 参考答案与解析
> (4×2+12×1)/16=1.25，不是1.5。按token总数加权才能匹配合并批次监督目标。
""",
    )

if __name__ == "__main__":
    lesson(
        4,
        r"""
## 本讲要解决的问题与前置

loss下降不等于完成任务；新任务变好也不等于所有能力都保留。前置是上一讲已运行CPU流程，结果目录中有report.json；未运行时先完成第4讲，不把作者数字当自己的结果。

快速顺序：确认实验身份 → 看验证选择 → 看测试分母 → 查看失败 → 看旧任务 → 判断过拟合。读 `train.py` 的run_experiment和 `training.py` 的两种评估。

## 两种指标测的是不同问题

答案token平均交叉熵是模型给正确下一token的概率所对应的误差，越低通常越好。evaluate_loss输入包含答案前缀，每位置预测下一token，这是teacher forcing，中文可理解为“训练式逐步提示”。它不是自由生成质量。

完整回答通过数要求模型仅收到6个提示token，自己生成 `tag = R/B` 并预测EOS；四个token全部正确才通过。predict不能读取预期答案。一个模型可能颜色预测正确却缺少tag，仍然不通过，因为本次任务包含格式要求。Base0/60因此不能被说成“完全不懂颜色”。

## 最小示例：读取你的报告

工程内新建 `lesson_05.py`，如果你用了不同目录名，改第一处路径：

```python
import json
from pathlib import Path

report = json.loads(Path("report-my-cpu-01/report.json").read_text(encoding="utf-8"))
print("范围：", report["scope"])
print("划分：", report["split_counts"])
print("Base测试：", report["base"]["test"]["passed"], "/", report["base"]["test"]["n"])
for variant in report["variants"]:
    print("rank：", variant["rank"], "训练loss：", variant["train_loss"],
          "验证loss：", variant["validation_loss"],
          "测试通过：", variant["test"]["passed"],
          "旧任务：", variant["copy_retention"]["passed"])
print("验证选择rank：", report["selected_rank"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`。scope应为合成微型因果模型，划分200/60/60。每组测试n必须是60；缺少报告先回第4讲，不能使用空字典默认0来隐藏未运行。

## 逐步比较：先验证，再测试

1. rank2和8以及三个targets在实验开始前固定，数据、批次规则、250次训练尝试和学习率规则保持一致。
2. 两组先在验证集比较完整回答通过数，再比较验证loss；若仍相同，选较小rank。这是本例明确的选择规则，不是某个库的强制要求。
3. 选择完成后才读测试集报告。脚本报告两组预先定义方案的测试结果，但不得看测试后再改rank、学习率和更新次数并沿用同一测试集声称独立评估。
4. 作者CPU结果：两组训练200/200、验证60/60、测试60/60；rank2验证loss约0.1524、rank8约0.000216，所以按上述规则选择rank8。它们测试任务质量相同，不能说rank8的测试准确率更高。

“0/60→60/60”表示该固定合成保留集完整格式任务改善100个百分点。它不是60位真实用户，也不是商业语言模型能力提升。时间、参数、精度与摘要必须和数字一起保存。

## 查看失败Case及旧任务回归

打开 `base.test.details` 找passed为false的记录，整数预测通过data.TOKENS查回字符串。写清期望、实际和失败类别。本例Base主要仍生成旧复制输出，未满足新格式；不是检索资料不足或工具权限故障。

选择方案若测试全部通过，也要如实记录“这个保留集未发现失败”，不要凭空编造失败率。扩展测试必须另建数据方案，例如新颜色、长输入、未知token或新输出格式，并注明哪些超出固定词表范围；输入被预处理拒绝与模型生成失败应分开。

report还记录copy_retention：对原 `copy` 提示是否仍输出颜色加EOS。若原任务回退，就不能把新适配器替换所有任务的默认模型。可以限定新格式入口使用适配器，保留Base服务旧任务，或设计混合训练数据并重新评估。

数据配比就是训练中不同任务/类别占多少。本例红蓝、route/classify各占一半，LoRA训练仅含新格式，没有混合旧复制任务。增加旧任务比例是一个新的实验变量，不能保证必然兼顾；先用验证集选配比，再留新测试报告。

## 过拟合、显存与耗时怎么写

过拟合指训练样本表现好、未见样本明显差。比较train_loss、validation_loss及两集合的自由生成质量；本例两者接近，未在这份简单规则任务发现明显差距，但不能据此证明没有过拟合任何真实语言能力。

cuda_peak_allocated_bytes是CUDA训练阶段PyTorch记录的已分配张量峰值，包括常驻Base和当前适配器，不是任务管理器的显卡总占用，也不是理论最低显存。CPU报告为null，表示没测，而不是0。两组约64.6MiB，不能用它估计一个7B模型只需64MiB。

training_seconds只包含该训练循环，排除导入、数据准备和大部分评估保存；GPU同步确保计算结束。一次测量不能给统计稳定的性能排名，重复实验时用新输出目录并保留环境和长度。

## 常见错误与练习

只贴最后loss：补生成指标及样本量。拿测试集挑方案：重新建立独立保留集，标记旧集已参与选择。把null显存写0：改为未测。只报新任务、不报旧任务：加回归对照，不隐藏退化。

### 跟做：找一个Base失败

用TOKENS将expected/predicted转回文本，写一句原因。完成标准是能对应同一个prompt和真实报告条目。

> [!example]- 参考答案与解析
> 具体预测以自己report为准；若预测red EOS而期望tag = R EOS，说明旧复制能力未遵守新格式。不能仅根据标签0就声称颜色识别失败。

### 独立：rank8是否“全面优于”rank2

至少比较任务质量、loss、可训练参数与时间。

> [!example]- 参考答案与解析
> 固定测试质量均60/60，rank8验证loss更低但可训练参数2032而rank2为508；时间需看实际报告。选择取决于预先约定目标，没有全面优于的证据。

### 迁移：业务只需要输出合法格式

还有哪些方案应先比较？完成标准是不把微调作为唯一解。

> [!example]- 参考答案与解析
> 可比较提示模板、结构化输出校验、确定性后处理或规则映射，并衡量成本及失败边界。本例颜色映射本就能规则解决；训练的用途是学习机制，不证明需要微调才能完成该业务。
""",
    )

if __name__ == "__main__":
    lesson(
        5,
        r"""
## 本讲要解决的问题与前置

训练结束后怎样让别人复现推理，怎样决定是否保留方案？前置是第5讲报告对照，清楚Base与LoRA版本。本讲读checkpoint.py、inference.py，完成可复现交接，不默认已经会模型发布。

## 三类文件各有用途

Base权重包含原始模型参数和词表；推理适配器只存A/B、rank、targets、dropout和对应Base摘要；完整训练状态还包含优化器、scaler、attempt、随机状态、配置，用于恢复训练。文件小不表示独立可运行，适配器需要匹配的Base和模型结构。

`state_digest`按参数名称、dtype、形状及内容计算摘要。加载时验证实际Base摘要与适配器绑定值；不能拿另一次训练的Base搭配旧适配器。摘要检测匹配关系，不证明文件来源可信；仅加载自己可信生成的文件，weights_only也不等于任意外来文件都安全。

## 最小操作：不重训就运行推理

在示例工程终端运行（目录名与你第4讲一致）：

```powershell
& ..\..\..\.venv\Scripts\python.exe inference.py --base report-my-cpu-01/base.pt --adapter report-my-cpu-01/adapter-rank-8.pt --prompt "route red item 70 answer :"
& ..\..\..\.venv\Scripts\python.exe inference.py --base report-my-cpu-01/base.pt --adapter report-my-cpu-01/adapter-rank-8.pt --prompt "classify blue item 70 answer :" --merged
```

预期分别 `tag = R`、`tag = B`。prompt引号把有空格的文本作为一个参数；merged标记把适配器增量合入普通线性层再推理。只支持6个固定词表token；输入自然中文会报未知token，不能作为聊天机器人使用。

## 逐步讲解：合并为什么要eval

不合并时 `xWᵀ + (alpha/r)xAᵀBᵀ`；合并后权重 `W + (alpha/r)BA`，一次普通线性变换。浮点运算顺序不同，会有微小数值误差，应比较容差内logits和任务输出，而不是要求每个字节完全一样。

训练模式dropout是随机分支，不能合入固定矩阵。本工程要求eval后合并，并返回模型副本，不破坏原Base。报告保留reload_max_abs_error和merge_max_abs_error，并执行容差断言。作者CPU重新加载差值0，合并最大差值约1.2×10⁻⁵；对应测试验证数值接近。

[PEFT LoRA参考](https://huggingface.co/docs/peft/v0.21.0/package_reference/lora)介绍了框架中的适配器与合并选项；本例是手写机制实现，未安装PEFT、Transformers或TRL，不能把这里的pt文件直接当成它们的模型格式。

## 全参训练与LoRA显存构成

全参训练需保存权重、梯度、优化器状态、前向激活、算子临时空间。FP32权重P个参数约4P字节，梯度常约4P，Adam的一阶与二阶状态各约4P，总共约16P，但未含激活、缓冲和可能的主权重副本。这是简化估算，不是每种训练器的精确公式。

例如15008个FP32参数仅权重约60032字节；微型训练实测CUDA峰值仍远大于它，因为激活、库工作区和常驻对象也占内存。真实大模型激活随批量、序列长度、层数及实现改变，不能只看参数量。LoRA减少可训练梯度/优化器状态，却仍保留Base和必要反向路径的激活。

稳定性检查顺序：输入/labels合法 → loss和梯度有限 → 设备精度匹配 → 学习率与warmup合理 → 更新是否真正发生 → 验证与回归是否改善。量化、分布式、梯度检查点重计算留后续；不要同时引入以致无法定位问题。

## 动手交接：写一页采用判断

新建自己的实验说明，记录：问题、合成数据来源、200/60/60切分、SHA摘要、Base训练目标、rank/alpha/targets/dropout、种子/更新/精度、任务通过数、loss、旧任务、内存与时间、未测范围、采用或拒绝理由。

若新格式改善但旧任务退化，仅允许新格式限定入口采用，不替换通用模型；保留Base回退和完整实验目录。若新任务也未改善，保留失败记录、停止部署，检查数据与目标是否适合微调，不只增加更新数。真实语言模型迁移需要重新选择可信模型、核对许可证、聊天模板、实际Tokenizer、数据授权及资源，并先给出安装/下载方案再获得批准；本单元没有执行这些环境变更。

## 常见错误与练习

找不到文件：检查工程当前目录和自己实验目录。Base不匹配：用同目录base.pt，不能删掉校验。合并报先eval：说明仍在训练模式，先关闭dropout再验证。推理权重能加载但无法等价续训：回到完整training-rank文件，核对配置和状态，不使用adapter冒充检查点。

### 跟做：比较合并前后输出

同一个blue提示分别不带和带merged运行。完成标准是两次都为tag = B，并记录命令、目录和模型版本。

> [!example]- 参考答案与解析
> 输出一致只验证此样本。数值接近由report中的探针和测试支持，不能从两行文本推断全输入域数学完全一致。

### 独立：写恢复文件清单

列出推理与恢复训练分别必须携带什么。

> [!example]- 参考答案与解析
> 推理携带Base、词表/结构、适配器配置与权重、摘要、运行命令；恢复再携带优化器/scaler/attempt/随机状态及相同数据顺序协议。真实工程还可能需要调度器、采样器和分布式状态。

### 迁移：为什么暂时不采用

假设新任务提升10个百分点、旧任务下降30个百分点，写有条件结论。

> [!example]- 参考答案与解析
> 不能替换原有全任务模型；可保留隔离的新任务试验，评估用户真实收益和风险，或用混合数据重新训练。若业务要求旧任务不退化，这次方案验收失败，报告提升和退化都要保留。

## 返回与后续

[[../参考工程验证记录|作者实验与限制]] · [[../示例工程/README|代码导航]]。下一单元规划：推理服务与性能工程，待编写。
""",
    )

if __name__ == "__main__":
    write(
        f"{MAP}.md",
        r"""
## 现在学哪一讲

打开 [[逐讲学习/01 整理指令数据并只监督答案|第1讲]]，在VS Code工程新建lesson_01.py，先确认答案的4个监督位置。完成判断：能解释提示参与计算但不计损失、EOS为什么监督、来源为什么分组，不以看完目录为完成。

## 六讲顺序

"""
        + "\n".join(
            f"{index + 1}. [[逐讲学习/{name}|{name}]]"
            for index, name in enumerate(LESSONS)
        )
        + r"""

## 前置与使用方式

需要Python列表/字典/函数、矩阵乘法、张量和完整训练闭环；不熟先返回 [[../06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|训练基础]]、[[../08_Transformer从零实现/00 Transformer 从零实现学习地图|因果小模型]]、[[../10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图|训练样本基础]]。

Obsidian阅读讲解，VS Code打开示例工程，使用根目录共享.venv。已有torch可运行CPU；GPU分支需CUDA实际可用。没有下载商业或开源预训练大模型，也不安装PEFT等新依赖。

## 会得到什么与边界

320条合成指令、按来源200/60/60切分、局部预训练Base、rank2/8LoRA对照、真实CPU/CUDA训练记录、推理适配器、完整状态恢复与合并验证。任务是固定词表颜色格式输出，不能作为真实语言能力或业务提升证明。另测原复制任务，防止只报新任务。

[[示例工程/README|源码与命令]] · [[参考工程验证记录|作者验证]] · [[../../00 从这里开始|学习首页]]。个人操作与独立练习写入学习记录，不自动勾选。

下一单元规划：推理服务与性能工程，待编写。
""",
    )

if __name__ == "__main__":
    write(
        "示例工程/README.md",
        r"""
## 先运行

在VS Code打开本目录，PowerShell使用工作区共享解释器，不创建单元虚拟环境：

```powershell
& ..\..\..\.venv\Scripts\python.exe train.py --device cpu --output-dir report-my-cpu-01
& ..\..\..\.venv\Scripts\python.exe inference.py --base report-my-cpu-01/base.pt --adapter report-my-cpu-01/adapter-rank-8.pt
```

需已有PyTorch。本机作者Python3.13.12、torch2.14.0+cu130，CUDA可用。缺包先核对共享环境并提出安装方案，不擅自运行pip。数据全部合成，模型自己预训练，没有联网、外部权重或用户数据。输出目录必须为新目录，不覆盖。报告任务范围为固定词表，并记录作者与学习者不同角色。

GPU可用时：

```powershell
& ..\..\..\.venv\Scripts\python.exe train.py --device cuda --precision bf16 --output-dir report-my-gpu-01
```

fp16替换precision另建目录；CPU明确fp32。完整步骤、预期与排错见 [[../逐讲学习/04 运行CPU和GPU训练并恢复状态|第4讲]]。

## 代码导航

- [data.py](./data.py)：三种单轮格式归一化、320条合成记录、来源切分、答案监督mask、词表摘要。
- [model.py](./model.py)：单块因果Transformer、LoRA低秩层、冻结与合并。
- [training.py](./training.py)：token加权累积、warmup、AMP、裁剪、loss与自由生成评估。
- [checkpoint.py](./checkpoint.py)：Base摘要、推理适配器与完整训练状态分开保存。
- [train.py](./train.py)：CPU/GPU实验入口，先验证选择再读测试，旧复制任务回归。
- [inference.py](./inference.py)：加载可信Base与适配器，可选合并，固定提示推理。
- [test_sft.py](./tests/test_sft.py)：数据边界、因果、冻结、累积、CPU精确恢复及GPU三种精度。
- [requirements.txt](./requirements.txt)：本工程最小依赖说明；共享约束以工作区清单为准。

## 报告与验证

新结果目录包含base.pt、adapter-rank-2/8.pt、training-rank-2/8.pt、report.json。摘要匹配才能加载适配器；仅加载自己可信文件。report记下loss、任务通过、训练时间、CUDA已分配张量峰值、旧任务及未测范围。

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

无GPU时GPU测试明确skip，不称运行通过。作者当前GPU路径已执行；具体记录见 [[../参考工程验证记录|验证记录]]。本例未实现packing、通用多轮chat模板、真实预训练模型微调、分布式或通用量化。
""",
        "SFT与LoRA示例工程代码导航",
    )

if __name__ == "__main__":
    print("已写入单元26六讲、地图与代码导航")
