---
title: 第 1 讲：Tensor设备与广播
aliases:
  - Tensor设备广播
tags:
  - pytorch
  - tensor
  - broadcasting
  - autograd
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 1 讲：Tensor设备与广播

> [!nav] 页面导航
> [[01_学习指南/06_PyTorch训练闭环/00 PyTorch训练闭环学习地图#学习顺序|单元 06：PyTorch训练闭环]] · [[01_学习指南/06_PyTorch训练闭环/逐讲学习/02 Dataset与DataLoader|下一讲]]

## 这一讲要解决什么问题

PyTorch 的 Tensor 不只是“装数字的数组”。它还带有 dtype、device、shape，并且可以参与自动求导。训练报错经常来自 CPU 与 GPU 混用、整数张量参与浮点计算、广播结果形状误解或梯度图被意外切断。

## 开始前要会什么

本讲用到 Python 变量、导入模块和运行脚本。如果“向量、矩阵、shape”这些词还不熟，先复习 [[01_学习指南/05_数学概率与优化/逐讲学习/01 向量矩阵与张量形状|单元 05 第 1 讲]]；本讲会把 batch 的形状写成“样本数 × 每个样本的特征数”。运行 PyTorch 示例前，按仓库根目录 [[README|README 中的共享环境说明]] 检查解释器和安装方式。

## Tensor 的四个基本属性

- shape：每一维有多少元素，例如 batch×features。
- dtype：数字类型，例如 float32、float16、int64；标签索引通常是整数，模型计算通常是浮点数。
- device：数据在 CPU 还是 CUDA GPU 上。参与同一运算的 Tensor 通常必须在同一设备。
- requires_grad：是否记录对该 Tensor 的梯度；模型参数通常需要，输入是否需要取决于任务。

~~~python
import torch

x = torch.tensor([[1.0, 2.0], [3.0, 4.0]], dtype=torch.float32)
print(x.shape, x.dtype, x.device)
parameter = torch.tensor(2.0, requires_grad=True)
loss = (parameter * 3) ** 2
loss.backward()
print(parameter.grad)
~~~

预期 shape 是 torch.Size([2, 2])，dtype 是 torch.float32，device 通常是 cpu，梯度是 36。最后一个结果来自 d(3w)²/dw = 18w，在 w=2 时为 36。

## 广播：为了逐元素运算自动扩展

广播允许形状兼容的 Tensor 在逐元素加减乘除时对齐维度。例如 batch×features 的矩阵加上 features 长度的偏置，偏置会被视为对每个 batch 重复使用。广播不是真的复制全部数据，但结果必须能按规则解释。

先用一个小例子观察最后一维如何对齐。把下面代码保存为单元 06 示例工程根目录中的 `broadcast_demo.py`：

~~~python
import torch

features = torch.tensor([
    [1.0, 2.0, 3.0],
    [4.0, 5.0, 6.0],
])
bias = torch.tensor([0.1, 0.2, 0.3])

adjusted_features = features + bias
print(adjusted_features)
print(adjusted_features.shape)
~~~

在该示例工程目录的 VS Code 终端运行 `..\..\..\.venv\Scripts\python.exe broadcast_demo.py`。输出形状为 `torch.Size([2, 3])`；每一行都分别加上 `[0.1, 0.2, 0.3]`，因此结果约为 `[[1.1, 2.2, 3.3], [4.1, 5.2, 6.3]]`。小数的显示可能带有极小的浮点误差。

为什么能相加？从右向左比较维度：`features` 的形状是 `(2, 3)`，`bias` 的形状是 `(3,)`。最后一维都是 3，所以长度为 3 的偏置会应用到两行。若偏置形状是 `(2,)`，它会和最后一维 3 比较，因 2 与 3 不相等而报维度不兼容错误。

### 给每个样本加一个标量偏置

有时我们要给第一行加 10，给第二行加 20。此时偏置原本是一维的 `(2,)`，需要增加一列维度，变成 `(2, 1)`。在刚才的代码后加入：

~~~python
sample_bias = torch.tensor([10.0, 20.0])
row_bias = sample_bias[:, None]

print(row_bias.shape)
print(features + row_bias)
~~~

`sample_bias[:, None]` 中：

- `:` 表示取这一维的全部元素；
- `None` 在该位置插入一个长度为 1 的新维度。

形状变化可以这样读：

| 张量 | 形状 | 含义 |
|---|---|---|
| `sample_bias` | `(2,)` | 两个样本各一个偏置 |
| `row_bias` | `(2, 1)` | 两个样本各一行、每行一个数 |
| `features` | `(2, 3)` | 两个样本、每个样本三个特征 |

相加时，广播规则会把 `row_bias` 末尾的长度 1 对齐到 `features` 的长度 3，让每一行都加上自己的标量偏置。它只是在运算时按规则匹配，不需要提前复制出 6 个偏置值。

> [!example] 预期结果
> 输出形状：`torch.Size([2, 3])`  
> 输出数值：`[[11, 12, 13], [24, 25, 26]]`

矩阵乘法和广播加法不是一回事：线性层通常先做矩阵乘法，再加偏置。看到相同数字不代表 shape 规则相同，必须写出每个维度的含义。

## 内存布局与 contiguous

转置或切片可能产生非连续视图。视图与原 Tensor 共享底层存储，修改一个可能影响另一个；某些操作要求连续内存，可以使用 contiguous 创建合适布局的副本。不要为了“看到 contiguous 就调用”而无目的复制，因为复制会增加时间和显存。

## 自动求导的最小边界

调用 backward 后，梯度默认累加到 parameter.grad。训练循环必须在下一批次前清零梯度，否则本批和上批的梯度会叠加。推理或验证时通常使用 torch.no_grad()，避免构建不需要的计算图。

## 动手操作

1. 在 `broadcast_demo.py` 中把 `bias` 临时改成两个数，例如 `[10.0, 20.0]`，运行并观察形状不匹配错误。
2. 把 `bias` 恢复成三个数，再按上面的例子加入 `sample_bias[:, None]`，运行后确认每一行都加上对应的标量。
3. 在示例工程的 `app/data.py` 中找到 `build_loaders`，查看它如何提供训练 batch；打印 batch 的 `shape`、`dtype` 和 `device`。
4. 对照模型输入要求，说明这些属性各自表示什么。
5. 把一个 `float32` 输入改成 `int64`，观察线性层为何出现类型不匹配。
6. 连续调用两次 `backward()`，查看梯度是否累加；再调用 `optimizer.zero_grad(set_to_none=True)` 后比较。

## 常见错误

- 只把模型移动到 GPU，却忘记把 batch 移动到同一设备。
- 把分类标签转换成 float，传给要求整数类别索引的损失函数。
- 验证阶段忘记 no_grad，导致额外显存占用。
- 忽略梯度累加，在每批次不清零。

## 练习与答案解析

### 跟做练习：预测广播结果

输入 shape 为 (4, 3)，偏置 shape 为 (3,)，相加后结果是什么 shape？如果偏置改成 (4,)，是否仍然能表示每个特征的偏置？

> [!example]- 参考答案
> (4, 3) 加 (3,) 会把长度 3 对齐到最后一维，结果是 (4, 3)。长度 4 对齐时不能直接表示每个特征偏置；除非 reshape 为 (4, 1)，它表达的是每个样本一个标量偏置，语义不同。

### 独立练习

写一个函数打印模型中每个参数的 name、shape、dtype、device 和 requires_grad。完成标准：能发现一个模型是否有参数被冻结或设备不一致。

### 迁移练习

为一个变长文本批次设计 shape 和 padding mask，说明为什么不能只把不同长度列表直接堆叠成一个 Tensor。

## 本讲小结

Tensor 的 shape、dtype、device 和梯度状态共同决定运算是否正确。训练前先检查这些属性，通常比看到报错后盲目更换代码更有效。

## 继续学习

> [!next] 下一步
> [[01_学习指南/06_PyTorch训练闭环/逐讲学习/02 Dataset与DataLoader|下一讲：Dataset与DataLoader]]

> [!info]- 练习与记录
> [[01_学习指南/06_PyTorch训练闭环/示例工程/README#代码导航|查看源码]] · [[01_学习指南/06_PyTorch训练闭环/示例工程/README#运行训练|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 06：PyTorch 与训练闭环|本单元完成清单]]
