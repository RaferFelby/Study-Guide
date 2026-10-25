---
title: DPO与偏好优化参考工程验证记录
tags: [validation, pytorch, dpo]
updated: 2026-10-12
cssclasses: ["guide-page", "guide-reference"]
---

# DPO与偏好优化参考工程验证记录

## 入口与实际环境

[[01_学习指南/33_DPO与偏好优化/00 DPO与偏好优化学习地图|学习地图]] · [[01_学习指南/33_DPO与偏好优化/示例工程/README|代码导航]]。2026-10-12，共享Python3.13.12、PyTorch2.14.0+cu130、pytest8.4.2、Ruff0.16.9。CPU与CUDA实际运行，GPU为NVIDIA GeForce RTX5070Laptop、CUDA运行时13.0，FP32。未安装新包、下载模型、使用API或接真实用户。

模型8133参数，45个固定词，Embedding24维、GRU隐藏32维；本地Base只学旧copy，不是通用预训练LLM。36来源组，train24组48对、dev/test各6组12对，来源隔离。全部偏好来自明确合成规则或故意错误短句，非真实人类签署。

## 最终实验协议与报告

Base在训练来源上copy100更新，SFT学ask150更新；SFT只按固定1:3短长数据监督，带颜色/风格相关性。保存sft.pt后实际重新加载，独立冻结副本作reference。四组DPO使用新AdamW、全训练批、梯度裁剪1、无dropout/AMP/LoRA。参考分数在固定数据上缓存，训练后逐参数断言未变，参考grad均None。

最终源码完整报告：

- `示例工程/report-author-cpu-delivery-20261012/report.json`
- `示例工程/report-author-cuda-delivery-20261012/report.json`

报告evaluation_protocol=fixed_diagnostic_not_blind_final_test。早期report-author-cpu/cuda-20261012、后续*-final-*均保留；早期三配置学习率0.01已严重退化，没有把这些失败删掉。参数后续在反复诊断后调整，不冒充盲测或未触碰最终保留集。

## 固定诊断实际结果

以下计数最终CPU/CUDA一致；各行分母12。颜色指标只检查ok/正确颜色前缀及EOS，非全面语义/格式验收；exact_brief检查完整短句。原始概率排序是teacher forcing，不是贪心生成。

| 阶段 | beta / lr / 更新 | 颜色命中 | 完全正确简短 | 旧copy | 给定正确短胜长 |
| --- | --- | --- | --- | --- | --- |
| 本地Base | copy训练 | 0 | 0 | 12 | 12 |
| SFT | SFT训练 | 12 | 2 | 3 | 2 |
| clean-beta-0.1 | 0.1 / 0.001 / 80 | 11 | 8 | 4 | 12 |
| clean-beta-0.5 | 0.5 / 0.001 / 80 | 12 | 6 | 4 | 8 |
| biased-short | 0.1 / 0.001 / 200 | 4 | 4 | 3 | 12 |
| aggressive-clean | 0.1 / 0.01 / 80 | 0 | 0 | 0 | 12 |

最终训练循环秒CPU依序约1.076/1.139/2.561/1.054，CUDA约1.089/1.070/2.600/1.113。只测微型训练段，首次导入/启动、所有评估、存盘等不包含其中；不能给真实模型性能排名。CUDA全实验最大已分配张量78009856字节，不是每策略独立或整卡显存；CPU峰值内存未测。

beta0.5在此固定诊断保留颜色，但旧copy仍4/12，不能全任务替换Base。偏好错误导致坏事实学习；大步更新把给定回答概率差推高，却产生重复red直到8token上限。loss或偏好排序提高不表示生成正确。Base短回答排序12/12但问答颜色0/12，保留长度倾向反例。

## 实际测试与异常

22项测试通过，17.41秒，无跳过，包括已有CUDA实际SFT/DPO有界更新。覆盖来源隔离、偏好结构/方向条件、completion含EOS/pad屏蔽、下一token位移、和/平均长度差、初始log2目标/梯度方向、beta边界、极值稳定、空监督/形状、因果不可见未来、policy改变/参考冻结、SFT权重读回及新阶段DPO。

早期CUDA曾出现GRU权重不连续布局警告；最终复制/冻结后调用flatten_parameters整理布局，最终完整实验无该警告，不改变数学参数。训练损失/梯度不有限会停止，没有吞掉失败。

Ruff规则/格式通过。六讲6个完整Python教学片段实际运行通过。全库308份正式文档的YAML、标题、围栏、表格双链和本地链接检查发现0个问题，全部能从学习首页到达；未做Obsidian界面视觉验收。

## 权重能力与未验证

pt只含推理权重和词表，purpose明确为inference_weights_not_resume_checkpoint；DPO从SFT权重开始新阶段，未保存优化器/RNG/完整轮次，resume_training_supported=False。只加载本工程可信文件，不声称等价中断续训。

没有真实人类偏好、通用LLM、真实Tokenizer/chat模板、TRL/PEFT、PPO训练、盲评或生产收益。PPO只讲目标与工程分工，ppo_executed=False。小固定数据不支持统计显著性、通用beta结论或对齐安全保证。未做Obsidian界面视觉验收。

最终源码再次运行22项测试，8.65秒通过，无跳过。格式复查发现data.py一处长行后已格式化并重新通过Ruff。教学片段批查工具新增报告路径后，单元26的5段与单元33的6段再次运行通过；作者维护脚本另14项测试通过，0.15秒。六讲练习与未勾选学习记录复核，临时教学文件已清理。
