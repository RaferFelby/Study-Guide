---
title: DPO示例工程代码导航
tags: [learning, dpo, preference]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# DPO示例工程代码导航

> [!nav] 页面导航
> [[01_学习指南/33_DPO与偏好优化/00 DPO与偏好优化学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/01 构造同一问题的chosen与rejected偏好|从第一讲开始：构造同一问题的chosen与rejected偏好]]

## 先运行

第 1～3 讲讲解机制，第 4～6 讲完成本工程实验。先掌握 SFT、回答掩码、来源分组、对数概率和梯度；比较报告前补 API 单元第 5 讲的固定评估。工程的 `data.py` 自行生成合成偏好，`experiment.py` 自行训练并保存起始 SFT 权重，无需先产出单元 31 的数据包。

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

[[01_学习指南/33_DPO与偏好优化/00 DPO与偏好优化学习地图|六讲正文]] · [[90_参考与维护/单元验证/33 DPO与偏好优化验证记录|作者实验与限制]]。[DPO论文](https://arxiv.org/abs/2305.18290) · [TRL目标参考](https://huggingface.co/docs/trl/dpo_trainer)。
