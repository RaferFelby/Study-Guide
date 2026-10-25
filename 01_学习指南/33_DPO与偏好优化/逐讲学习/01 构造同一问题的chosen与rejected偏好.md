---
title: 第 1 讲：构造同一问题的chosen与rejected偏好
tags: [learning, dpo, preference]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 1 讲：构造同一问题的chosen与rejected偏好

> [!nav] 页面导航
> [[01_学习指南/33_DPO与偏好优化/00 DPO与偏好优化学习地图#学习顺序|单元 33：DPO与偏好优化]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/02 计算回答概率并只统计completion|下一讲]]

## 本讲要解决的问题与前置

SFT教模型模仿一个回答；如果同一问题有两个回答，我们想表达“更喜欢哪一个”，怎样存数据？本讲先定义偏好方向及依据，不把更喜欢自动等同于事实正确。

前置是 [[01_学习指南/26_SFT与LoRA全流程/逐讲学习/01 整理指令数据并只监督答案|SFT 与回答监督]]、[[01_学习指南/26_SFT与LoRA全流程/逐讲学习/02 按来源切分并理解拼接边界|按来源分组隔离]] 和 Python 列表／字典。陌生语法沿单元 01 详细讲解复习。当前工程独立构造合成偏好，不读取工具数据构造单元的文件，不下载模型；需要制作带工具轨迹的数据包时，再进入单元 31。

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

## 继续学习

> [!next] 下一步
> [[01_学习指南/33_DPO与偏好优化/逐讲学习/02 计算回答概率并只统计completion|下一讲：计算回答概率并只统计completion]]

> [!info]- 练习与记录
> [[01_学习指南/33_DPO与偏好优化/示例工程/README#代码导航|查看源码]] · [[01_学习指南/33_DPO与偏好优化/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 33：DPO与偏好优化|本单元完成清单]]
