---
title: 第 3 讲：检查Tensor布局并阅读原生算子路径
tags: [learning, cpp, cuda, beginner]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 3 讲：检查Tensor布局并阅读原生算子路径

> [!nav] 页面导航
> [[01_学习指南/38_CPP算子与CUDA/00 C++算子与CUDA学习地图#学习顺序|单元 38：C++算子与CUDA]] · [[01_学习指南/38_CPP算子与CUDA/逐讲学习/02 用引用指针与容器理解内存所有权|上一讲]] · [[01_学习指南/38_CPP算子与CUDA/逐讲学习/04 连接C++函数并注册可求导算子|下一讲]]

## 要解决的问题与前置

一个Tensor看起来是矩阵，底层却不是“每一行一个Python列表”。要把地址交给C++，先弄清元素存放顺序。前置是上一讲指针与所有权，以及 [[01_学习指南/06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|PyTorch基础]]中的Tensor与dtype。

本讲阅读顺序：shape与stride → 转置最小实验 → 为什么契约拒绝非连续输入 → 阅读ATen核心路径。

## 概念与直觉：shape不等于内存布局

shape（形状）是每个维度的长度；stride（步幅）是在某维下标加1，需要跨过多少个元素。二维索引(i,j)相对首元素的位置，在本例是`i * stride[0] + j * stride[1]`。步幅单位是元素，不是字节；float32的每个元素占4字节，算字节距离还要乘4。

连续Tensor按标准顺序紧密排列。转置可以只改变shape和stride，而共享原存储；看起来行列交换，不一定真的搬动数据。把它想成给同一排座位换一张编号表；实际Tensor还包含存储偏移、dtype和设备信息，这个类比不能表达全部视图机制。

## 完整最小实验与逐步解释

在本工程新建`lesson_03.py`，使用共享解释器运行：

```python
import torch

values = torch.arange(6, dtype=torch.float32).reshape(2, 3)
transposed = values.T
copied = transposed.contiguous()
print(values.tolist(), values.stride(), values.is_contiguous())
print(transposed.tolist(), transposed.stride(), transposed.is_contiguous())
print(copied.tolist(), copied.stride(), copied.is_contiguous())
print("转置共享地址:", values.data_ptr() == transposed.data_ptr())
print("连续化新地址:", copied.data_ptr() != transposed.data_ptr())
```

`arange(6)`生成0～5；`dtype=float32`让后续与C++的float约定一致。`reshape(2,3)`变成两行三列，`.T`是本例二维转置。`contiguous()`在必要时创建连续布局；已经连续时可能直接返回原Tensor，不保证每次都复制。`data_ptr()`给首元素地址，本例只比较，不自行读写任意地址。

预期三组列表分别为`[[0,1,2],[3,4,5]]`、`[[0,3],[1,4],[2,5]]`、与转置相同的列表；实际浮点打印带`.0`。步幅依次`(3,1)`、`(1,3)`、`(2,1)`；连续标志True、False、True；两个地址判断均True。地址的具体数值每次可不同，不作为验收常量。

现在手算：原values[1,2]的位置=1×3+2×1=5。transposed[2,1]的位置=2×1+1×3=5，也读到5。复制后的同一逻辑索引位置=2×2+1×1=5；此处数字恰相同不表示所有索引都同位置，transposed[1,0]的位置1，copied[1,0]的位置2。

## 为什么教学算子要拒绝非连续输入

本工程CPU/CUDA循环都按`input[index]`读一段连续float。它们没有收到shape、stride或广播规则，不能正确表达任意视图语义。Python边界明确检查float32和连续性；需要转置结果时由调用者写`.contiguous()`，让复制成本显式出现。

GPU地址也不能拿给CPU函数解引用。数值地址看起来都是整数，但属于不同设备的内存空间；必须根据`value.device.type`选择对应实现。误用不是一个可以安全catch的普通Python计算错误，可能损坏进程，因此边界校验必须在调用原生函数前完成。

## 读一个ATen核心路径：先看职责，再看宏

ATen是PyTorch中提供Tensor操作的C++核心部分。Dispatcher（分发器）根据算子注册、设备等信息选择实现；不要把所有工作都归给某一个核函数文件。

打开 [PyTorch官方threshold CUDA源码](https://github.com/pytorch/pytorch/blob/main/aten/src/ATen/native/cuda/ActivationThresholdKernel.cu)。这是2026-10-14阅读的main分支，不声称是本机wheel的精确源码；页面可变，做严格复现时应固定commit。这里读的是threshold路径，不能把它全部当成ReLU的唯一实现。

先在网页按Ctrl+F依次查`REGISTER_DISPATCH`、`threshold_kernel_cuda`、`AT_DISPATCH_ALL_TYPES_AND2`、`threshold_kernel_impl`、`gpu_kernel_with_scalars`。登记把stub接到设备实现；类型分支选择实际元素类型；模板得到对应类型实现；迭代设施按元素执行条件选择。真正的逐元素规则是“x不大于阈值时取替代值，否则取other”。当前只需解释这个核心路径，不展开每个宏。

TensorIterator是处理迭代布局等工作的原生设施，本工程简单指针循环没有复制它的全部能力。官方实现包含多种dtype与通用迭代支持；本例float32连续输入是教学限制，不是PyTorch算子普遍限制。到 [官方C++与CUDA算子教程](https://docs.pytorch.org/tutorials/advanced/cpp_custom_ops.html) 可了解常见的`TORCH_LIBRARY`注册、ATen Tensor与编译扩展流程；本单元实际编译的是C接口DLL，下一讲会把两种边界说清楚。

## 动手与常见错误

先运行布局例子，再手写上面两个索引位置；打开本工程`operator_impl.py`的`check_input`，把三个限制和CPU循环对应起来。

- 误以为T总复制：用地址与stride一起验证，而不是仅看打印矩阵。
- 误以为连续化没有成本：复制也消耗时间与显存，在端到端评测里单独说明。
- 只看shape就给裸指针：补上dtype、device、contiguous和元素数检查。
- 网页文件或行号变了：记录访问日期与分支，按符号搜索；不要伪称已核对本机提交。

## 三层练习

**跟做：** 跑布局例子并解释三个stride。标准：能用元素位置公式解释转置共享存储。

**独立：** 算`values[1,0]`和`transposed[0,1]`的位置。提示：使用各自stride。标准：都得到位置3和元素3。

**迁移：** 为“接收转置矩阵的自定义函数”写两种方案，并列成本。标准：方案一先连续化并记录复制；方案二传shape/stride并实现正确索引，还需新边界测试，不只删掉检查。

> [!example]- 参考答案与过程
> 原矩阵(3,1)，第二行起点3；转置(1,3)，第二列起点3。连续副本(2,1)重排存储。独立题1×3+0=3，0×1+1×3=3。迁移若仍用本工程核函数，就只能选显式连续化；“支持任意stride”涉及索引计算和广播规则，属于新的实现工作。源码阅读卡可写：符号入口、类型选择、元素规则、布局设施、当前未展开的部分；不要写“已经懂全部ATen”。

## 继续学习

> [!next] 下一步
> [[01_学习指南/38_CPP算子与CUDA/逐讲学习/04 连接C++函数并注册可求导算子|下一讲：连接C++函数并注册可求导算子]]

> [!info]- 练习与记录
> [[01_学习指南/38_CPP算子与CUDA/示例工程/README#代码导航|查看源码]] · [[01_学习指南/38_CPP算子与CUDA/示例工程/README#环境与运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 38：C++、算子与CUDA|本单元完成清单]]
