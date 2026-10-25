---
title: 第 4 讲：Module优化器与调度器
aliases:
  - Module优化器调度器
tags:
  - pytorch
  - nn-module
  - adamw
  - scheduler
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 4 讲：Module优化器与调度器

> [!nav] 页面导航
> [[01_学习指南/06_PyTorch训练闭环/00 PyTorch训练闭环学习地图#学习顺序|单元 06：PyTorch训练闭环]] · [[01_学习指南/06_PyTorch训练闭环/逐讲学习/03 拼齐变长序列并验证掩码|上一讲]] · [[01_学习指南/06_PyTorch训练闭环/逐讲学习/05 训练验证与指标记录|下一讲]]

## 这一讲要解决什么问题

训练时，谁保存要学习的数字？谁根据梯度修改它们？学习率什么时候改变？本讲按“模型 → 一次更新 → 权重衰减 → 学习率变化”回答这些问题。

前置：能读懂函数、类和字典；知道 Tensor 的形状、`requires_grad` 与 `backward()`。忘记时先回到 [[01_学习指南/01_Python工程化/逐讲学习/01 运行Python并统计工单|Python 基础]]、[[01_学习指南/06_PyTorch训练闭环/逐讲学习/01 Tensor设备与广播|Tensor 基础]]和 [[01_学习指南/05_数学概率与优化/逐讲学习/08 链式法则与反向传播|梯度讲解]]。类是把数据和相关操作放在一起的定义，对象是按这个定义创建的具体实例。

阅读顺序：第一次完成下面三个小实验和跟做练习；第二次阅读 AdamW 并完成独立练习；Transformer 分组与混合精度留到基础熟悉后。

在 VS Code 打开 `01_学习指南/06_PyTorch训练闭环/示例工程/`。在集成终端运行 `Get-Location`，确认最后一级为本单元的“示例工程”。后面每个 Python 代码块各保存成文中指定的文件，均可单独运行，使用根目录共享环境，无需新安装。

> [!contents]- 本讲导航
> - [[#这一讲要解决什么问题|这一讲要解决什么问题]]
> - [[#两层回归模型|两层回归模型]]
> - [[#初始化与输入尺度|初始化与输入尺度]]
> - [[#AdamW 与解耦权重衰减|AdamW 与解耦权重衰减]]
> - [[#学习率调度器|学习率调度器]]
> - [[#混合精度的边界|混合精度的边界]]
> - [[#动手操作|动手操作]]
> - [[#常见错误|常见错误]]
> - [[#练习与答案解析|练习与答案解析]]
> - [[#本讲小结|本讲小结]]

## 两层回归模型

示例工程使用一个小型两层回归模型学习 y = 2x² - 0.5x 加少量噪声。两层指两个 Linear 层，中间用 ReLU；不是说只有两次所有运算，也不是“层数越多一定越好”。

~~~python
from torch import nn


class TinyRegressor(nn.Module):
    def __init__(self, hidden_size=16):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(1, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, features):
        return self.network(features)
~~~

这段结构是源码 [model.py](../示例工程/app/model.py) 的教学摘录；源码还检查隐藏维度必须为正。`class TinyRegressor(nn.Module)` 表示继承 PyTorch 模型基类，复用其参数管理能力。`__init__` 在创建对象时执行，`self` 是当前对象，`super().__init__()` 先初始化基类。把层赋给 `self.network` 时，Module 才能追踪它们的参数。

`nn.Linear(1, hidden_size)` 把每条记录的 1 个特征变成 16 个特征，含权重和偏置；ReLU 把负数变成 0；最后的 Linear 把 16 个特征变成 1 个预测。`nn.Sequential` 按书写顺序连接这些步骤。`forward` 定义前向计算，调用 `model(features)` 时框架会调用它。`model.parameters()` 提供模型登记的参数，优化器靠这些对象更新模型。

### 实验一：先核对数量与形状

保存为 `lesson_03_model.py`：

```python
import torch
from app.model import TinyRegressor, parameter_summary

torch.manual_seed(7)
model = TinyRegressor(hidden_size=16)
features = torch.tensor([[1.0], [2.0], [3.0]])
model.eval()
with torch.no_grad():
    predictions = model(features)
print(parameter_summary(model))
print(list(predictions.shape))
```

运行 `..\..\..\.venv\Scripts\python.exe lesson_03_model.py`，依次应看到 `{'total': 49, 'trainable': 49}` 和 `[3, 1]`。三行输入对应三行输出，每行一个数。这里不要求预测准确，因为模型还未训练。

`manual_seed` 固定本次随机初始化的起点，不能保证跨设备或版本逐位一致。`eval()` 切换到评估模式；`no_grad()` 关闭本段梯度记录，两者职责不同。这个网络没有依赖模式的 Dropout 层，但仍采用明确的推理写法。参数数目由 `parameter_summary` 统计：第一层 16 个权重加 16 个偏置，第二层 16 个权重加 1 个偏置。

## 初始化与输入尺度

默认初始化通常适合许多基础网络，但理解尺度很重要：输入过大、权重过大或激活函数组合不当，会让输出和梯度一开始就异常。手动初始化时要使用与激活函数匹配的策略，并在实验记录中写明改动原因。

参数初始化就是给待学习的数字设置起始值。本节使用 Linear 自带的初始化；暂时只核对形状、数量与输出是否为有限数。熟悉完整训练后，再打印输出均值/标准差和梯度范数，判断尺度是否异常。不要一次同时修改数据、初始化和优化器，否则难以判断变化来自哪里。

### 实验二：手算一次更新，再让优化器执行

先只训练一个权重 `w`：输入为 1，预测为 `w×1`，目标是 2，损失是预测误差的平方。起点 `w=0` 时，损失为 4，梯度为 `2×(0−2)×1=−4`。学习率为 0.1，梯度下降更新得到 `0−0.1×(−4)=0.4`，新损失为 `(0.4−2)²=2.56`。

保存为 `lesson_03_update.py`：

```python
import torch
from torch import nn

model = nn.Linear(1, 1, bias=False)
with torch.no_grad():
    model.weight.fill_(0.0)
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
features = torch.tensor([[1.0]])
targets = torch.tensor([[2.0]])

model.train()
optimizer.zero_grad(set_to_none=True)
predictions = model(features)
loss = ((predictions - targets) ** 2).mean()
loss.backward()
print("更新前损失：", round(loss.item(), 4))
print("梯度：", round(model.weight.grad.item(), 4))
optimizer.step()
print("更新后权重：", round(model.weight.item(), 4))

model.eval()
with torch.no_grad():
    new_loss = ((model(features) - targets) ** 2).mean()
print("更新后损失：", round(new_loss.item(), 4))
```

运行 `..\..\..\.venv\Scripts\python.exe lesson_03_update.py`。四行数字应依次为 `4.0`、`-4.0`、`0.4`、`2.56`。`bias=False` 去掉偏置，使模型只有一个待训练数字；`fill_` 修改原权重，初始赋值放在 `no_grad` 内。

`SGD` 是随机梯度下降优化器，本例无动量、只有一个样本，更新就是上面的公式。`lr` 是学习率。`zero_grad(set_to_none=True)` 清除上次梯度；`backward()` 计算并存入 `.grad`；`step()` 才按梯度改权重。`** 2` 表示平方，`mean()` 对误差取平均，`item()` 从单元素张量取得 Python 数，`round(..., 4)` 便于查看浮点结果。下一讲把这个顺序放进多个批次的循环。

## AdamW 与解耦权重衰减

有时当前梯度会因样本不同而抖动。Adam 保存历史梯度的平滑统计：一阶移动平均跟踪带正负号的梯度，二阶移动平均跟踪梯度平方。这里“移动平均”指每次保留一部分旧统计，再加入一部分新值；二阶统计不是二阶导数。

例如旧平均为 0、新梯度为 2、旧值权重为 0.9，则新一阶平均为 `0.9×0+0.1×2=0.2`。若平方平均的旧值权重为 0.999，则新平方平均为 `0.999×0+0.001×4=0.004`。`betas=(0.9, 0.999)` 控制这两个权重。实际 Adam 还做起步偏差修正，并用平方平均的平方根和小常数缩放更新；暂时无需手写完整优化器。

权重衰减（`weight_decay`）让参数在更新时向零收缩。AdamW 把它作为与梯度统计分开的步骤；在常见写法中，衰减部分为 `w ← (1−学习率×衰减系数)w`。显式 L2 正则则把参数平方和加进损失，其导数进入梯度统计。两者在自适应更新中通常不等价。这里比较的是耦合 L2 的 Adam；新版接口也可能提供解耦选项，不能仅凭优化器名称判断配置。

要单独观察衰减，保存 `lesson_03_decay.py`：

```python
import torch

weight = torch.nn.Parameter(torch.tensor([1.0]))
optimizer = torch.optim.AdamW([weight], lr=0.1, weight_decay=0.2)
optimizer.zero_grad(set_to_none=True)
loss = (weight * 0.0).sum()
loss.backward()
optimizer.step()
print(round(weight.item(), 4))
```

运行 `..\..\..\.venv\Scripts\python.exe lesson_03_decay.py`，输出 `0.98`，对应 `(1−0.1×0.2)×1`。`Parameter` 把张量标记为可训练参数；这里传给优化器的列表只有它。乘零的损失让梯度是实际存在的零张量，从而隔离衰减。若只清梯度、没有反向传播，`.grad` 为 None，PyTorch 会跳过该参数，不能据此演示衰减。

这不是“AdamW 永远更好”的结论。应记录 optimizer 类型、learning rate、weight_decay、betas 和参数分组，尤其是是否对 bias 或归一化参数使用衰减。

## 学习率调度器

学习率调度器按规则改变优化器里的学习率。`epoch` 指完整遍历训练数据一次，`batch` 是其中一小批数据；本实验每轮只有一个批次。`StepLR(step_size=2, gamma=0.5)` 在本节约定下每完成两轮把学习率乘 0.5。它根据调用次数推进，放错循环位置就会改变实际周期。

保存 `lesson_03_schedule.py`：

```python
import torch

weight = torch.nn.Parameter(torch.tensor([0.0]))
optimizer = torch.optim.SGD([weight], lr=0.1)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
for epoch in range(1, 5):
    used_learning_rate = optimizer.param_groups[0]["lr"]
    optimizer.zero_grad(set_to_none=True)
    loss = ((weight - 2.0) ** 2).mean()
    loss.backward()
    optimizer.step()
    scheduler.step()
    next_learning_rate = optimizer.param_groups[0]["lr"]
    print(epoch, round(used_learning_rate, 4), round(next_learning_rate, 4))
```

运行 `..\..\..\.venv\Scripts\python.exe lesson_03_schedule.py`，预期：

```text
1 0.1 0.1
2 0.1 0.05
3 0.05 0.05
4 0.05 0.025
```

每行是轮次、本轮实际使用的学习率、下一轮将使用的学习率。`param_groups` 是参数组字典组成的列表，`[0]["lr"]` 读取第一组的学习率。本例先执行参数更新，轮末再调度；若每批调用，周期就变为每两批。按验证指标调整的 `ReduceLROnPlateau` 还需要传入指标，不能机械照搬本例。配套完整工程可能使用不同调度器，阅读时核对其创建参数和调用位置。

## 混合精度的边界

这部分可稍后学。混合精度让部分运算使用较低精度，其他运算保留较高精度；潜在收益需结合设备、模型与计时验证。`autocast` 按规则选择运算精度。FP16 的数值范围较窄，小梯度可能下溢成零；梯度缩放器先放大损失再反传，更新前还原梯度并检查非有限值。BF16 的指数范围不同，通常不需要同样的缩放。

本讲的小实验统一使用 CPU 浮点数。后面在 [training.py](../示例工程/app/training.py) 结合完整顺序学习 CUDA 混合精度；CPU 也有特定混合精度支持，但本工程选择 CPU 关闭，不应写成框架完全不支持。启用后仍需记录 dtype、梯度缩放与实际收益，不能只看到 CUDA 可用就认定一定更快。

## 动手操作

1. 运行四个独立文件，记录 49 个参数、一次更新的四个数字、0.98 和四行学习率。
2. 不运行代码，先预测学习率 0.05 时单步权重和新损失，再修改实验二核对。
3. 打开工程 `train.py` 搜索优化器与调度器创建，打开 `app/training.py` 搜索反向传播，指出它们与小实验对应的位置。完整验证与保存流程在后两讲学习。

## 常见错误

- 忘记调用 super().__init__，导致参数没有注册。
- 创建模型后才创建优化器，随后替换模型参数却没有更新优化器引用。
- 保存了 model.state_dict，却没有保存优化器和调度器状态，续训时动量丢失。
- 调度器调用频率与预期不一致，学习率曲线悄悄改变。
- `ModuleNotFoundError: app`：检查终端是否位于本单元示例工程，脚本是否保存于该目录；不要全局加入其他单元的 app。
- 修改参数时报原地操作错误：初始赋值放在 `torch.no_grad()` 中；训练时由优化器更新。
- 读到 `.grad` 为 None：确认已调用 backward，且参数参与了损失计算。不要用吞掉异常的方式略过它。

## 练习与答案解析

### 跟做练习：数参数

输入维度 1、隐藏维度 16、输出维度 1 的两层网络有多少可训练参数？

> [!example]- 参考答案
> 第一层 1×16 个权重加 16 个 bias，第二层 16×1 个权重加 1 个 bias，总数为 49。将实验一隐藏维度改为 8 后，总数变为 `8+8+8+1=25`，输出形状仍为 `[3,1]`。再将实验二学习率改为 0.05，更新后权重为 0.2，新损失为 3.24。完成判断：能从公式解释这些变化。

### 独立练习

写一个函数打印每个参数组的学习率和 weight_decay。完成标准：能发现不同参数组是否真的使用了不同设置。

提示：遍历 `optimizer.param_groups`，每个组都是字典；使用 `enumerate` 同时取得组编号。另建 `lesson_03_groups.py`，先尝试，再对照完整答案。

> [!example]- 独立练习参考答案与解析
> ```python
> import torch
> from app.model import TinyRegressor
>
> def print_parameter_groups(optimizer):
>     for index, group in enumerate(optimizer.param_groups):
>         print(index, group["lr"], group["weight_decay"])
>
> model = TinyRegressor()
> optimizer = torch.optim.AdamW([
>     {"params": model.network[0].parameters(), "lr": 0.01, "weight_decay": 0.1},
>     {"params": model.network[2].parameters(), "lr": 0.001, "weight_decay": 0.0},
> ])
> print_parameter_groups(optimizer)
> ```
> 用相同共享解释器运行该文件，输出 `0 0.01 0.1`、`1 0.001 0.0`。Sequential 的下标 0 和 2 分别取两层 Linear，下标 1 是没有参数的 ReLU。此处按层分组只为观察配置，不代表推荐的训练策略。完成判断：把第二组学习率改为 0.002，打印应只改变第二行；每个参数只属于一组。

### 迁移练习

为一个 Transformer 训练配置设计参数分组：哪些参数可能不使用 weight decay？说明这只是常见工程策略，仍需结合模型和实验验证。

先用两层网络练习相同机制：矩阵权重衰减为 0.1，偏置不衰减，两组学习率均为 0.001。完成判断：两组分别有 32 和 17 个标量，总数为 49，没有遗漏或重复。提示：`named_parameters()` 每次给出参数名和参数对象；本例偏置名称以 `.bias` 结束。

> [!example]- 迁移练习参考答案与解析
> 保存为 `lesson_03_transfer.py`，按前面的方式运行：
> ```python
> import torch
> from app.model import TinyRegressor
>
> model = TinyRegressor()
> decay_parameters = []
> no_decay_parameters = []
> for name, parameter in model.named_parameters():
>     if name.endswith(".bias"):
>         no_decay_parameters.append(parameter)
>     else:
>         decay_parameters.append(parameter)
> optimizer = torch.optim.AdamW([
>     {"params": decay_parameters, "weight_decay": 0.1},
>     {"params": no_decay_parameters, "weight_decay": 0.0},
> ], lr=0.001)
> for group in optimizer.param_groups:
>     count = 0
>     for parameter in group["params"]:
>         count += parameter.numel()
>     print(count, group["weight_decay"])
> ```
> 输出 `32 0.1`、`17 0.0`。`endswith` 判断名称后缀，`append` 把对象加入对应列表，`numel` 给出参数元素数。Transformer 中常见做法还会把归一化层的缩放参数放进不衰减组；本例没有归一化层，这段名称规则不能直接概括所有模型。进入单元 08 后应按具体模块和参数名称核对，再比较相同划分、种子和预算下的验证损失，不能仅凭分组名称判断效果。

## 本讲小结

nn.Module 管理模型结构和参数，优化器管理更新规则，调度器管理学习率变化。AdamW 的关键是解耦权重衰减；混合精度要和设备、梯度缩放、数值稳定性一起判断。

接口参考：[PyTorch 优化器与学习率调度说明](https://docs.pytorch.org/docs/2.14/optim.html)、[StepLR 参数说明](https://docs.pytorch.org/docs/2.14/generated/torch.optim.lr_scheduler.StepLR.html)。本讲调用还需以共享环境的实际运行结果核对。

## 继续学习

> [!next] 下一步
> [[01_学习指南/06_PyTorch训练闭环/逐讲学习/05 训练验证与指标记录|下一讲：训练验证与指标记录]]

> [!info]- 练习与记录
> [[01_学习指南/06_PyTorch训练闭环/示例工程/README#代码导航|查看源码]] · [[01_学习指南/06_PyTorch训练闭环/示例工程/README#运行训练|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 06：PyTorch 与训练闭环|本单元完成清单]]
