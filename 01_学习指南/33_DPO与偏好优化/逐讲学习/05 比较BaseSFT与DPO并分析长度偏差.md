---
title: 第 5 讲：比较BaseSFT与DPO并分析长度偏差
tags: [learning, dpo, preference]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 5 讲：比较BaseSFT与DPO并分析长度偏差

> [!nav] 页面导航
> [[01_学习指南/33_DPO与偏好优化/00 DPO与偏好优化学习地图#学习顺序|单元 33：DPO与偏好优化]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/04 从SFT权重启动CPU与GPU的DPO|上一讲]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/06 分清SFTPPO与DPO并写采用结论|下一讲]]

## 本讲要解决的问题与前置

偏好得分高就可以采用吗？本讲比较 Base／SFT／DPO 的固定生成与旧任务，明确长度偏差、坏标签和过优化。先完成前四讲，复习 [[01_学习指南/11_LLM_API与Prompt/逐讲学习/05 用固定评估集比较三个 Prompt|固定题集与指标分母]]，并保留单元 26 的来源分组边界。本讲在下面逐项定义实际使用的指标；完整 Agent 评估体系可在需要系统评估时另学。

## 指标先定义

factual_correct在本固定任务中指生成前两词为ok/正确颜色且以EOS结束，是**窄颜色命中指标**，不检查全部自然语言语义。exact_brief要求整段恰为ok/正确颜色/EOS。old_copy_correct要求copy问题输出颜色/EOS。

chosen_raw_logp_wins是给定两回答在teacher forcing下的概率排序，和自由贪心生成不同；它不证明模型实际会输出chosen，更不证明回答正确。mean_raw_logp_gap为两序列log概率差，长度也会影响。

## 实际CPU结果（每行12个固定诊断题）

| 模型 | 颜色命中 | 正确且完全简短 | 旧copy | 给定正确短胜长 |
| --- | --- | --- | --- | --- |
| 本地Base | 0/12 | 0/12 | 12/12 | 12/12 |
| SFT | 12/12 | 2/12 | 3/12 | 2/12 |
| clean beta0.1 | 11/12 | 8/12 | 4/12 | 12/12 |
| clean beta0.5 | 12/12 | 6/12 | 4/12 | 8/12 |
| biased-short | 4/12 | 4/12 | 3/12 | 12/12 |
| aggressive-clean | 0/12 | 0/12 | 0/12 | 12/12 |

作者CUDA最终计数相同，但log概率与时间不完全一致，不声称跨设备字节级复现。来源分组隔离，但实验反复观察过这些固定题，所以不是盲测或严格未触碰最终测试，不能给统计泛化结论。

## 最小示例：读自己刚生成的报告

先完成第4讲CPU实验，再新建lesson_05.py：

```python
import json
from pathlib import Path

report = json.loads(Path("report-my-cpu-01/report.json").read_text(encoding="utf-8"))
for name in ("base", "sft"):
    item = report[name]
    print(name, item["factual_correct"], item["exact_brief"], item["old_copy_correct"])
for run in report["runs"]:
    item = run["test"]
    print(run["name"], item["factual_correct"], item["exact_brief"],
          item["old_copy_correct"], item["chosen_raw_logp_wins"])
print("参考未变：", report["reference_unchanged"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`。预期得到上表计数与参考True。若文件不存在，先跑自己的CPU实验；不假定你电脑提前有作者报告。修改实验参数后输出可不同，必须记录配置，不追着数字改数据。

## 三种偏差与实际失败

**长度倾向**：Base颜色命中0，但给定短回答胜长12。单看排序会误以为模型优秀；更短序列乘的概率项更少，原始概率不能替代任务检查。DPO减参考相对倾向也不能自动消除所有长度/标签偏差。

**坏事实偏好**：故障标签偏爱错误颜色的短句，biased-short颜色4/12，尽管偏好相关排序很好。模型跟随偏好不等于学到正确事实。换回正常测试对仍见退化；故障对评估仅检查它是否跟随坏标签，不能叫任务质量。

**过优化**：学习率0.01的aggressive-clean把给定短对数差推很大，却贪心输出red重复至8token上限或异常结束，颜色0/12。不能用loss下降/分数提高替代生成验收。较小学习率也仍有11/12的错误和旧任务不全恢复。

## 旧任务与采用范围

SFT本身copy从12降3，DPO最多4，并未保住Base旧能力。若业务要求copy不退化，整个SFT/DPO替换方案都不通过。若只研究ask新格式，可保留隔离的小实验与Base回退，但这不是生产收益或真实偏好验证。

dev结果与test固定诊断都保留，不能因某个beta在小test上好就称通用最佳。后续真实实验应先用dev选配置，再在没反复看的保留集/盲评验收；人工评审应隐藏模型标签、明确规则并记录分歧。

## 练习与答案

### 跟做：排序12/12而事实0/12

完成标准是解释Base和aggressive两个反例，指出给定回答概率与实际生成不同。

> [!example]- 参考答案与解析
> Base受短序列概率倾向影响；aggressive通过降低较长回答等方式扩大相对差，却生成异常文本。排序指标不是生成任务正确率。

### 独立：beta0.5可以替换Base吗

提示：看旧copy。完成标准是12/12新颜色不等于全任务保持，并写采用条件。

> [!example]- 参考答案与解析
> copy只有4/12，低于Base12/12，不能全替换。仅可保留隔离ask任务研究，真实泛化与利益未验证。

### 迁移：真实偏好盲评

提出独立任务、标注标准和泄漏控制。完成标准是隐藏模型名、保存失败/分歧、评估事实与风格及旧能力。

> [!example]- 参考答案与解析
> 固定未用于调参的题，随机隐藏候选来源，明确事实/约束/风格评分，记录审核及分歧，做旧任务回归。不能只看chosen训练准确或同生成模型自评。

## 继续学习

> [!next] 下一步
> [[01_学习指南/33_DPO与偏好优化/逐讲学习/06 分清SFTPPO与DPO并写采用结论|下一讲：分清SFTPPO与DPO并写采用结论]]

> [!info]- 练习与记录
> [[01_学习指南/33_DPO与偏好优化/示例工程/README#代码导航|查看源码]] · [[01_学习指南/33_DPO与偏好优化/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 33：DPO与偏好优化|本单元完成清单]]
