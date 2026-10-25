"""编写小模型实际DPO教材；生成器导入不写文件。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/33_DPO与偏好优化"
MAP = "00 DPO与偏好优化学习地图"
LESSONS = [
    "01 构造同一问题的chosen与rejected偏好",
    "02 计算回答概率并只统计completion",
    "03 用冻结参考与beta读懂DPO损失",
    "04 从SFT权重启动CPU与GPU的DPO",
    "05 比较BaseSFT与DPO并分析长度偏差",
    "06 分清SFTPPO与DPO并写采用结论",
]


def write(name, body, title=None):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    heading = title or path.stem
    path.write_text(
        f"---\ntitle: {heading}\ntags: [learning, dpo, preference]\nupdated: 2026-10-12\n---\n\n# {heading}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(index, body):
    previous = (
        f"[[{LESSONS[index - 1]}|上一讲]]"
        if index
        else "[[../../32_推理时策略/00 推理时策略学习地图|前一单元]]"
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

SFT教模型模仿一个回答；如果同一问题有两个回答，我们想表达“更喜欢哪一个”，怎样存数据？本讲先定义偏好方向及依据，不把更喜欢自动等同于事实正确。

前置是 [[../../26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图|SFT与回答监督]]、[[../../31_推理与工具数据构造/00 推理与工具数据构造学习地图|数据来源与隔离]] 和Python列表/字典。陌生语法沿单元01详细讲解复习。当前运行不下载模型，全部问题与偏好都是合成规则。

## 三个核心字段

prompt是同一个问题或对话前缀，chosen是该问题下更偏好的回答，rejected是较不偏好的回答。两侧必须对应同一prompt；不能把不同问题的答案随机配对。[DPO原始论文](https://arxiv.org/abs/2305.18290)以这种成对偏好直接优化模型。

本例问题token为ask/red/item/id-00，意思是让模型回复这个合成对象的颜色。正确简短回答ok/red/EOS；正确较长回答ok/red/detail/detail/EOS。detail只是教学词，表示无额外事实的延伸，EOS表示回答结束。chosen偏简短，rejected仍可能事实正确，只是风格不合目标。

| 字段 | 作用 | 本例 |
| --- | --- | --- |
| prompt | 同一问题 | ask red item id-00 |
| chosen / rejected | 有方向的比较 | 正确短句 / 正确长句 |
| source_id | 来源组隔离 | source-00 |
| preference_origin | 记录偏好依据 | synthetic_brief_style_rule |
| usage_policy | 合成资料使用范围 | local_teaching_only |

None、平票、两者同样好时不应强行有方向标签。当前验证拒绝相同回答或空回答；真实任务还需要评审定义、审核人、理由与分歧处理。这里没有真实人类签署偏好，不能称“人类反馈数据集”。

## 最小示例与操作

VS Code打开 `01_学习指南/33_DPO与偏好优化/示例工程`，新建lesson_01.py：

```python
from data import make_pairs, validate_pair

pair = make_pairs("train")[0]
validate_pair(pair)
print(pair["prompt"])
print("chosen：", pair["chosen"])
print("rejected：", pair["rejected"])
biased = make_pairs("train", biased=True)[0]
print("故意错误偏好：", biased["chosen"], biased["preference_origin"])
```

保存后打开“终端→新建终端”，确认路径在示例工程；根目录进入可用 `Set-Location '01_学习指南/33_DPO与偏好优化/示例工程'`。运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe lesson_01.py
```

&执行指定程序，三个..回工作区根，共享.venv不另建。预期正常chosen是ok/red/EOS，rejected多两个detail；错误偏好chosen变ok/blue/EOS，并明确标deliberately_wrong_short_fixture。

## 为什么故意保留错误偏好对照

压力数据把“错误但短”排在“正确但长”前面，测试模型会不会顺着坏标签学坏。它不是可用训练数据推荐。validate_pair检查结构/来源/使用约定，并允许明确标注的故障夹具；验证通过不能证明偏好合理。

正常make_pairs默认biased=False。真实数据不能凭“较短”“较礼貌”“较自信”就标chosen，需要内容、约束与用户需求依据；已知错误应在正常数据审核中拒绝。故障数据只用于隔离实验，不能混入默认训练包。

## 切分与来源

36个来源组，每组red/blue两题。train24组48对、dev6组12对、test6组12对，整组隔离。来源ID不是模型的真实商品资料；词表45个固定token，中文解释不在模型词表中。

本实验是反复观察的固定诊断，非盲测或未触碰最终保留集。来源组不交叉仅证明这项隔离，不保证真实泛化；小模型也没有通用预训练知识。

## 常见错误与练习

方向反了会把模型推向不想要的回答；同样好时强选会增加噪声；同来源改写进不同集合会泄漏；把合成标签当真人审核会误导。先核对prompt、方向与理由，再谈训练。

### 跟做：chosen不等于唯一正确

完成标准是指出两条正常回答都给red，区别是风格长度，拒绝项不一定事实错。

> [!example]- 参考答案与解析
> rejected可以正确但不符合简短目标。DPO学相对偏好，不自动得知所有事实或用户目标。

### 独立：错误但简短

为什么结构验证通过仍不能加入正常数据？完成标准是区分格式合法、偏好依据与事实正确。

> [!example]- 参考答案与解析
> ok/blue/EOS结构合法，但问题是red；故障夹具明确允许研究坏标签。真实审核应拒绝，不能让长度替代事实。

### 迁移：真实人工偏好

列出至少四项审核记录。完成标准是评审准则、评审人/依据、分歧/平票处理、来源许可与隔离。

> [!example]- 参考答案与解析
> 保留同prompt两回答、真实评审及理由，平票不硬造方向，记录允许用途和修订，按来源/题族切分。本例使用约定不证明外部数据许可。
""",
    )
    lesson(
        1,
        r"""
## 本讲要解决的问题与前置

DPO需要比较两个回答的概率。概率怎样变成一个数？为什么问题和padding不能算进回答概率？前置 [[../../05_数学概率与优化/00 数学概率优化学习地图|对数与概率]]、[[../../06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|张量形状]]、[[../../26_SFT与LoRA全流程/逐讲学习/01 整理指令数据并只监督答案|回答掩码]]。

## completion、条件概率与对数

completion是prompt之后的完整回答。本例chosen三个token（ok、颜色、EOS），rejected五个token（多两个detail）。因果语言模型逐token预测：回答概率是每个回答token在问题与已知前缀下的条件概率乘积；取log后变为这些log概率相加。

例如三个token概率都0.5，序列概率0.125，log概率3×log(0.5)。log概率通常负数；-2比-4大，表示序列概率更高。log可以避免很多小数相乘下溢，不能把负号解释成负概率。

标准本例DPO用回答log概率的**和**，不默认按长度平均。平均是不同统计，不可随便替换目标；不同DPO变体也需明确，不把所有偏好损失称同一公式。

## 最小示例：均匀词表下只看长度

新建lesson_02.py：

```python
import torch
from data import TOKENS, batch_sequences, make_pairs
from objectives import sequence_logps

pair = make_pairs()[0]
inputs, labels = batch_sequences([pair["prompt"]] * 2,
                                 [pair["chosen"], pair["rejected"]])
logits = torch.zeros(*inputs.shape, len(TOKENS))
logps, counts = sequence_logps(logits, labels)
print("形状：", tuple(logits.shape), tuple(labels.shape))
print("回答token数：", counts.tolist())
print("log概率和：", logps.tolist())
print("每token平均：", (logps / counts).tolist())
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_02.py`。预期logits形状(2,9,45)、labels(2,9)，回答计数[3,5]，log概率和约[-11.41999,-19.03331]，平均两项都约-3.80666。浮点末位允许变化。

## 逐步讲解形状与位移

B=2是两条序列，T=9是最长prompt4+回答5，V=45是词表。短序列后面补pad。logits[B,T,V]在每个位置给下一token的分数，不是已经归一化的概率。

batch_sequences把prompt和padding的labels设-100，回答含EOS保留真实ID。sequence_logps使用logits[:, :-1]预测labels[:, 1:]：输入位置t预测下一个位置t+1。第一回答位于索引4，应由最后prompt位置索引3预测；不位移就会让模型“看着答案预测自己”。

log_softmax先把分数转为log概率，gather按目标ID取每个位置的值；无监督位置临时用安全ID0索引，再乘mask消除其贡献。每行至少有一个有效回答，超词表标签和空监督拒绝。

短回答较高概率在此来自长度，不说明内容更正确。这也是为什么只看chosen_raw_logp_wins会误导：Base还不会问答也可能喜欢短序列。DPO还要减去reference相对倾向，第3讲解释。

## 动手与常见错误

打印labels，确认前四位-100、EOS仍计数、短回答padding不计。把无监督位置logits任意改大，log概率和应不变；回答预测位置改变会变。练习只改自己的脚本，不改公共词表。

sum换mean并非小格式调整，会改变长短回答的目标。PAD和EOS用途不同：PAD只是补批次形状，EOS是结束，应纳入回答概率。标签屏蔽不等于把prompt从输入删除。

## 练习与答案

### 跟做：解释3与5

完成标准是指出含EOS、不含prompt/pad，并说明-11比-19表示更高序列概率。

> [!example]- 参考答案与解析
> 两回答3/5个token，均匀词表每token概率1/45，和为3或5倍log(1/45)。差异是长度造成，不是事实裁判。

### 独立：不位移会怎样

提示：看第一回答token已有输入。完成标准是说明预测目标错位和答案泄漏。

> [!example]- 参考答案与解析
> 同一位置输入已经有目标token，模型可能学复制自身而非下一token。正确为prompt末位预测首回答，回答末前位预测EOS。

### 迁移：真实Tokenizer

列出概率比较前的对齐条件。完成标准是同prompt、同模型词表/模板、completion边界、EOS/pad及截断规则。

> [!example]- 参考答案与解析
> 两侧用一致聊天模板和Tokenizer，核对回答边界与因果位移，不重复特殊token，不截掉一侧而保留另一侧。本固定词表ID不能给外部模型。
""",
    )
    lesson(
        2,
        r"""
## 本讲要解决的问题与前置

为什么DPO不只最大化chosen概率，还需要reference与beta？本讲从四个log概率构造损失并检查梯度方向。前置第2讲、梯度和 [[../../05_数学概率与优化/00 数学概率优化学习地图|sigmoid直觉]]。

## 冻结参考是比较起点

policy是正在训练的模型，reference是固定的SFT模型副本。reference不是每轮替换的policy，也不是一个单独训练的奖励模型。两者开始权重相同，后续只更新policy；参考关闭梯度和dropout状态变化。

令Pc/Pr为policy对chosen/rejected的回答log概率和，Rc/Rr为reference两项，定义Δ=(Pc-Pr)-(Rc-Rr)。Δ比较“policy更偏chosen的程度，相对SFT起点改变了多少”，不是最终事实正确性。

标准sigmoid DPO单对损失为：

$$
L=-\log\sigma(\beta\Delta),\quad \sigma(z)=\frac{1}{1+e^{-z}}
$$

批量取平均。[DPO论文](https://arxiv.org/abs/2305.18290)与 [TRL目标说明](https://huggingface.co/docs/trl/dpo_trainer)给出这一基于相对log概率的目标；本例手写标准形式，不安装TRL或其他变体。

## beta是什么、不是什么

beta为有限正数，缩放相对偏好margin，来源与参考约束的推导有关。固定Δ时beta更大让sigmoid变化更明显；训练后模型变化还受学习率、数据和更新次数影响，不能简单说“越大越远离reference”或“越大越好”。

这里不显式另加KL项；reference差值已在目标中。不能把beta当学习率：学习率控制每次参数更新步长，beta改变损失对相对概率的响应。

## 最小示例与操作

新建lesson_03.py：

```python
import torch
from objectives import dpo_loss

chosen = torch.tensor([-2.0], requires_grad=True)
rejected = torch.tensor([-4.0], requires_grad=True)
reference_chosen = torch.tensor([-2.0])
reference_rejected = torch.tensor([-4.0])
loss, margin = dpo_loss(chosen, rejected, reference_chosen, reference_rejected, 0.1)
loss.backward()
print("loss和margin：", round(loss.item(), 6), margin.item())
print("梯度方向：", chosen.grad.item() < 0, rejected.grad.item() > 0)
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_03.py`。预期loss≈0.693147、margin0，梯度方向True/True。policy/reference相同起点时Δ=0，任何正beta都有log(2)损失，并不是已经训练失败。

## 逐步解释梯度与稳定实现

这里chosen/rejected只是标量log概率代理，不是真实模型参数；requires_grad记录可求导关系，backward计算对它们的梯度。梯度下降减去梯度，所以chosen负梯度推动其上升，rejected正梯度推动其下降；真实模型各token共享参数，变化不保证独立。

dpo_loss用logsigmoid直接计算稳定log概率，不先sigmoid再log导致极值下溢。reference两项detach，保证本函数不回传参考梯度；真实训练还把整个reference.requires_grad设False，避免构建其计算图。

缓存reference概率仅在参考权重、数据/模板、精度和模式固定时合理。本例无dropout，reference固定，预先缓存两侧分数；换模型或数据后不能复用旧缓存。

## 为什么loss下降仍可能学坏

目标奖励相对偏好差，不保证chosen绝对概率一直上升，也不保证贪心生成一定输出chosen。模型可以大幅降低rejected，margin增大，但生成别的错误文本。用户标签错、长度倾向或过大更新会造成事实/旧任务退化；后两讲用实际结果检查。

## 练习与答案

### 跟做：初始0.693

完成标准是手算Δ=0、sigmoid(0)=0.5、-log(0.5)≈0.693，说明不是错误报错。

> [!example]- 参考答案与解析
> 相对SFT尚未改变，分类信号在中点。训练希望偏好方向改变，但初始损失本身不评价语义或事实。

### 独立：只更换reference

如果reference已经更偏chosen，policy没变，Δ会怎样？完成标准是比较两侧差值，而不是只看Pc。

> [!example]- 参考答案与解析
> Rc-Rr增大，Δ变小，表示policy相对新参考不足。随意更换参考改变目标，所以固定并记录其来源/权重版本。

### 迁移：缓存错误

数据模板变了却使用旧reference分数，为什么不可靠？完成标准是同序列/Tokenizer/边界条件必须一致。

> [!example]- 参考答案与解析
> 分数属于原序列，不能与新序列policy相减。重新计算并记录参考、模板和数据版本；不同长度或EOS也会影响和。
""",
    )
    lesson(
        3,
        r"""
## 本讲要解决的问题与前置

从SFT权重怎样开始实际DPO，怎样确认reference没有一起训练？本讲运行微型模型CPU/CUDA路径，不下载任何外部模型。前置前三讲及单元26的训练步骤和保存权重。

## 微型模型先解释清楚

TinyLanguageModel是Embedding→GRU→词表投影，共8133参数。Embedding把token ID变24维向量；GRU是循环神经网络单元，按顺序更新32维隐状态来汇总已经读过的前缀；Linear映射到45个词的分数。形状[B,T,24]→[B,T,32]→[B,T,45]。

它与Transformer结构不同，但都是本例的因果下一token模型，不读取未来。GRU帮助把示例缩小到本机可运行，不是现代通用LLM架构结论。本Base只用训练来源学copy颜色旧任务；SFT再学ask颜色的新格式，没有通用知识或外部预训练权重。

## 实际CPU运行

在VS Code本工程终端：

```powershell
& ..\..\..\.venv\Scripts\python.exe experiment.py --device cpu --output-dir report-my-cpu-01
```

--device选设备，--output-dir是新目录，相对当前工程。存在拒绝覆盖，换新名字。共享环境需已有PyTorch；若导入失败先核对根解释器及实际版本，依工作区规则提出安装方案并获批，不全局安装或另建单元环境。

执行顺序：固定seed2026 → Base学copy100更新并保存 → SFT学ask150更新并保存 → 从sft.pt重新加载 → 复制冻结参考 → 四组DPO → 固定诊断评估 → 保存报告。训练来源48对，dev/test各12对。

SFT短/长比例约1:3，而且固定索引规则造成颜色与风格相关，是教学数据偏差，不叫均衡真人偏好。完整实验可能首次导入较慢；微型训练几秒，不凭速度推断大模型资源需求。

## 四组对照及GPU

| 名称 | 数据 | beta | 学习率 | 更新 |
| --- | --- | --- | --- | --- |
| clean-beta-0.1 | 正确短胜正确长 | 0.1 | 0.001 | 80 |
| clean-beta-0.5 | 同上 | 0.5 | 0.001 | 80 |
| biased-short | 错误短胜正确长 | 0.1 | 0.001 | 200 |
| aggressive-clean | 正确短胜正确长 | 0.1 | 0.01 | 80 |

已有CUDA可另开新目录：

```powershell
& ..\..\..\.venv\Scripts\python.exe experiment.py --device cuda --output-dir report-my-gpu-01
```

本例CPU/CUDA均FP32，不引入AMP、LoRA、量化或分布式。作者本机RTX5070Laptop实际跑过两条路径，任务计数相同，log概率/耗时有数值差异；没有GPU时CPU足够完成本单元，不自动切设备或安装驱动。

## 最小检查：参考独立与冻结

新建lesson_04.py：

```python
from model import TinyLanguageModel
from training import make_reference

policy = TinyLanguageModel()
reference = make_reference(policy)
print("不同对象：", policy is not reference)
print("参考均冻结：", all(not p.requires_grad for p in reference.parameters()))
print("参考eval：", not reference.training)
print("参数量：", sum(p.numel() for p in policy.parameters()))
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_04.py`，预期True/True/True/8133。这是检查结构；完整训练报告还通过逐参数比较保证reference没变，测试保证其grad为None。

## 看training.py的明确顺序

policy.train，optimizer.zero_grad，计算policy两侧回答log概率，减冻结参考差，loss.backward，检查/裁剪有限梯度，optimizer.step。reference.eval并no_grad，缓存分数不进入训练图。梯度裁剪1是教学数值选择；不能吞掉非有限梯度继续写成功。

GPU复制GRU后调用flatten_parameters整理库所需权重布局；早期实验曾提示非连续权重，最终代码处理布局，没有把警告当数据失败或直接静默隐藏。它不改变模型数学参数。

## 保存文件的实际能力

base.pt、sft.pt和四组DPO的pt只含推理权重/词表。DPO从SFT快照开始**新阶段**，新建AdamW；不是恢复SFT优化器。没有完整优化器/RNG/训练轮次检查点，不能等价中断续训，报告resume_training_supported=False。只加载自己可信生成文件，不下载陌生pt。

## 练习与答案

### 跟做：定位SFT与reference

完成标准是找到sft.pt、load_weights与make_reference，解释为什么不能reference=policy。

> [!example]- 参考答案与解析
> 同对象会一起更新，比较基准不再固定。需独立副本、冻结和eval/no_grad，并验证权重/梯度，不能只靠变量名不同。

### 独立：推理权重能续训吗

列出当前pt缺少的状态。完成标准是不宣称等价恢复，指出优化器、随机状态与更新位置。

> [!example]- 参考答案与解析
> 可以以权重开始新训练，但不等价接回原训练轨迹；缺Adam状态、完成阶段/RNG等。当前明确不支持完整恢复。

### 迁移：真实大模型资源

为什么8133参数实验不能预测7B训练显存？完成标准是基座/参考、梯度/优化器、激活、序列/批量和精度都考虑。

> [!example]- 参考答案与解析
> DPO要计算两回答和参考，大模型成本受多因素控制；小模型几秒不证明真实任务便宜。先算资源与选方案，获批再安装/下载，不为跑通浪费资源。
""",
    )
    lesson(
        4,
        r"""
## 本讲要解决的问题与前置

偏好得分高就可以采用吗？本讲比较Base/SFT/DPO的固定生成与旧任务，明确长度偏差、坏标签和过优化。前置四讲、[[../../19_Agent评估体系/00 Agent 评估体系学习地图|固定评估与分母]]。

## 指标先定义

factual_correct在本固定任务中指生成前两词为ok/正确颜色且以EOS结束，是**窄颜色命中指标**，不检查全部自然语言语义。exact_brief要求整段恰为ok/正确颜色/EOS。old_copy_correct要求copy问题输出颜色/EOS。

chosen_raw_logp_wins是给定两回答在teacher forcing下的概率排序，和自由贪心生成不同；它不证明模型实际会输出chosen，更不证明回答正确。mean_raw_logp_gap为两序列log概率差，长度也会影响。

## 实际CPU结果（每行12个固定诊断题）

| 模型 | 颜色命中 | 正确且完全简短 | 旧copy | 给定正确短胜长 |
| --- | --- | --- | --- | --- |
| 本地Base | 0/12 | 0/12 | 12/12 | 12/12 |
| SFT | 12/12 | 2/12 | 3/12 | 2/12 |
| clean beta0.1 | 11/12 | 8/12 | 4/12 | 12/12 |
| clean beta0.5 | 12/12 | 6/12 | 4/12 | 8/12 |
| biased-short | 4/12 | 4/12 | 3/12 | 12/12 |
| aggressive-clean | 0/12 | 0/12 | 0/12 | 12/12 |

作者CUDA最终计数相同，但log概率与时间不完全一致，不声称跨设备字节级复现。来源分组隔离，但实验反复观察过这些固定题，所以不是盲测或严格未触碰最终测试，不能给统计泛化结论。

## 最小示例：读自己刚生成的报告

先完成第4讲CPU实验，再新建lesson_05.py：

```python
import json
from pathlib import Path

report = json.loads(Path("report-my-cpu-01/report.json").read_text(encoding="utf-8"))
for name in ("base", "sft"):
    item = report[name]
    print(name, item["factual_correct"], item["exact_brief"], item["old_copy_correct"])
for run in report["runs"]:
    item = run["test"]
    print(run["name"], item["factual_correct"], item["exact_brief"],
          item["old_copy_correct"], item["chosen_raw_logp_wins"])
print("参考未变：", report["reference_unchanged"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`。预期得到上表计数与参考True。若文件不存在，先跑自己的CPU实验；不假定你电脑提前有作者报告。修改实验参数后输出可不同，必须记录配置，不追着数字改数据。

## 三种偏差与实际失败

**长度倾向**：Base颜色命中0，但给定短回答胜长12。单看排序会误以为模型优秀；更短序列乘的概率项更少，原始概率不能替代任务检查。DPO减参考相对倾向也不能自动消除所有长度/标签偏差。

**坏事实偏好**：故障标签偏爱错误颜色的短句，biased-short颜色4/12，尽管偏好相关排序很好。模型跟随偏好不等于学到正确事实。换回正常测试对仍见退化；故障对评估仅检查它是否跟随坏标签，不能叫任务质量。

**过优化**：学习率0.01的aggressive-clean把给定短对数差推很大，却贪心输出red重复至8token上限或异常结束，颜色0/12。不能用loss下降/分数提高替代生成验收。较小学习率也仍有11/12的错误和旧任务不全恢复。

## 旧任务与采用范围

SFT本身copy从12降3，DPO最多4，并未保住Base旧能力。若业务要求copy不退化，整个SFT/DPO替换方案都不通过。若只研究ask新格式，可保留隔离的小实验与Base回退，但这不是生产收益或真实偏好验证。

dev结果与test固定诊断都保留，不能因某个beta在小test上好就称通用最佳。后续真实实验应先用dev选配置，再在没反复看的保留集/盲评验收；人工评审应隐藏模型标签、明确规则并记录分歧。

## 练习与答案

### 跟做：排序12/12而事实0/12

完成标准是解释Base和aggressive两个反例，指出给定回答概率与实际生成不同。

> [!example]- 参考答案与解析
> Base受短序列概率倾向影响；aggressive通过降低较长回答等方式扩大相对差，却生成异常文本。排序指标不是生成任务正确率。

### 独立：beta0.5可以替换Base吗

提示：看旧copy。完成标准是12/12新颜色不等于全任务保持，并写采用条件。

> [!example]- 参考答案与解析
> copy只有4/12，低于Base12/12，不能全替换。仅可保留隔离ask任务研究，真实泛化与利益未验证。

### 迁移：真实偏好盲评

提出独立任务、标注标准和泄漏控制。完成标准是隐藏模型名、保存失败/分歧、评估事实与风格及旧能力。

> [!example]- 参考答案与解析
> 固定未用于调参的题，随机隐藏候选来源，明确事实/约束/风格评分，记录审核及分歧，做旧任务回归。不能只看chosen训练准确或同生成模型自评。
""",
    )
    lesson(
        5,
        r"""
## 本讲要解决的问题与前置

DPO、SFT、PPO都是训练方法，但优化目标和工程需求不同。本讲用对照表解释，再完成自己的采用报告。前置前五讲；PPO只解释概念，不要求已经会强化学习。

## SFT、DPO与PPO各自在做什么

| 方法 | 当前需要的数据/信号 | 优化直觉 | 本单元状态 |
| --- | --- | --- | --- |
| SFT | 问题与目标回答 | 增加目标token概率 | 实际运行 |
| 标准DPO | 同问题chosen/rejected与固定参考 | 优化相对参考的偏好概率差 | 实际运行 |
| PPO类RLHF | 在线采样与奖励/优势等 | 用受约束策略更新提高奖励 | 仅概念，未运行 |

PPO是Proximal Policy Optimization，近端策略优化，核心以限制策略更新的方式进行强化学习。[原论文](https://arxiv.org/abs/1707.06347)。在常见语言模型RLHF工程中，还需生成轨迹、奖励信号、价值/优势计算和策略/参考约束等；实现变体不同，不能把所有PPO训练器流程说成一个固定模板。

标准DPO直接使用离线偏好对，当前训练阶段不需要另训显式奖励模型或在线采样来更新policy；但偏好数据仍可能来自模型生成和人工评审。更省某些工程步骤不意味着总是更好，也不意味着没有参考/显存/数据成本。

## 最小示例：检查初始DPO目标与信息边界

新建lesson_06.py：

```python
import torch
from data import make_pairs
from objectives import dpo_loss

pair = make_pairs()[0]
loss, margin = dpo_loss(torch.tensor([-3.0]), torch.tensor([-5.0]),
                        torch.tensor([-3.0]), torch.tensor([-5.0]))
print(pair["preference_origin"], pair["usage_policy"])
print("初始损失：", round(loss.item(), 6), "margin：", margin.item())
print("本例偏好由真人签署吗？", False)
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_06.py`，预期输出合成风格规则、教学范围、0.693147/0及False。最后False是本工程事实说明，不是检测任意外部偏好真实性的算法。

## 实际资源与测试

CPU与CUDA只用已有PyTorch，不装TRL/Transformers/PEFT。运行检查：

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

tests限定本工程，-q精简输出。作者22项测试通过，无CUDA跳过；CPU没有CUDA时该设备测试会明确skip，不写成GPU已验证。测试含公式梯度方向、completion/pad屏蔽、长度和/平均差、极值、参考冻结、权重读取和实际有界CPU/CUDA更新。

完整DPO循环CPU约1～3秒，CUDA也约1～3秒，仅微型训练段；首次导入/启动和评估另有时间，不是大模型性能排名。CUDA峰值约78009856字节是PyTorch分配张量的峰值，包含实验中仍存活的多个对象，不是整卡显存或每策略独立峰值。

## 交付一页采用判断

写问题/偏好准则与来源、train/dev/test来源分组、Base含义、SFT权重及参考来源、beta/学习率/更新/精度、log概率统计边界、实际生成/偏好排序/旧任务、至少一个偏差或退化、资源、采用范围与未做项。

本实验固定诊断已反复查看，不叫盲测；数据合成，没有真实人类偏好、外部权重或通用Tokenizer。报告中ppo_executed=False、resume_training_supported=False。非有限损失/梯度必须停止，不能删错样本或隐藏失败来凑跑通。

结论可以是“不采用全任务替换”，这也完成实验。只要能复核DPO从SFT快照开始、目标与参考正确、数据有出处并报告退化，不需要为了课程下载大模型或追求好看的分数。

## 常见错误与练习

把DPO叫在线PPO；reference随着policy更新；用回答平均log概率代替标准和却不说明变体；chosen等于事实真值；偏好分数提高就部署；拿推理pt称等价续训；从固定诊断选出的beta称普遍最优。

### 跟做：说明三个目标区别

完成标准是SFT目标回答、DPO相对偏好、PPO奖励驱动，并明确本例PPO未跑。

> [!example]- 参考答案与解析
> SFT增加示范回答概率；DPO优化成对选择相对参考；PPO类方法使用强化学习奖励与更新约束。数据、反馈和工程需求不同，不能只比较训练命令名字。

### 独立：写拒绝全替换

用至少两个实测依据写结论。完成标准是旧copy退化、坏偏好/过优化风险，以及范围限制。

> [!example]- 参考答案与解析
> 旧copy从12/12降到SFT3/12、DPO最多4/12，不能全替换；坏偏好/大步更新可严重退化。保留Base及隔离研究，真实任务/盲评待测，不用风格改善掩盖旧能力损失。

### 迁移：数据与算力不足

怎样完成有意义的小实验？完成标准是小模型、明确数据/公式/参考、失败与限制，不下载超出资源模型。

> [!example]- 参考答案与解析
> 用获批小数据和已有设备验证目标/冻结/评估机制，记录偏差与代价；真实资源方案明确后再申请安装/下载。小实验不冒充真实LLM对齐收益，但足以学习工程流程。

## 后续

[[../参考工程验证记录|作者实际实验与限制]] · [[../示例工程/README|代码导航]]。下一单元规划：规划与工具使用微调，待编写。
""",
    )
    write(
        f"{MAP}.md",
        r"""
## 第一讲从哪里开始

打开 [[逐讲学习/01 构造同一问题的chosen与rejected偏好|第1讲]]，在VS Code创建lesson_01.py，读取一对合成数据。完成判断：能区分同prompt下相对偏好、事实正确和偏好来源。

## 六讲顺序

1. [[逐讲学习/01 构造同一问题的chosen与rejected偏好|01 偏好数据与故障标签]]
2. [[逐讲学习/02 计算回答概率并只统计completion|02 completion概率和掩码]]
3. [[逐讲学习/03 用冻结参考与beta读懂DPO损失|03 DPO目标与参考]]
4. [[逐讲学习/04 从SFT权重启动CPU与GPU的DPO|04 实际CPU/CUDA训练]]
5. [[逐讲学习/05 比较BaseSFT与DPO并分析长度偏差|05 固定评估与退化]]
6. [[逐讲学习/06 分清SFTPPO与DPO并写采用结论|06 方法分工与采用结论]]

## 前置、阅读与环境

[[../26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图|SFT、训练与权重]]、[[../05_数学概率与优化/00 数学概率优化学习地图|log概率/梯度]]、[[../31_推理与工具数据构造/00 推理与工具数据构造学习地图|来源与标签]]。陌生概念沿详细讲解复习。

Obsidian读正文，VS Code读 [[示例工程/README|代码导航]]。根共享.venv、已有PyTorch；CPU即可，作者也实际CUDA FP32验证。无新依赖、外部权重或模型下载。

## 实际产物与限制

8133参数GRU，合成48/12/12偏好对；本地copy Base→SFT权重快照→冻结参考→两beta、小/大学习率和错误偏好对照。保留偏好分数好但生成坏、旧任务退化等实际反例，不要求结果必须改善才完成课程。

固定诊断已反复查看，非盲测；无真实人类偏好、PPO、TRL或等价续训，不能推断真实LLM收益。[[参考工程验证记录|作者结果]] · [[../我的学习记录|记录自己的实际进度]] · [[../../00 从这里开始|学习首页]]。

下一单元规划：规划与工具使用微调，待编写。
""",
    )
    write(
        "示例工程/README.md",
        r"""
## 先运行

VS Code打开本目录，选择根共享Python：

```powershell
& ..\..\..\.venv\Scripts\python.exe experiment.py --device cpu --output-dir report-my-cpu-01
& ..\..\..\.venv\Scripts\python.exe experiment.py --device cuda --output-dir report-my-gpu-01
```

第二条仅已有CUDA时执行，不安装环境/驱动。新目录拒绝覆盖。实际PyTorch2.14.0+cu130可用，运行不需要TRL/Transformers/PEFT或外部权重。8133参数GRU、45token词表，不是通用LLM。

## 代码导航

- [data.py](./data.py)：36来源组、合成chosen/rejected、故障偏好、词表、completion与padding标签。
- [model.py](./model.py)：Embedding/GRU/词表投影，贪心8token上限生成。
- [objectives.py](./objectives.py)：因果位移、completion log概率和、标准sigmoid DPO与beta检查。
- [training.py](./training.py)：SFT与DPO训练、独立冻结参考、参考缓存、梯度检查/裁剪与GRU布局。
- [evaluation.py](./evaluation.py)：窄颜色/EOS指标、完全简短、旧copy、给定回答概率排序与逐题输出。
- [experiment.py](./experiment.py)：Base→SFT.pt重新加载→四组DPO及固定dev/test诊断报告。
- [test_dpo.py](./tests/test_dpo.py)：数据/掩码/位移/长度/公式/梯度/参考/读取与实际CPU/CUDA测试。
- [conftest.py](./tests/conftest.py)：仅本工程测试加入源码目录。
- [requirements.txt](./requirements.txt)：沿用共享PyTorch及已有pytest/Ruff，不自动安装。

## 结果与文件

训练48对、dev/test各12对，整来源组隔离；合成风格规则不是人类签署，错误偏好是显式故障对照。Base旧copy12/12、新颜色0；SFT颜色12/12、brief2/12、copy3/12。最终CPU/CUDA：clean beta0.1为颜色11/12、brief8/12、copy4/12；beta0.5为12/12、6/12、4/12；biased-short为4/12、4/12、3/12；aggressive-clean三项均0。

base.pt、sft.pt和四组DPO.pt只供推理/开始新训练阶段，未含优化器/RNG等状态，不支持等价续训。DPO从保存SFT权重加载并建立新AdamW。reference未改变有断言与测试支持。

## 检查与范围

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

作者22项测试通过，包括实际CUDA有界更新，无skip。固定诊断反复观察，非盲测或未经调参的最终保留集。窄颜色指标不表示全部语义/格式；排序和生成不同。参考约束不能自动修复坏偏好/长度偏差/过优化。未执行PPO、真实人类偏好、外部模型或大规模资源测试。

[[../00 DPO与偏好优化学习地图|六讲正文]] · [[../参考工程验证记录|作者实验与限制]]。[DPO论文](https://arxiv.org/abs/2305.18290) · [TRL目标参考](https://huggingface.co/docs/trl/dpo_trainer)。
""",
        "DPO示例工程代码导航",
    )
    print("已写入单元33六讲、地图与代码导航")


if __name__ == "__main__":
    main()
