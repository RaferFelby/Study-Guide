---
title: 第 3 讲：用冻结参考与beta读懂DPO损失
tags: [learning, dpo, preference]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 3 讲：用冻结参考与beta读懂DPO损失

> [!nav] 页面导航
> [[01_学习指南/33_DPO与偏好优化/00 DPO与偏好优化学习地图#学习顺序|单元 33：DPO与偏好优化]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/02 计算回答概率并只统计completion|上一讲]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/04 从SFT权重启动CPU与GPU的DPO|下一讲]]

## 本讲要解决的问题与前置

为什么DPO不只最大化chosen概率，还需要reference与beta？本讲从四个log概率构造损失并检查梯度方向。前置第2讲、梯度和 [[01_学习指南/05_数学概率与优化/00 数学概率优化学习地图|sigmoid直觉]]。

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

> [!nav] 路线续读
> 若本讲已到当前路线列出的范围末尾，返回原阶段继续下一项或检查产物；继续单元学习时沿下方“下一讲”。
>
> - [[00_学习路线/03 学习模型训练与大模型算法#分支 A：偏好优化|学习模型训练与大模型算法 · 分支 A：偏好优化]]

## 继续学习

> [!next] 下一步
> [[01_学习指南/33_DPO与偏好优化/逐讲学习/04 从SFT权重启动CPU与GPU的DPO|下一讲：从SFT权重启动CPU与GPU的DPO]]

> [!info]- 练习与记录
> [[01_学习指南/33_DPO与偏好优化/示例工程/README#代码导航|查看源码]] · [[01_学习指南/33_DPO与偏好优化/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 33：DPO与偏好优化|本单元完成清单]]
