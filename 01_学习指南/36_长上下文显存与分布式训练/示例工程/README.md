---
title: README
tags: [learning, context-memory, beginner]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# README

> [!nav] 页面导航
> [[01_学习指南/36_长上下文显存与分布式训练/00 长上下文显存与分布式训练学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/36_长上下文显存与分布式训练/逐讲学习/01 计算注意力矩阵并区分显存组成|从第一讲开始：计算注意力矩阵并区分显存组成]]

## 从哪里开始

Obsidian 进入 [[01_学习指南/36_长上下文显存与分布式训练/00 长上下文显存与分布式训练学习地图|学习地图]]，VS Code 按下列源码顺序阅读。小模型实测、位置机制与多卡设计分别记录，不把估算当实测。

## 代码导航

- [planning.py](./planning.py)：注意力矩阵与FP32 Adam／分片粗状态预算。
- [position.py](./position.py)：相邻坐标对RoPE、简单位置插值，非完整YaRN。
- [packing.py](./packing.py)：因果／窗口掩码与样本段隔离、边界标签。
- [model.py](./model.py)：208192参数四层因果Decoder、显式注意力、SDPA、逐层重算。
- [experiment.py](./experiment.py)：固定输入／初始化的CPU/CUDA长度、峰值、耗时和数值对照。
- [packing_experiment.py](./packing_experiment.py)：padding／packing实际比较，包含等长反例。
- [distributed_demo.py](./distributed_demo.py)：真正双CPU进程Gloo/DDP、参考更新与复制权重文件。
- [test_context_training.py](./test_context_training.py)：因果、段边界、梯度一致、GPU更新与DDP验证。
- [requirements.txt](./requirements.txt)：复用根共享已有PyTorch，不安装FlashAttention／DeepSpeed。

## 环境与运行

在本单元示例工程的PowerShell执行；根共享 `.venv`。作者Python3.13.12、PyTorch2.14.0+cu130、pytest8.4.2、Ruff0.16.9。CPU可完成基本实验与真实DDP，CUDA路径需要BF16支持。

```powershell
..\..\..\.venv\Scripts\python.exe experiment.py --device cpu --lengths 64 128 256 512 --output-dir report-my-cpu-01
..\..\..\.venv\Scripts\python.exe experiment.py --device cuda --lengths 64 128 256 512 1024 --output-dir report-my-cuda-01
..\..\..\.venv\Scripts\python.exe packing_experiment.py --device cpu --output-dir report-my-packing-cpu-01
..\..\..\.venv\Scripts\python.exe packing_experiment.py --device cuda --output-dir report-my-packing-cuda-01
..\..\..\.venv\Scripts\python.exe distributed_demo.py --output-dir report-my-ddp-01
..\..\..\.venv\Scripts\python.exe -m pytest -q
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

输出目录必须新建。默认SDPA math；`--sdpa-backend flash`仅在已编入且输入兼容环境强制尝试，本机明确不可用，没有静默把math称为Flash。CPU无CUDA内存计数，null代表未测。DDP会合临时文件在系统自有临时目录创建并清理，旧报告不删除。

## 输入、测量与限制

长度实验batch=2、四层、固定合成整数与映射标签，SGD无动量；CPU FP32，CUDA BF16 autocast但权重／梯度／损失FP32。每组预热一步、恢复相同权重、测三次一步更新，中位数含梯度检查与CPU复制，不是纯内核测速。峰值allocated含活跃快照／权重／输入／梯度／临时量，不是显卡总占用。

packing正确隔离样本、重置位置、忽略每条末尾目标；两种方案按同有效目标求均值。密集块掩码不跳过矩阵块计算，等长打包可能更慢且更耗内存。位置／窗口探针不代表真实长文本能力或稀疏加速。

DDP实际两CPU进程、各2样本，对照全局4样本一步更新；两份rank权重是副本，非分片／完整续训状态。没有多GPU、NCCL、FSDP、DeepSpeed、张量并行或分布式完整恢复。实际数值与失败见 [[90_参考与维护/单元验证/36 长上下文显存与分布式训练验证记录|作者记录]]。
