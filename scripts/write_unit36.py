"""生成长上下文、显存与分布式六讲；导入不修改教材。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/36_长上下文显存与分布式训练"
MAP = "00 长上下文显存与分布式训练学习地图"
LESSONS = [
    "01 计算注意力矩阵并区分显存组成",
    "02 实测长度显存耗时与激活重算",
    "03 打包短样本并阻止跨样本泄漏",
    "04 观察位置缩放和滑动窗口的边界",
    "05 用两个CPU进程读懂DDP梯度同步",
    "06 估算分片显存并设计多卡与保存方案",
]


def write(name, body):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {path.stem}\ntags: [learning, context-memory, beginner]\nupdated: 2026-10-13\n---\n\n# {path.stem}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(index, body):
    previous = (
        f"[[{LESSONS[index - 1]}|上一讲]]"
        if index
        else "[[../../35_模型公开基准评测/00 模型公开基准评测学习地图|前一单元]]"
    )
    following = (
        f"[[{LESSONS[index + 1]}|下一讲]]" if index < 5 else f"[[../{MAP}|返回地图]]"
    )
    write(
        f"逐讲学习/{LESSONS[index]}.md",
        f"[[../{MAP}|单元地图]] · {previous} · {following}\n\n" + body,
    )


def main():
    write(
        f"{MAP}.md",
        r"""
## 现在从哪里开始

打开 [[逐讲学习/01 计算注意力矩阵并区分显存组成|第 1 讲]]。在 VS Code 进入本单元“示例工程”，创建 `lesson_01.py`，算出序列翻倍后的注意力矩阵大小。完成判断：知道哪一部分按长度平方增长，知道估算不等于 GPU 实测峰值。

## 六讲学习顺序

1. [[逐讲学习/01 计算注意力矩阵并区分显存组成|01 注意力复杂度与显存组成]]
2. [[逐讲学习/02 实测长度显存耗时与激活重算|02 实测、重算与 SDPA 后端]]
3. [[逐讲学习/03 打包短样本并阻止跨样本泄漏|03 padding／packing 与实际反例]]
4. [[逐讲学习/04 观察位置缩放和滑动窗口的边界|04 RoPE、插值、YaRN 与窗口]]
5. [[逐讲学习/05 用两个CPU进程读懂DDP梯度同步|05 真实双 CPU 进程 DDP]]
6. [[逐讲学习/06 估算分片显存并设计多卡与保存方案|06 FSDP／ZeRO／张量并行与保存设计]]

## 前置与环境

矩阵、张量与梯度见 [[../06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|PyTorch 训练闭环]]；因果注意力、Q/K/V 和 Decoder 见 [[../08_Transformer从零实现/00 Transformer 从零实现学习地图|Transformer 从零实现]]；固定数据／配置／质量边界见 [[../35_模型公开基准评测/00 模型公开基准评测学习地图|评测教程]]。本单元重新讲解直接使用的概念，不默认你已理解多进程、显存分配器或分片。

Obsidian 读正文，VS Code 从 [[示例工程/README|代码导航]]进入。根共享 `.venv`、已有 PyTorch，不下载大模型、不安装 FlashAttention 或 DeepSpeed。本机一张 RTX 5070 Laptop GPU，BF16 可用，Gloo 可用、NCCL 不可用。当前 Windows wheel 未编入 FlashAttention；明确记录失败，不把 math SDPA 写成 FlashAttention。

## 实际练习与范围

208192 参数因果 Decoder，CPU FP32 与 CUDA BF16 autocast，比较长度 64～512（GPU 另到 1024）的朴素注意力、逐层激活重算、显式 math SDPA。另实测不等长与等长 packing，保留“填充减少却变慢”“等长打包反增显存”的结果。两 CPU 进程真正执行 Gloo/DDP 一步，与单进程全批次参考一致。

位置旋转／缩放和窗口只做机制探针，没有训练出可靠长上下文模型。多 GPU、FSDP、DeepSpeed ZeRO、张量并行和分布式保存做带假设的设计，不声称已实测多卡或等价恢复。[[参考工程验证记录|作者结果与未测范围]]。

当前必须掌握：显存组成、正确测量、重算代价、样本边界、位置外推风险、梯度平均与分片估算。更大的模型、跨机通信、完整分布式恢复与长程质量验证可稍后扩展；无多卡也能完成本单元设计验收。

[[../我的学习记录|记录自己实际完成的操作]] · [[../../00 从这里开始|学习首页]]。

下一单元规划：论文精读与技术趋势判断，待编写。
""",
    )
    lesson(
        0,
        r"""
## 本讲任务与前置

先计算注意力矩阵，再分清训练状态、激活与缓存，最后写估算假设。需要二维矩阵乘法和张量 shape；陌生时先到 [[../../08_Transformer从零实现/00 Transformer 从零实现学习地图|注意力详细教程]]，本讲重新解释维度含义。

完成标准：能算出长度翻倍导致分数矩阵四倍，知道完整训练峰值不只有参数；能区分 MB/MiB、allocated/reserved 与设备总占用。

## 要解决什么问题：为什么长输入容易耗尽显存

模型参数不变，输入由 128 token 增到 256 token，内存需求仍会增加。token 是模型处理的文本单位，本例用整数代替文本编号。每个位置与前面位置计算匹配，需要保留前向计算的中间结果供反向求梯度；这些中间张量称激活。

先估算主要增长项，再测实际峰值。仅根据模型文件大小判断能否训练，会漏掉梯度、优化器状态、激活、临时算子缓冲等；仅按最大序列长度判断模型能力，又会把“放得下”误当“答得对”。

## 概念与直觉：注意力矩阵

Q（query，查询）表示当前位置想找的信息；K（key，键）表示各位置用于匹配的信息；V（value，值）表示匹配后要汇总的内容。每个查询和每个键的内积得到分数，随后 softmax 归一化成权重，再汇总 V。

设 B 为一个批次的样本数、H 为注意力头数、L 为每个样本的 token 长度、d 为每头表示宽度。分数张量形状是 B×H×L×L，最后两个 L 分别对应查询位置和键位置。每头 QK 匹配与加权 V 的主要计算量随 L²d 增长；写 O(L²) 是固定其他尺寸时的增长描述，不是具体毫秒数。

因果掩码禁止看未来位置，分数矩阵的上三角不可见，但普通密集实现仍常分配完整 L×L；即便仅计算下三角，增长阶数仍是平方。像每个人和其他人做配对，人数翻倍，组合近似四倍；实际矩阵操作还受硬件与算子实现影响，不能由类比预测耗时。

## 最小示例：手算与程序核对

VS Code 打开工作区，在 `01_学习指南/36_长上下文显存与分布式训练/示例工程` 打开 PowerShell 终端，新建 `lesson_01.py`：

```python
from planning import attention_matrix_bytes, training_state_bytes

for length in (128, 256):
    byte_count = attention_matrix_bytes(2, 4, length, element_bytes=4)
    print(length, byte_count, byte_count / 1024**2)
print("FP32 Adam状态", training_state_bytes(100, 4, "ddp"))
```

```powershell
..\..\..\.venv\Scripts\python.exe lesson_01.py
```

三个 `..` 回到根共享环境；当前目录中的 lesson_01.py 是要执行的文件。预期：

```text
128 524288 0.5
256 2097152 2.0
FP32 Adam状态 1600
```

第一行计算 2×4×128×128×4=524288 bytes；第二行长度翻倍，得到四倍字节。`1024**2` 表示 1024 的平方，一个 MiB。每元素 4 bytes 是 FP32（32 位浮点）的假设。这里仅一层的一张分数矩阵，没有把四层、概率张量、反向临时量等都算进去。

## 逐步区分显存组成

| 部分 | 存什么 | 主要受什么影响 |
| --- | --- | --- |
| 参数 | 可学习权重 | 参数量、存储精度、是否分片 |
| 梯度 | 权重如何调整 | 参数量、精度、同步策略 |
| 优化器状态 | 更新历史，例如 Adam 两个统计量 | 优化器与状态精度 |
| 激活 | 前向中间结果供反向使用 | 批次、长度、层数、宽度、重算 |
| 临时量与通信缓冲 | 算子／聚合阶段使用 | 实现、后端、并行策略 |
| 推理 KV cache | 已生成位置的 K/V | 推理长度、批次、层、KV 头数与精度 |

本次训练实验用无动量 SGD（按当前梯度更新参数），不保存 Adam 的两个统计量；没有自回归推理 KV cache。因此 planning.py 的 FP32 Adam 16 bytes/参数估算是另一个设计假设，不能当本实验实际状态量。

该估算为参数 4+梯度 4+Adam 两个状态 8=16 bytes。多张卡 DDP 每卡仍复制完整状态，所以 world_size=4 时每卡 100×16=1600 bytes，不是自动除以四。第 6 讲再讲哪些分片策略能分摊哪些状态。

## allocated、reserved 与实际总占用

PyTorch 的 CUDA 分配器会保留可复用的内存块。allocated 是当前张量实际使用量，reserved 是分配器向设备保留的块量；设备管理工具还可能显示上下文、其他程序和非该分配器占用。不能将三者当一个数。

删除张量未必让 reserved 立即下降；释放未用缓存不能释放仍被张量引用的内存，也不替代解决激活过大。相关机制可核对 [PyTorch 2.14 CUDA 说明](https://docs.pytorch.org/docs/2.14/notes/cuda.html)。MiB/GiB 用 1024 的幂，MB/GB 用 1000 的幂，报告单位要一致。

## 动手操作与常见错误

先不运行代码，预测 L=512 时第一张矩阵为多少 MiB；再改 length 值验证。完成判断：能指出“仅一层、B=2、H=4、FP32”的假设，而不是只给一个显存结论。

把 32 位当 32 bytes 会放大八倍：8 bits=1 byte。把序列翻倍按内存两倍算，检查是否漏掉第二个 L。报维度需为正整数时核对输入，不能用零长度输出证明不占显存。CPU 示例不使用 CUDA 内存计数，后面报告为 null；null 是未测，不是 0 MiB。

## 分级练习与答案解析

### 跟做练习：再翻倍

将 L 改为 512，手算本例单层分数矩阵。提示：256 的 2 MiB 再乘四。

> [!example]- 参考答案
> 8 MiB。它仍不是总训练峰值，层数、概率与反向张量等另计。完成标准：数字与单位正确，并保留估算范围。

### 独立练习：只看权重文件

权重文件 4 GiB，显卡有 8 GiB，可以直接断定全参数训练可行吗？

> [!example]- 参考答案
> 不可以，还要估梯度、优化器、激活与临时量，核对精度和实现。文件编码也未必等于加载后的张量大小。完成标准：说出至少三项遗漏，知道最终还要实测。

### 迁移练习：allocated 与 reserved

张量已删，reserved 仍高，是否一定泄漏？该先看什么？

> [!example]- 参考答案
> 不一定，分配器可能保留空闲块。先看 allocated 是否仍高、有没有活跃张量引用，再对照分配器和设备总占用；不能只调用清缓存掩盖活跃计算图。完成标准：区分缓存与仍被引用的对象。
""",
    )
    lesson(
        1,
        r"""
## 本讲任务与前置

实际运行不同长度，再对比逐层激活重算和 SDPA math 后端。需要上一讲的显存组成、前向／反向／优化器更新；训练顺序见 [[../../06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|PyTorch 训练闭环]]。

完成标准：保存自己的 CPU 报告，可用 GPU 时保存 CUDA 报告；说明计时包含什么、峰值是什么、损失差不代表长程能力，并区分 FlashAttention 与 math SDPA。

## 要解决什么问题：低显存是否白得

前向保存全部中间激活，反向读取它们，通常节省重算时间但占内存。激活重算（gradient/activation checkpointing）保留必要输入，反向时再执行部分前向，用额外计算换较少保存。

这里 checkpointing 的“检查点”是计算图中的重算边界，不是磁盘训练检查点。它不会保存优化器或随机状态用于续训。第 5、6 讲的 rank 权重文件属于另一类保存，不能混用名称推断功能。

## 本次模型与公平对照

四层小 Decoder，64 token 词表、表示宽度 64、4 个头，共 208192 参数。输入是随机合成整数，标签按当前整数的固定映射构造，仅用于稳定、可对照的前向损失与梯度；没有自然语言训练、长期收敛或长文本能力测量。

每种方案从相同初始化与相同输入开始：eager 显式计算注意力矩阵；checkpoint 在 eager 各层使用重算；sdpa 调用 PyTorch 统一注意力接口，默认明确指定 math 后端。每组预热一步，再恢复初始权重，计时三次，每次恢复权重后完成一轮更新，以中位数汇总。

打开 [model.py](../示例工程/model.py)：块内归一化输入→线性得到 Q/K/V→分头→位置旋转→注意力→残差→前馈。每头宽度 16，张量变为 B×4×L×16，输出再拼回 B×L×64。相同状态字典可用于三种执行方式，不改变参数结构。

## 动手操作：CPU 与 CUDA

在本单元示例工程 PowerShell 运行：

```powershell
..\..\..\.venv\Scripts\python.exe experiment.py --device cpu --lengths 64 128 256 512 --output-dir report-my-cpu-01
```

`--lengths` 列出要测的长度，程序限制 8～1024；`--device` 选计算设备；`--output-dir` 必须是新目录。报告出现 4×3=12 行。CPU 没有 CUDA 峰值，相关字段为 null，不将 null 写成零内存。

已有 CUDA 支持 BF16 时运行：

```powershell
..\..\..\.venv\Scripts\python.exe experiment.py --device cuda --lengths 64 128 256 512 1024 --output-dir report-my-cuda-01
```

BF16 是 16 位浮点格式，动态范围与 FP32 接近但有效精度较低。本例用 `torch.autocast` 在适合的运算中使用 BF16，权重／梯度及损失保持 FP32；不等于所有张量减半，也不是 INT4 量化。本例不使用 FP16 的梯度缩放路径，仍检查损失与梯度有限；不能把此选择机械搬给所有 FP16 训练。

## 最小示例：读取自己的 CPU 测量

创建 `lesson_02.py`，先完成 CPU 命令：

```python
import json
from pathlib import Path

with (Path("report-my-cpu-01") / "report.json").open(encoding="utf-8") as file:
    report = json.load(file)
print(report["parameters"], report["device"])
for row in report["results"]:
    if row["length"] == 512:
        print(row["variant"], round(row["median_seconds"], 4),
              row["peak_allocated_bytes"], round(row["loss_abs_difference"], 6))
```

```powershell
..\..\..\.venv\Scripts\python.exe lesson_02.py
```

预期参数 208192、设备 cpu；长度 512 出现 eager/checkpoint/sdpa 三行，峰值均 None，损失差接近零。具体时间由本机负载决定，不要求复制作者小数。

## 逐步读计时与质量检查

[experiment.py](../示例工程/experiment.py) 在 CUDA 上先同步，清零峰值统计，再计时；结束同步，避免把异步提交时间当完整计算时间。计时包括前向、损失、反向、梯度检查、SGD 更新和梯度复制到 CPU，不含数据加载；tokens/s 是本例每步 2×L 的处理槽数除时间。

CUDA peak_allocated 包含仍存活的权重快照、输入、梯度和临时张量，不是设备总占用；peak_reserved 受缓存影响，不能用它直接判某方案活跃张量峰值。短序列的固定缓冲可能主导峰值，所以不是每种优化都按比例省显存。

本机作者 CUDA 长度 1024：eager 峰值约 358.21 MiB，重算约 198.65 MiB，math SDPA 约 309.21 MiB。重算损失／梯度与 eager 一致，耗时增加；短长度 64 的重算峰值未降低。质量检查仅证明本合成一步的损失与梯度一致或接近，不能证明长文本准确率保持。

重算代码显式 `use_reentrant=False`，按 [PyTorch 2.14 checkpoint 文档](https://docs.pytorch.org/docs/2.14/checkpoint.html)核对接口；函数重执行时若依赖已改变的全局状态，可能得到错误梯度。当前无 dropout 或隐藏外部状态，测试还检查反向确实再次调用块。

## FlashAttention：接口存在不代表内核可用

[FlashAttention 原论文](https://arxiv.org/abs/2205.14135)利用分块与片上存储减少注意力计算中的读写及大矩阵保存，仍计算同类全注意力，不是通过只看近邻改变任务。它不把全注意力的计算增长阶数自动变成线性。

SDPA 是 scaled dot product attention（缩放点积注意力）的接口名；[PyTorch 文档](https://docs.pytorch.org/docs/2.14/generated/torch.nn.functional.scaled_dot_product_attention.html)说明后端可选且存在限制。本机 wheel 没有编入 FlashAttention，首次强制调用报 No available kernel。本工程现在先检查能力，明确指定 math，不静默写成 Flash 成功。

在确实编入且设备／输入兼容的环境，`--sdpa-backend flash` 才能强制尝试；本机执行会明确失败。需要新平台或额外包时先准备完整兼容方案并按工作区规则批准，当前不为教程变更环境。两项实际显存优化比较是重算与下一讲 packing，Flash 的本机边界保留为结果。

## 常见错误与分级练习

报缺 BF16 CUDA：先用 CPU 完成，核对环境，不自行安装驱动。报输出目录存在：换新名。峰值变化与耗时不同步正常，检查测量范围与缓存；只比一轮冷启动会混入初始化。出现非有限损失／梯度应停止检查，不隐藏失败。损失接近零差不是长期任务质量证明。

### 跟做练习：同长度比较

取自己报告长度 512 的三行，写时间、峰值是否测到、损失差。提示：CPU 没测 CUDA 内存。

> [!example]- 参考答案
> CPU 应记录 None，并解释为未测；GPU 记录实际 bytes 与统一单位，再比较损失差和耗时。完成标准：同设备、同长度、同精度比较，不拿 CPU FP32 与 GPU BF16 差异只归因后端。

### 独立练习：重算与续训

启用 checkpoint_layers=True，是否已经可以等价恢复训练？

> [!example]- 参考答案
> 没有，它改变激活保存／重执行，不生成完整磁盘训练状态。完成标准：区分计算图检查点与续训文件。

### 迁移练习：Flash 可用性

程序调用了 scaled_dot_product_attention，所以声称 Flash 加速。你先检查哪两项？

> [!example]- 参考答案
> 检查当前构建与输入是否支持该内核，并记录实际选定后端／强制运行结果；API 名称不够。完成标准：不会把 math 回退或 No available kernel 写成 Flash 成功。
""",
    )
    lesson(
        2,
        r"""
## 本讲任务与前置

先打包两个短序列，看清注意力与标签边界，再运行不等长／等长样本对照。需要因果掩码、标签与 ignore_index；忘记时到 [[../../34_规划与工具使用微调/00 规划与工具使用微调学习地图|监督范围教程]]，本讲重新解释跨样本问题。

完成标准：两个样本不能相互看见，边界不预测下一样本首 token，位置按样本重置；能解释为什么 packing 不总更快或更省显存。

## 要解决什么问题：短句被长句拖着补空位

padding（填充）把同批各序列补到最长长度，便于用矩形张量并行计算。例如长度 128、32、16、8，补到 128 后处理 4×128=512 个槽位，真实 token 仅 184。即使填充标签不算损失，普通密集计算仍可能处理这些槽位。

packing（打包）把多个短样本放进同一较长序列，减少填充。但直接拼接会让后一条看到前一条内容，还可能把上一条末 token 的目标设成下一条开头。省了填充却改变学习问题，不能当正确优化。

## 概念与机制：三项边界

样本 A=[1,2,3]，B=[4,5]。打包 token 为 [1,2,3,4,5]；位置为 [0,1,2,0,1]，分别从零开始；监督标签为 [2,3,-100,5,-100]，每条末尾忽略。

当前位置只可看同一段、且不晚于自己的位置。段 ID 表示属于哪个原样本，注意力允许条件是“相同段”与“因果”同时成立。布尔掩码中 True 表示允许；不同 API 可能有不同约定，当前按本模型与 SDPA 的规则解释。

位置重置让当前 RoPE 旋转按各样本位置计算；标签忽略阻止跨样本预测；注意力掩码阻止跨样本读内容。三者职责不同，不能只做其中一项就宣布完全隔离。

## 最小示例：查看打包结果

在本单元示例工程新建 `lesson_03.py`：

```python
from packing import pack_sequences

batch = pack_sequences([[1, 2, 3], [4, 5]])
print(batch["tokens"].tolist())
print(batch["labels"].tolist())
print(batch["positions"].tolist())
print(batch["allowed"].int().tolist())
```

```powershell
..\..\..\.venv\Scripts\python.exe lesson_03.py
```

预期前几行：

```text
[[1, 2, 3, 4, 5]]
[[2, 3, -100, 5, -100]]
[0, 1, 2, 0, 1]
[[1, 0, 0, 0, 0], [1, 1, 0, 0, 0], [1, 1, 1, 0, 0], [0, 0, 0, 1, 0], [0, 0, 0, 1, 1]]
```

矩阵每一行是某查询能读哪些键。例如第 3 行（从零数，是 B 的首 token）只有自己可见，不能看 A；`.int()` 将 True/False 显示为 1/0，实际模型仍使用布尔允许掩码。

## 逐步读源码与损失分母

打开 [packing.py](../示例工程/packing.py)：循环每条序列，将 token 放入总列表；`sequence[1:] + [-100]` 是本条下一个 token 的目标，最后忽略；`segments` 用重复段 ID 标归属，`positions` 对每段从零编号。两个段 ID 向量按行列比较得到同段矩阵，再与因果矩阵相与。

[packing_experiment.py](../示例工程/packing_experiment.py) 制作 padding 参照。填充位置的标签是 -100，键不可见；填充查询不参与损失，但至少有真实可见键，避免一整行 -inf 经 softmax 产生 NaN。不能以“填充不算损失”为由允许前向出现非有限值。

两种方案都对相同有效目标求均值。长度 128+32+16+8=184，四个样本各最后一项忽略，有效目标 180。不能一边按处理槽位平均、一边按有效 token 平均，随后把损失差解释成模型变化。

## 动手操作：两组真实对照

```powershell
..\..\..\.venv\Scripts\python.exe packing_experiment.py --device cpu --output-dir report-my-packing-cpu-01
```

有 BF16 CUDA 时另运行：

```powershell
..\..\..\.venv\Scripts\python.exe packing_experiment.py --device cuda --output-dir report-my-packing-cuda-01
```

报告分别有 uneven（128/32/16/8）与 equal（64/64/64/64），各 padding／packing 两行。同一初始化、相同样本内容、相同有效目标；计时三次中位数，字段 valid_targets_per_second 是有效监督目标吞吐，区别于填充槽位吞吐。

CPU FP32 损失／梯度接近一致，CUDA BF16 有小数值差，记录而不改判。它是这次一步数值质量对照，不证明长期训练或真实语料效果不变。

## 预期结果与密集 packing 反例

作者 GPU uneven：处理槽位 512→184，有效目标都 180，峰值约 78.89→72.24 MiB，但打包这次略慢。equal：槽位都 256、有效目标都 252，峰值约 70.27→77.12 MiB，打包也慢。

原因是本例仍计算一个完整密集打包注意力矩阵，即使块间掩码为 False，也不跳过这些矩阵运算。四条等长 64 序列的分数元素与 4×64² 成正比；拼成 256 后与 256² 成正比，扩大四倍。正确掩码保证语义隔离，不自动保证稀疏算子跳过工作。

真正高效的变长或块布局需要相应内核与边界协议；当前没有运行 Flash varlen 或稀疏 packing。不能把本例负结果推成 packing 普遍无效，也不能只宣传填充减少就隐去速度代价。

## 常见错误与分级练习

后一条输出随前一条无关 token 改变：先检查块掩码，测试会固定 B、改 A 并要求 B 输出不变。边界标签出现下一段首 token：修复末尾 -100。所有填充查询都无可见键：检查非有限值与掩码规则。实测变慢时保留报告，先检查密集长度平方与内核，而不是删掉反例。

### 跟做练习：读一行掩码

解释最后一行 [0,0,0,1,1]。提示：两个 1 都属于 B。

> [!example]- 参考答案
> B 的第二个 token 看得到 B 的第一和第二个 token，看不到 A；它的标签被忽略，因为是 B 末尾。完成标准：注意力可见与监督是否计分分别解释。

### 独立练习：只加 EOS

给 A 末尾加结束 token，却不做段掩码，是否一定阻止 B 读 A？

> [!example]- 参考答案
> 不能，结束 token 是数据，普通因果注意力仍允许 B 看到此前 A。需要明确段边界掩码与标签规则；真实模型可能学习边界行为，但不能当硬隔离。完成标准：不把文本标记当算子权限。

### 迁移练习：优化是否成立

packing 槽位减少，但有效目标/s 下降，应该报告什么？

> [!example]- 参考答案
> 同时记录槽位、有效目标、峰值、耗时和数值质量；说明当前实现／形状减少填充但速度未改善。完成标准：用目标吞吐判断任务效率，不用填充槽位数字替代收益。
""",
    )
    lesson(
        3,
        r"""
## 本讲任务与前置

观察 RoPE 角度缩放，再查看滑动窗口掩码，最后写长上下文验证方案。需要 Q/K/V、因果掩码和前面的位置重置；三角函数的用途是表示旋转，不要求先背复数推导。

完成标准：区分可以输入更大位置、可以分配更多 token、真正可靠地使用远处信息；知道简单插值不是完整 YaRN，窗口改变可见范围而不是免费保留全注意力。

## 要解决什么问题：模型放得下不等于用得好

输入超出训练长度，模型可能接收张量却误读距离、遗漏中间证据或答旧信息。延长上限只改变允许输入，不能保证权重已经学过这些距离。位置外推是将模型用到训练中没出现过的更远位置，存在分布变化风险。

本章只探查位置和可见范围，没有做长程训练、检索准确率或自然语言质量评测。后面任何“支持 L=1024”的计算结果都不自动变成“可靠理解 1024 token”。

## 概念与直觉：RoPE 的旋转

RoPE 是 rotary position embedding（旋转位置编码）。它在 Q 与 K 的坐标对上，按位置旋转不同角度，使匹配分数能体现位置关系。像不同位置把指针转不同角度；实际机制是对每两个坐标做二维旋转，不是给模型额外事实或记忆。

本例相邻两坐标为一对，角度由位置×频率得到；不同坐标对有不同频率。旋转保持每对长度，但改变方向，从而影响 QK 内积。[RoFormer 原论文](https://arxiv.org/abs/2104.09864)给出旋转位置的机制。不同实际模型可能采用不同配对布局，权重转换时不能随意换。

简单位置插值把位置除以 scale，例如 scale=2 时位置 4096 的角度对应原位置 2048。这让角度范围压回较短范围，也压缩了位置间距离；“范围接近”不等于保留所有分辨率与能力。

## 最小示例：角度与窗口

在本单元示例工程新建 `lesson_04.py`：

```python
import torch
from packing import causal_mask
from position import rope_angles

original = rope_angles(torch.tensor([4096]), head_dim=16)
scaled = rope_angles(torch.tensor([4096]), head_dim=16, scale=2)
print(original[0, 0].item(), scaled[0, 0].item())
print(torch.equal(scaled, rope_angles(torch.tensor([2048]), 16)))
print(causal_mask(6, window=2).int()[-1].tolist())
```

```powershell
..\..\..\.venv\Scripts\python.exe lesson_04.py
```

预期为 `4096.0 2048.0`、`True`、`[0,0,0,0,1,1]`。第一坐标对频率为 1，所以角度数值直接是位置；其他对频率更低。这里只验证公式对应，没有给模型新权重或测回答正确性。

## 逐步读旋转与缩放

打开 [position.py](../示例工程/position.py)。`head_dim` 是每个注意力头宽度，必须偶数才能成对。`torch.arange(0,head_dim,2)` 逐坐标对生成索引；基数 10000 用来确定频率，本例固定这个教学设置，不声称全部模型都用它。

`rope_angles` 得到长度×坐标对数的角度。`apply_rope` 分出 even/odd 两组，按 `a*cos-b*sin`、`a*sin+b*cos` 旋转，再交错放回。模型中只旋转 Q、K，V 不变。位置列表必须与序列长度一致，packing 的重置正是在这里发挥作用。

测试验证旋转前后范数接近、位置零不改变向量；这些是机制正确性，不是模型能力验收。scale 限制≥1且有限，任意缩放并非自动可用长上下文方案。

## YaRN 与其他扩展：保持方法边界

[YaRN 原论文](https://arxiv.org/abs/2309.00071)提出更完整的上下文扩展方法，涉及按频率处理与注意力相关调整，并需要相应模型验证。它不是仅把所有位置统一除以 2。本工程没有实现或训练 YaRN，`scale=2` 只称为简单位置插值，不给它贴完整算法名字。

选择扩展策略时要核对具体模型的原始位置配置、训练长度、预期扩展范围和适配训练；还要分别测短上下文是否退化、长位置是否利用证据，而不是把最大输入长度写成能力分数。

## 滑动窗口：看近处的明确代价

window=2 表示本层当前位置可看自己和前一个位置，掩码条件为 0≤查询位置-键位置<2；未来仍不可见。最后一行不能直接看到位置 0～3，但多层模型可以通过中间位置逐层传递信息，因此不能用一层矩阵断言所有远程信息绝对消失。

如果算法／内核真的只计算窗口内交互，注意力工作量可接近 L×window；本工程只是创建窗口布尔矩阵，仍为 L×L 存储，若送给当前 dense eager 算子不会自动省掉全部窗口外计算。与上一讲 packing 一样，掩码是语义规则，不等于稀疏内核。

长期任务要看窗口是否覆盖必要依赖，或是否另外提供全局位置、摘要或跨窗口传递。当前没有运行真实滑窗内核，也不把观察掩码叫速度实验。

## 动手操作：设计质量探针

把测试长度、证据位置和干扰内容分开变化：例如固定问题，把关键事实放在开头／中间／结尾；分别用训练内长度与扩展长度，保存实际回答和引用。再加入需要两段远处信息合并的任务，比较原始／插值／窗口方案，同时测显存与耗时。

在自己的学习记录写“本次角度与掩码已运行，长文本回答尚未验证”。不要用简单 needle（一条埋入事实）测试替代所有复杂长程能力；实际业务还需跨段推理和抗干扰。needle 在这里指将待查事实放进长输入的定位题，不是模型结构。

## 常见错误与分级练习

奇数 head_dim 不能完整配对，会报错；检查头数与宽度设计。位置长度不匹配时核对 packing 位置列表。窗口允许未来时检查距离方向，应该是 query-key 而非 key-query。看到 scaled 与原角度相等就宣称能力等价：改为记录机制结果，另做实际质量任务。

### 跟做练习：窗口变三

将 window=3，预测最后一行。提示：自己加两个之前位置。

> [!example]- 参考答案
> [0,0,0,1,1,1]。完成标准：知道这一行表示当前层直接可见范围，不能据此报告真实加速。

### 独立练习：插值与 YaRN

只改 scale=2，可以写已实现 YaRN 吗？为什么？

> [!example]- 参考答案
> 不可以，这只是统一位置插值，缺少完整方法中的频率与注意力调整及训练验证。完成标准：准确命名机制，不用算法名称替代实际实现。

### 迁移练习：长文本宣称

模型不报错处理 32K token，能写 32K 可靠上下文吗？列两项未完成验证。

> [!example]- 参考答案
> 不能仅凭不报错。还需不同证据位置／跨段任务的正确率与短上下文退化检查，同时测实际显存／耗时。完成标准：区分输入容量、机制与任务质量。
""",
    )
    lesson(
        4,
        r"""
## 本讲任务与前置

启动两个 CPU 进程，完成一次真实 DDP 更新，再核对单进程全批次参考。需要参数、梯度、优化器以及均值；不知道进程时把它理解为操作系统中独立运行的一份程序，它与普通函数调用不同。

完成标准：自己的新报告 world_size=2、每进程 2 样本、全局 4 样本，两个进程更新后权重相同，并与参考一致；知道它不是双 GPU 测速或显存分片。

## 要解决什么问题：多份模型如何学成一份

数据并行让多份相同模型处理不同数据，再合并梯度，同步更新。DDP 是 DistributedDataParallel（分布式数据并行）；它复制模型，每个进程处理一份数据，反向时协调梯度，不自动切分参数，也不自动为你划分所有输入。

rank 是进程在组里的编号，world_size 是组大小；本例 rank=0、1。Gloo 是通信后端，负责这些进程交换张量；NCCL 是常见 NVIDIA GPU 通信后端。本机 Windows Gloo 可用、NCCL 不可用，示例采用两个 CPU 进程，避免把单卡冒充多卡。

## 概念与直觉：平均梯度

两人各解两题，最后合并学习反馈；实际是每个进程对本地均值损失求梯度，再同步平均。本地批次大小相等时，“两份本地均值梯度的平均”对应四题整体均值梯度。每人处理数量不等时，直接平均本地均值可能不等于全局样本均值，需要明确加权或数据补齐策略。

```mermaid
flowchart LR
    A[rank 0：样本 0和1] --> C[同步平均梯度]
    B[rank 1：样本 2和3] --> C
    C --> D[两份相同权重更新]
```

本例线性模型只有两个权重，输入两维、输出一维，无偏置。初始 [0.5,-0.25]，SGD 学习率 0.1，均方误差损失。小模型足以观察同步过程，不需要昂贵全参数训练。

## 动手操作：真实双进程实验

在本单元示例工程 PowerShell 运行：

```powershell
..\..\..\.venv\Scripts\python.exe distributed_demo.py --output-dir report-my-ddp-01
```

脚本用 main 入口启动两个子进程，在系统自有临时目录创建通信会合文件；会合表示各进程先约好属于同一个通信组。使用完成自动清理自己的临时目录，不删除学习者的旧报告。

预期输出 world_size=2、local_samples=2、global_samples=4、max_abs_difference=0.0，参考权重的两个值约为 0.9875、0.1625。新目录有 rank-0.pt、rank-1.pt 与 report.json。两份是重复模型权重，不是模型分片，也不是完整续训检查点。

## 最小示例：读取执行结果

新建 `lesson_05.py`，先执行上面命令：

```python
import json
from pathlib import Path

with (Path("report-my-ddp-01") / "report.json").open(encoding="utf-8") as file:
    report = json.load(file)
print(report["world_size"], report["local_samples"], report["global_samples"])
print(report["reference_weights"])
print(report["max_abs_difference"])
print(report["checkpoint_scope"])
```

```powershell
..\..\..\.venv\Scripts\python.exe lesson_05.py
```

预期第一行 `2 2 4`、第三行 `0.0`；权重最后小数因浮点显示可为 0.9875000119 等。最后字段明确是两份复制权重，不能把文件名中的 rank 当成分片证据。

## 逐步读训练顺序

打开 [distributed_demo.py](../示例工程/distributed_demo.py)。父进程 `multiprocessing.spawn` 启两个 worker；每个 worker 先 init_process_group，以相同会合位置、不同 rank、相同 world_size=2 形成组，超时 30 秒。

每个进程构造相同初始模型并用 DDP 包装。`slice(rank*2,(rank+1)*2)` 给 rank0 前两题、rank1 后两题，显式分数据；没有默认所有进程重复全部四题。然后 train、zero_grad、前向、本地均值损失、backward、step。DDP 在反向协调梯度，step 后两份权重相同。

每进程保存自己权重，barrier 表示都到达该点再继续；最后销毁组释放通信资源。父进程等待子进程完成，单独对全部四题做一次相同 SGD 更新，读取两个文件并比较最大绝对差；不一致立即报错，不把文件写出来当同步成功。

按 [PyTorch 2.14 DDP 文档](https://docs.pytorch.org/docs/2.14/generated/torch.nn.parallel.DistributedDataParallel.html)核对机制；当前示例无真实 GPU 同步速度或跨机网络测试，也没有 DataLoader 的自动采样器。

## 保存与恢复的边界

rank 文件只保存模型状态、rank/world_size 与完成步数。未保存优化器、随机状态、数据位置或完整恢复协议，因此用途写成 replicated_DDP_weights_not_sharded_checkpoint_or_exact_resume。两份权重重复是 DDP 的模型副本，不是 FSDP/ZeRO 分片。

真实 DDP 常由指定 rank 保存一份可恢复状态；其他 rank 按协调协议读入，但保存前必须保证步数与状态一致。分片训练的保存方式不同，第 6 讲讨论设计。本例文件可核对一步更新，不声称等价续训。

## 常见错误与排查

启动后通信超时：查看最早子进程错误，核对后端、会合位置、world_size、各进程是否都启动，不无限等待。Windows 原生 FileStore 在本次中文工作区路径上首次报 No such file or directory，改用系统临时目录的自有会合文件后成功；不因此重命名工作区或更换系统 Python。

重复运行目录已存在：换新名，保留失败与成功记录。少一个 rank 文件表示运行没完整完成，不能仅凭另一个文件通过验收。若两进程都用全部数据，可能权重一致但没有实现期望的数据划分，检查 local/global 样本范围。设备和进程数不同概念，CPU 双进程不等于双 GPU。

## 分级练习与答案解析

### 跟做练习：数据归属

在源码标出 rank0、rank1 的索引范围，解释 global_samples=4。提示：slice 右边界不含。

> [!example]- 参考答案
> rank0 为 [0,2)，rank1 为 [2,4)，各两题、合起来四题。完成标准：不把两个进程各全批次误写成八条独立样本。

### 独立练习：DDP 是否省参数显存

模型与优化器状态单卡放不下，只增加 DDP 卡数就一定可行吗？

> [!example]- 参考答案
> 不一定，DDP 每卡复制完整参数／状态。可以减少本地批次激活，但状态过大时需评估分片、参数高效训练等策略。完成标准：指出 DDP 主要分数据，不把总显存简单相加。

### 迁移练习：不等量本地均值

rank0 一题，rank1 三题，简单平均两份均值梯度会给两组怎样的权重？

> [!example]- 参考答案
> 两组各占一半，rank0 的单题权重过大；全局逐题均值应按1/4与3/4分组加权，或设计均衡批次与相应损失归约。完成标准：说明当前演示仅验证等量本地批次，不直接推广全部数据分布。
""",
    )
    lesson(
        5,
        r"""
## 本讲任务与前置

估算 DDP／ZeRO 的每卡状态，设计无多卡条件下的方案与保存协议。需要上一讲模型复制、梯度平均，以及第一讲参数／梯度／优化器与激活区别。本讲不安装分布式框架，不声称估算是实际峰值或吞吐量。

完成标准：给出带假设的单卡／多卡方案、目标吞吐验证计划和保存／恢复状态表；知道数据并行、张量并行与分片各改变什么。

## 要解决什么问题：单卡状态放不下时怎么分

DDP 每卡完整复制状态，模型本身过大时增加副本不能解决。FSDP 是 Fully Sharded Data Parallel（完全分片的数据并行），通过分摊参数、梯度与优化器状态，计算到某部分时再协作取得所需数据。它仍需要激活、通信缓冲与临时参数聚合，不能把总状态除卡数就当实际峰值。

DeepSpeed ZeRO（Zero Redundancy Optimizer，减少冗余状态的优化方案）分阶段处理状态冗余：stage1 分优化器，stage2 再分梯度，stage3 再分参数。按 [DeepSpeed 官方说明](https://www.deepspeed.ai/tutorials/zero/)核对阶段；框架具体配置、卸载到 CPU 等另需验证，本机没有安装或运行它。

## 概念与简单估算

本例统一用 FP32 参数4、梯度4、Adam 两状态8 bytes/参数，不含激活、额外 master 副本、通信、临时聚合或碎片。P 是参数数、N 是分摊状态的进程数：

| 策略 | 每卡粗状态 bytes | 哪部分复制 |
| --- | --- | --- |
| DDP | 16P | 参数、梯度、优化器 |
| ZeRO1 | P×(8+8/N) | 参数与梯度 |
| ZeRO2 | P×(4+12/N) | 参数 |
| ZeRO3 全分片近似 | 16P/N | 粗状态分摊，临时聚合另计 |

FSDP 全分片可以用相似粗状态起点，但实际布局、层级和预取影响峰值；本计算器不是完整 FSDP/ZeRO 实现。模型只有推理、使用 SGD、冻结大部分参数或不同精度时，需改变假设，不能套用这个16。

## 最小示例：状态与容量方案

在本单元示例工程新建 `lesson_06.py`：

```python
from planning import GIB, memory_plan, training_state_bytes

for strategy in ("ddp", "zero1", "zero2", "zero3"):
    byte_count = training_state_bytes(1_000_000_000, world_size=4, strategy=strategy)
    print(strategy, round(byte_count / GIB, 3))
plan = memory_plan(7_000_000_000, gpu_gib=24, activation_gib=2,
                   world_size=8, strategy="zero3")
print(round(plan["estimate_with_headroom_gib"], 3), plan["estimated_fits"])
print(plan["scope"])
```

```powershell
..\..\..\.venv\Scripts\python.exe lesson_06.py
```

预期四策略约 14.901、9.313、6.519、3.725 GiB；7B、8进程、每卡24 GiB 的粗预算含余量约18.798 GiB，estimated_fits=True。这是一个假设方案，不是本机八张卡或真实7B训练结果。

`1_000_000_000` 中下划线只帮助读数，仍是一十亿整数；GIB 是1024³。memory_plan 把粗状态加自己给出的激活估计，再乘1.25作为教学余量。1.25 不是官方万能安全系数，也未精确估临时全参数聚合；True 表示这套假设预算内，不保证运行不溢出。

## 逐步做单卡／多卡设计

假设 7B FP32 Adam，全状态约104.31 GiB；本机约7.93 GiB GPU，状态本身远超容量，减少序列长度不能让这些状态消失。当前单卡适合小模型、已有参数高效教程或明确更小状态方案；不强制在本机做昂贵全参训练。

假设可用8×24 GiB与通信条件合适，ZeRO3/FSDP 全分片可作为候选，上述粗每卡预算约18.80 GiB。下一步列实际层大小、聚合／预取、优化器精度、激活峰值、通信拓扑，再在允许的环境跑小批验证；如果峰值仍超预算，要调整微批次、重算或分片粒度，不能改估算数字让结论变真。

吞吐量不能由显存公式推出。假设目标每秒2000个有效监督 token，本地微批次1、长度2048、梯度累积4、8进程，全局每更新32条。若每条有效目标约2048，则一次更新约65536有效token，目标要求完整更新不超过约32.77秒；这是验收预算，不是速度预测。

梯度累积是在更新前处理多个微批次并累加梯度；要按目标损失归一化，再 step，而不是每微批次都更新。有效 batch=每进程微批次×累积次数×数据并行进程数。真实数据有填充、末尾忽略等，需实际计数有效目标；通信、数据加载和保存都应纳入完整性能计划，不能用本单元小模型速度外推7B。

## 数据并行、张量并行与流水线

数据并行分不同样本给模型副本；张量并行把同一层的矩阵计算／权重按维度拆到多个设备，处理同一输入时协作；流水线并行把不同层或阶段放不同设备，按微批次推进。这些策略可组合，但通信方式、批次含义和保存布局更复杂。

例如张量并行把某线性层输出通道拆两半，各卡算一部分再按后续算子需要汇总；它不是给两卡各一份完整模型的 DDP。FSDP 的分片用于状态存储与取用，也不能只看“切开权重”就等同张量并行。当前都做机制设计，未运行真实多 GPU、跨机、张量并行或流水线。

## 分布式保存与恢复设计

保存检查点需要定义共同的已完成阶段：更新数、优化器／调度器位置、数据顺序与随机状态一致。分片状态可能由多个 rank 写不同块，需要元数据说明参数名、形状、分片布局、world_size、版本和完整状态用途。

| 项目 | 应保存／核对什么 |
| --- | --- |
| 模型 | 参数、必要缓冲、词表或模型配置 |
| 训练状态 | 优化器、调度器、完成的全局更新数 |
| 数据与随机 | 各 rank 随机状态、采样器 epoch／位置、累积阶段 |
| 分片元数据 | 参数布局、rank/world_size、实现版本 |
| 完成标记 | 所有必要分片写完并校验后才发布完整状态 |

设计上先写暂存目录，协调所有必要分片完成，验证元数据与文件完整，再发布完成标记；恢复遇缺分片应拒绝，不随机初始化补上还声称等价。world_size 改变时需要框架支持重分片并实际测试，不能手工改元数据就假定支持。

[PyTorch Distributed Checkpoint 文档](https://docs.pytorch.org/docs/2.14/distributed.checkpoint.html)提供分布式保存接口；[FSDP 文档](https://docs.pytorch.org/docs/2.14/fsdp.html)说明状态相关策略。本机示例只有两份重复 DDP 推理权重，没有实现这套完整协议，也没有做恢复后的轨迹等价验证。

## 动手操作与常见错误

在学习记录写一张设计卡：模型与状态假设、序列／微批次／累积、显卡容量与进程数、策略、激活估算来源、通信条件、目标吞吐预算、保存状态和待验证项。无多卡完成这张卡及本机双CPU演示即可，不把未跑的FSDP方案当成果。

若计算器写estimated_fits却真实失败，检查聚合峰值与激活假设，不将错误吞掉。DDP状态除以卡数是错误估算；grad accumulation次数改变有效批次，需要同步损失归一化和优化器更新。rank文件名不是分片证明，完整恢复必须检查内容与阶段。

### 跟做练习：四卡状态

用输出解释为什么DDP为14.901 GiB而ZeRO3约3.725 GiB。提示：同一1B FP32 Adam假设。

> [!example]- 参考答案
> DDP复制完整16 bytes/参数；ZeRO3粗状态按4进程分摊。实际ZeRO3还需临时聚合与激活。完成标准：明确这是每卡粗状态，不是总集群状态消失。

### 独立练习：有效批次

每进程微批次2、累积3、数据并行4进程，有效全局batch是多少？何时更新一次？

> [!example]- 参考答案
> 2×3×4=24条；每进程完成3个微批次后协作执行一次目标更新，损失归一化需匹配目标。完成标准：不把每微批次step误当累积。

### 迁移练习：缺分片恢复

训练目录缺一个必要rank文件，其他都能加载，可以写恢复成功吗？

> [!example]- 参考答案
> 不能完整恢复。先按元数据检查缺的是必要分片还是冗余副本；缺必要状态应拒绝或寻找完整检查点，记录实际阻碍，不随机补状态声称等价。完成标准：保存用途和布局可核对，恢复声明有实际验证。

下一单元规划：论文精读与技术趋势判断，待编写。
""",
    )
    write(
        "示例工程/README.md",
        r"""
## 从哪里开始

Obsidian 进入 [[../00 长上下文显存与分布式训练学习地图|学习地图]]，VS Code 按下列源码顺序阅读。小模型实测、位置机制与多卡设计分别记录，不把估算当实测。

## 代码导航

- [planning.py](./planning.py)：注意力矩阵与FP32 Adam／分片粗状态预算。
- [position.py](./position.py)：相邻坐标对RoPE、简单位置插值，非完整YaRN。
- [packing.py](./packing.py)：因果／窗口掩码与样本段隔离、边界标签。
- [model.py](./model.py)：208192参数四层因果Decoder、显式注意力、SDPA、逐层重算。
- [experiment.py](./experiment.py)：固定输入／初始化的CPU/CUDA长度、峰值、耗时和数值对照。
- [packing_experiment.py](./packing_experiment.py)：padding／packing实际比较，包含等长反例。
- [distributed_demo.py](./distributed_demo.py)：真正双CPU进程Gloo/DDP、参考更新与复制权重文件。
- [test_context_training.py](./test_context_training.py)：因果、段边界、梯度一致、GPU更新与DDP验证。
- [requirements.txt](./requirements.txt)：复用根共享已有PyTorch，不安装FlashAttention／DeepSpeed。

## 环境与运行

在本单元示例工程的PowerShell执行；根共享 `.venv`。作者Python3.13.12、PyTorch2.14.0+cu130、pytest8.4.2、Ruff0.16.9。CPU可完成基本实验与真实DDP，CUDA路径需要BF16支持。

```powershell
..\..\..\.venv\Scripts\python.exe experiment.py --device cpu --lengths 64 128 256 512 --output-dir report-my-cpu-01
..\..\..\.venv\Scripts\python.exe experiment.py --device cuda --lengths 64 128 256 512 1024 --output-dir report-my-cuda-01
..\..\..\.venv\Scripts\python.exe packing_experiment.py --device cpu --output-dir report-my-packing-cpu-01
..\..\..\.venv\Scripts\python.exe packing_experiment.py --device cuda --output-dir report-my-packing-cuda-01
..\..\..\.venv\Scripts\python.exe distributed_demo.py --output-dir report-my-ddp-01
..\..\..\.venv\Scripts\python.exe -m pytest -q
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

输出目录必须新建。默认SDPA math；`--sdpa-backend flash`仅在已编入且输入兼容环境强制尝试，本机明确不可用，没有静默把math称为Flash。CPU无CUDA内存计数，null代表未测。DDP会合临时文件在系统自有临时目录创建并清理，旧报告不删除。

## 输入、测量与限制

长度实验batch=2、四层、固定合成整数与映射标签，SGD无动量；CPU FP32，CUDA BF16 autocast但权重／梯度／损失FP32。每组预热一步、恢复相同权重、测三次一步更新，中位数含梯度检查与CPU复制，不是纯内核测速。峰值allocated含活跃快照／权重／输入／梯度／临时量，不是显卡总占用。

packing正确隔离样本、重置位置、忽略每条末尾目标；两种方案按同有效目标求均值。密集块掩码不跳过矩阵块计算，等长打包可能更慢且更耗内存。位置／窗口探针不代表真实长文本能力或稀疏加速。

DDP实际两CPU进程、各2样本，对照全局4样本一步更新；两份rank权重是副本，非分片／完整续训状态。没有多GPU、NCCL、FSDP、DeepSpeed、张量并行或分布式完整恢复。实际数值与失败见 [[../参考工程验证记录|作者记录]]。
""",
    )


if __name__ == "__main__":
    main()
