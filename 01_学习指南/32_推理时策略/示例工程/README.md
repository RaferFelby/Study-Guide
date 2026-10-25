---
title: 推理时策略示例工程代码导航
tags: [learning, inference, sampling]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 推理时策略示例工程代码导航

> [!nav] 页面导航
> [[01_学习指南/32_推理时策略/00 推理时策略学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/32_推理时策略/逐讲学习/01 从单次回答理解温度与候选采样|从第一讲开始：从单次回答理解温度与候选采样]]

## 先运行

VS Code打开本目录，使用工作区根共享Python：

```powershell
& ..\..\..\.venv\Scripts\python.exe evaluation.py --output report-my-01.json
```

新文件不覆盖。只生成合成候选，不用模型/API/下载/真实数据，不安装依赖。

## 代码导航

- [sampling.py](./sampling.py)：五类候选、候选层温度softmax、固定六题和局部随机源。
- [selection.py](./selection.py)：完整/循环/步数检查、答案投票、固定加法结果与步骤验证。
- [strategies.py](./strategies.py)：single/vote/best_of_n、次数/字节/实际及模拟时间预算，失败成本与弃权。
- [evaluation.py](./evaluation.py)：六题×三seed配对，选择后评分，报告全部运行且不覆盖文件。
- [test_strategies.py](./tests/test_strategies.py)：温度/平票/错误多数/步骤错、预算/迟到结果、失败成本和对照分母。
- [conftest.py](./tests/conftest.py)：只为本工程测试加入源码目录。
- [requirements.txt](./requirements.txt)：运行标准库，测试/格式使用共享环境已有工具。

## 实际固定结果

N=1 single5/18、回答12、尝试18、字节4518；N=5 vote3/18、回答12、尝试90、字节22590；N=5 best_of_n6/18、回答6、尝试90、验证60、字节32955。18是六题三seed，不是18独立题。全分母包含循环/长输出/弃权。

生成模拟0.01+输出字节×0.00001秒，验证每次模拟0.002秒；wall_seconds仅本机Python耗时。字节不是真实LLM token，费用None为未测；规则验证不是学习PRM。当前投票配置无收益应停用，不能扩大到所有真实方法。

## 检查命令

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

作者27项示例测试通过。时钟检查前后丢弃迟到结果，但不强行中断真实后端；long在本机先造固定文本再模拟超限，不证明真实流式截流。真实接入须另验证超时/取消/token预算、Tokenizer和模型费用。

## 教学入口

[[01_学习指南/32_推理时策略/00 推理时策略学习地图|六讲正文]] · [[90_参考与维护/单元验证/32 推理时策略验证记录|作者实际范围]]。[Self-Consistency论文](https://arxiv.org/abs/2203.11171) · [过程监督论文](https://arxiv.org/abs/2305.20050)。本工程只是机制教学，不是论文实验复现。
