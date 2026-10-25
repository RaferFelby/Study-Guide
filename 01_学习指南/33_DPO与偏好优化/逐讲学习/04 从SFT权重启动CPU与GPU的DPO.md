---
title: 第 4 讲：从SFT权重启动CPU与GPU的DPO
tags: [learning, dpo, preference]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 4 讲：从SFT权重启动CPU与GPU的DPO

> [!nav] 页面导航
> [[01_学习指南/33_DPO与偏好优化/00 DPO与偏好优化学习地图#学习顺序|单元 33：DPO与偏好优化]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/03 用冻结参考与beta读懂DPO损失|上一讲]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/05 比较BaseSFT与DPO并分析长度偏差|下一讲]]

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

## 继续学习

> [!next] 下一步
> [[01_学习指南/33_DPO与偏好优化/逐讲学习/05 比较BaseSFT与DPO并分析长度偏差|下一讲：比较BaseSFT与DPO并分析长度偏差]]

> [!info]- 练习与记录
> [[01_学习指南/33_DPO与偏好优化/示例工程/README#代码导航|查看源码]] · [[01_学习指南/33_DPO与偏好优化/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 33：DPO与偏好优化|本单元完成清单]]
