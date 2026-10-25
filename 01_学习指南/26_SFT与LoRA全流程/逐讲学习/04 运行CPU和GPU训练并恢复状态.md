---
title: 第 4 讲：运行CPU和GPU训练并恢复状态
tags: [learning, pytorch, sft, lora]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 4 讲：运行CPU和GPU训练并恢复状态

> [!nav] 页面导航
> [[01_学习指南/26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图#学习顺序|单元 26：SFT与LoRA全流程]] · [[01_学习指南/26_SFT与LoRA全流程/逐讲学习/03 手写LoRA看懂秩缩放与冻结|上一讲]] · [[01_学习指南/26_SFT与LoRA全流程/逐讲学习/05 比较Base与两组LoRA的保留集表现|下一讲]]

## 本讲要解决的问题与前置

这一讲亲自运行微调，理解设备、精度、梯度累积及恢复。前置是第3讲冻结参数和 [[01_学习指南/06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|训练闭环]]；PyTorch基本顺序仍是train→清梯度→前向→损失→反向→更新。新概念按下面顺序加入，不需要先安装训练框架。

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

## 继续学习

> [!next] 下一步
> [[01_学习指南/26_SFT与LoRA全流程/逐讲学习/05 比较Base与两组LoRA的保留集表现|下一讲：比较Base与两组LoRA的保留集表现]]

> [!info]- 练习与记录
> [[01_学习指南/26_SFT与LoRA全流程/示例工程/README#代码导航|查看源码]] · [[01_学习指南/26_SFT与LoRA全流程/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 26：SFT与LoRA全流程|本单元完成清单]]
