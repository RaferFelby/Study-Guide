---
title: README
tags: [learning, paper-reading, beginner]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# README

> [!nav] 页面导航
> [[01_学习指南/37_论文精读与技术趋势判断/00 论文精读与技术趋势判断学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/37_论文精读与技术趋势判断/逐讲学习/01 带着问题选择论文并建立阅读卡|从第一讲开始：带着问题选择论文并建立阅读卡]]

## 从哪里开始

Obsidian读 [[01_学习指南/37_论文精读与技术趋势判断/00 论文精读与技术趋势判断学习地图|学习地图]]，VS Code沿下面源码阅读。阅读结构检查、矩阵机制与选型教学情景分别记录。

## 代码导航

- [catalog.py](./catalog.py)：六篇四问卡、原始来源、定位和真实阅读深度。
- [evidence.py](./evidence.py)：非空字段、证据类别与条件差异，不做自动语义事实核验。
- [merge_probe.py](./merge_probe.py)：随机小线性层、LoRA合并／冻结、漏缩放负例和CPU/CUDA验证。
- [decision.py](./decision.py)：教学四种状态，关键失败优先；输入须由证据支持。
- [review.py](./review.py)：保存结构化卡与明确标记的教学情景建议。
- [test_reading.py](./test_reading.py)：缺字段、未知证据、决策边界、矩阵与初始化行为。
- [requirements.txt](./requirements.txt)：复用根共享已安装PyTorch，不新增依赖。

## 环境与运行

在本示例工程PowerShell执行，使用根共享.venv；Python3.13.12、PyTorch2.14.0+cu130、pytest8.4.2、Ruff0.16.9为作者实际环境。

```powershell
..\..\..\.venv\Scripts\python.exe review.py --output-dir report-my-review-01
..\..\..\.venv\Scripts\python.exe merge_probe.py --device cpu --output-dir report-my-cpu-01
..\..\..\.venv\Scripts\python.exe merge_probe.py --device cuda --output-dir report-my-cuda-01
..\..\..\.venv\Scripts\python.exe -m pytest -q
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

CUDA可用才运行GPU命令；CPU完整覆盖机制学习。输出目录须新建，旧结果不覆盖。模块导入不联网、不训练、不写报告；没有外部模型或付费API。

## 产物与判定

review.json只做六张作者卡与教学情景，默认业务未验收，结果试点，不是自动业务审批。LoRA探针report.json／probe.pt记录8输入、6输出、rank2、alpha4、scale2、FP32、seed2026、更新前后合并、冻结与漏缩放差异；基础与输入先在CPU生成后移设备。

非零B初始化用于非平凡合并探针，零B起点另有测试；基础随机而非预训练大模型。SGD仅更新A/B一步，不测真实任务、长期训练、速度或原论文全部资源收益。probe.pt为推理状态，非精确续训；正文 [[01_学习指南/37_论文精读与技术趋势判断/参考阅读/01 六篇论文的四问阅读示范|阅读卡]] 与 [[90_参考与维护/单元验证/37 论文精读与技术趋势判断验证记录|作者记录]] 说明未测范围。
