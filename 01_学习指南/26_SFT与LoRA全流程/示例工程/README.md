---
title: SFT与LoRA示例工程代码导航
tags: [learning, pytorch, sft, lora]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# SFT与LoRA示例工程代码导航

> [!nav] 页面导航
> [[01_学习指南/26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/26_SFT与LoRA全流程/逐讲学习/01 整理指令数据并只监督答案|从第一讲开始：整理指令数据并只监督答案]]

## 先运行

在VS Code打开本目录，PowerShell使用工作区共享解释器，不创建单元虚拟环境：

```powershell
& ..\..\..\.venv\Scripts\python.exe train.py --device cpu --output-dir report-my-cpu-01
& ..\..\..\.venv\Scripts\python.exe inference.py --base report-my-cpu-01/base.pt --adapter report-my-cpu-01/adapter-rank-8.pt
```

需已有PyTorch。本机作者Python3.13.12、torch2.14.0+cu130，CUDA可用。缺包先核对共享环境并提出安装方案，不擅自运行pip。数据全部合成，模型自己预训练，没有联网、外部权重或用户数据。输出目录必须为新目录，不覆盖。报告任务范围为固定词表，并记录作者与学习者不同角色。

GPU可用时：

```powershell
& ..\..\..\.venv\Scripts\python.exe train.py --device cuda --precision bf16 --output-dir report-my-gpu-01
```

fp16替换precision另建目录；CPU明确fp32。完整步骤、预期与排错见 [[01_学习指南/26_SFT与LoRA全流程/逐讲学习/04 运行CPU和GPU训练并恢复状态|第 4 讲：运行CPU和GPU训练并恢复状态]]。

## 代码导航

- [data.py](./data.py)：三种单轮格式归一化、320条合成记录、来源切分、答案监督mask、词表摘要。
- [model.py](./model.py)：单块因果Transformer、LoRA低秩层、冻结与合并。
- [training.py](./training.py)：token加权累积、warmup、AMP、裁剪、loss与自由生成评估。
- [checkpoint.py](./checkpoint.py)：Base摘要、推理适配器与完整训练状态分开保存。
- [train.py](./train.py)：CPU/GPU实验入口，先验证选择再读测试，旧复制任务回归。
- [inference.py](./inference.py)：加载可信Base与适配器，可选合并，固定提示推理。
- [test_sft.py](./tests/test_sft.py)：数据边界、因果、冻结、累积、CPU精确恢复及GPU三种精度。
- [requirements.txt](./requirements.txt)：本工程最小依赖说明；共享约束以工作区清单为准。

## 报告与验证

新结果目录包含base.pt、adapter-rank-2/8.pt、training-rank-2/8.pt、report.json。摘要匹配才能加载适配器；仅加载自己可信文件。report记下loss、任务通过、训练时间、CUDA已分配张量峰值、旧任务及未测范围。

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

无GPU时GPU测试明确skip，不称运行通过。作者当前GPU路径已执行；具体记录见 [[90_参考与维护/单元验证/26 SFT与LoRA全流程验证记录|验证记录]]。本例未实现packing、通用多轮chat模板、真实预训练模型微调、分布式或通用量化。
