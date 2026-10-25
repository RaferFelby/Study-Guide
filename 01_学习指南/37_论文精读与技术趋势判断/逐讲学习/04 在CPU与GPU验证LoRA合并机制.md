---
title: 第 4 讲：在CPU与GPU验证LoRA合并机制
tags: [learning, paper-reading, beginner]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 4 讲：在CPU与GPU验证LoRA合并机制

> [!nav] 页面导航
> [[01_学习指南/37_论文精读与技术趋势判断/00 论文精读与技术趋势判断学习地图#学习顺序|单元 37：论文精读与技术趋势判断]] · [[01_学习指南/37_论文精读与技术趋势判断/逐讲学习/03 检查实验对照消融与复现条件|上一讲]] · [[01_学习指南/37_论文精读与技术趋势判断/逐讲学习/05 评估技术成熟度引入与退出成本|下一讲]]

## 本讲任务与前置

验证LoRA线性分支能合并，检查基础权重冻结，并运行漏缩放反例。需要矩阵乘法、PyTorch前向／梯度与LoRA基础；可到 [[01_学习指南/26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图|LoRA详细教程]]复习。本讲重新解释形状与执行顺序。

完成标准：自己的CPU报告合并通过、基础权重不变，GPU可用时另验证；漏掉缩放会出现明显差异。知道这不是模型质量／速度／长期训练实验。

## 要解决什么问题与等式

训练时保留基础权重W0，再加可训练增量sBA。推理时，若它是同一线性加法分支、没有额外非线性或训练随机操作，可先计算Wmerged=W0+sBA，再只执行合并线性层。原文[LoRA v2方法段](https://arxiv.org/abs/2106.09685v2)支持这种线性设计；我们验证其数值实现，不直接推断服务延迟。

输入每行8个数，W0形状6×8，A为2×8，B为6×2，BA为6×8；rank（秩上限）r=2表示更新由两个中间维度表示。alpha=4是缩放参数，s=alpha/r=2。A/B可训练参数2×8+6×2=28，基础权重48，另有6个冻结偏置。

PyTorch F.linear(inputs,weight,bias)用inputs乘weight的转置；输入4×8，输出4×6。分支先经A变4×2，再经B变4×6；合并先算6×8的BA，再对输入线性计算。不要因行向量写法把BA误写成AB。

## 最小示例：非零分支与负例

在示例工程新建lesson_04.py：

```python
import torch
from merge_probe import AdaptedLinear, compare_merge

torch.manual_seed(2026)
model = AdaptedLinear(rank=2, alpha=4)
result = compare_merge(model, torch.randn(4, 8))
print(model.matrix_a.shape, model.matrix_b.shape)
print(result["passed"])
print(result["max_abs_difference"] < 1e-6)
print(result["missing_scale_max_abs_difference"] > 0.001)
```

```powershell
..\..\..\.venv\Scripts\python.exe lesson_04.py
```

预期形状torch.Size([2,8])与torch.Size([6,2])，随后三个True。正确合并误差接近浮点舍入；负例用W0+BA漏掉s=2，导致明显不等价。负例说明检查有能力发现这类错误，而不是只比较两个都返回零的实现。

## 逐步读实现与初始化

打开merge_probe.py：base_weight和bias的requires_grad=False，A/B为可训练Parameter。forward返回基础线性加缩放低秩分支；merged_weight先复制基础权重再加增量，不覆盖原W0，便于验证与退出。

compare_merge用eval与inference_mode，关闭梯度记录；torch.allclose按atol=1e-6、rtol=1e-5比较，而不是要求每位完全一样。atol是绝对误差容忍，rtol是随参照数值大小的相对容忍；它们是当前小FP32实验选择，不是所有模型精度的万能阈值。

本探针B初始非零，确保增量不是零。原方法常见零B初始化使初始增量为零；测试另验证这种起点，第一步A梯度为零而B可更新。非零B探针是教学验证条件，不伪称原论文完整训练初始化。

## 动手操作：完整CPU与GPU验证

```powershell
..\..\..\.venv\Scripts\python.exe merge_probe.py --device cpu --output-dir report-my-cpu-01
```

新目录保存report.json与probe.pt。程序在更新前检查合并，然后用SGD仅更新A/B一步，再检查合并与W0冻结。训练顺序为train→zero_grad→前向／均方损失→backward→有限梯度检查→step；输出报告明确training_steps=1。

CUDA可用时另运行：

```powershell
..\..\..\.venv\Scripts\python.exe merge_probe.py --device cuda --output-dir report-my-cuda-01
```

权重、输入、目标先在CPU按同一种子生成再移设备；统一FP32，CUDA关闭TF32近似矩阵模式，便于检查小误差。两设备仍可能有舍入差异。报告before/after均passed、base_frozen=True；速度和任务质量均未测。不要用这一步随机回归损失代表论文任务成绩。

## 预期判断与常见错误

适配器文件与基础版本、目标层、rank、alpha、精度要配套；直接重复合并会加两次增量。本函数不原地改基础权重，测试也核对调用前后状态未变。真实量化或不同分支机制应另行验证，不能默认同一容差足够。

报形状不合法：核对A/B顺序与rank，当前rank不能大于最小输入／输出维度。报目录已存在：换新名。基础权重变化：检查优化器参数名单与requires_grad，不删冻结断言。误差过大：先看缩放、转置与重复合并，不扩大阈值掩盖错误。probe.pt只含推理状态，不是精确续训检查点。

## 分级练习与答案解析

### 跟做练习：数参数

给出W0、A、B形状和可训练参数数。提示：偏置单独冻结。

> [!example]- 参考答案
> W0=6×8、A=2×8、B=6×2，A/B共28，W0共48，偏置6。完成标准：不把冻结的基础参数说成从内存消失。

### 独立练习：漏缩放

alpha=rank时，漏掉scale是否能被当前负例发现？

> [!example]- 参考答案
> scale=1时不会有差异，所以负例特意选alpha=4、rank=2。完成标准：知道测试输入要激活所检查的错误，不因一个不起作用的反例通过就宣称实现正确。

### 迁移练习：合并后质量

数值等价通过，可以保证真实模型所有任务质量与延迟吗？

> [!example]- 参考答案
> 只能支持当前线性机制与条件下的等价；真实模型要核对全部目标层、精度、量化、路由及实际任务和服务测量。完成标准：保留本实验没有测速／真实任务的边界。

## 继续学习

> [!next] 下一步
> [[01_学习指南/37_论文精读与技术趋势判断/逐讲学习/05 评估技术成熟度引入与退出成本|下一讲：评估技术成熟度引入与退出成本]]

> [!info]- 练习与记录
> [[01_学习指南/37_论文精读与技术趋势判断/示例工程/README#代码导航|查看源码]] · [[01_学习指南/37_论文精读与技术趋势判断/示例工程/README#环境与运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 37：论文精读与技术趋势判断|本单元完成清单]]
