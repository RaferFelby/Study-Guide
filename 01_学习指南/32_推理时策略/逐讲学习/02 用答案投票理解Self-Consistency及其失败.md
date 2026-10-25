---
title: 第 2 讲：用答案投票理解Self-Consistency及其失败
tags: [learning, inference, sampling]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：用答案投票理解Self-Consistency及其失败

> [!nav] 页面导航
> [[01_学习指南/32_推理时策略/00 推理时策略学习地图#学习顺序|单元 32：推理时策略]] · [[01_学习指南/32_推理时策略/逐讲学习/01 从单次回答理解温度与候选采样|上一讲]] · [[01_学习指南/32_推理时策略/逐讲学习/03 用Best-of-N区分结果验证与过程验证|下一讲]]

## 本讲要解决的问题与前置

单次可能碰巧错，多次答案一致是否更可靠？本讲做答案投票，并观察相关错误怎样让更多样本更糟。前置第1讲、字典/列表/Counter计数；阅读selection.py的majority_answer与strategies.py的vote分支。

## Self-Consistency的概念与本例范围

Self-Consistency可理解为“多次生成后看最终答案一致性”：原论文从多条推理路径的最终答案聚合，而不是只取一条贪心路径。[原始论文](https://arxiv.org/abs/2203.11171)。它依赖候选多样性与正确答案的出现情况，不承诺所有任务都提高。

本工程只演示合成候选的整数答案投票，没有LLM、多条真实推理路径或论文完整复现。多个错误也可能一致；同一个生成器偏差导致的重复错误，不是独立专家的共识。

当前answer必须是整数，便于直接按值计数。真实答案可能有单位、同义表达、格式差异，必须先定义稳定的提取/规范化规则，否则同一答案被拆成多票；不能规范化掉关键数值或条件。

## 最小示例与操作

新建lesson_02.py：

```python
from sampling import evaluation_tasks, make_candidate
from selection import majority_answer
from strategies import run_strategy

task = evaluation_tasks()[0]
correct = make_candidate(task, "correct")
wrong = make_candidate(task, "wrong")
print("平票：", majority_answer([correct, wrong]))
print("错误多数：", majority_answer([wrong, wrong, correct]))
single = run_strategy(task, "single", 1, seed=17)
vote = run_strategy(task, "vote", 5, seed=17)
print("单次与五次投票：", single["answer"], vote["answer"])
print("尝试数：", single["attempts"], vote["attempts"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_02.py`。预期平票None、错误多数6、单次5而投票6、尝试1/5。这个固定seed案例已经说明增加样本可能把原来正确回答改错。

## 逐步解释计数、平票与失败

Counter按answer累计票数，找最大票数；有多个最大答案时返回None，不读取参考答案打破平票。None是明确弃权，不能为了提高成功率偷偷挑正确项。

run_strategy先对每次生成做格式、步骤上限、重复状态和完成检查；循环/超长候选不能投票。但生成失败仍计attempts和字节成本。过滤失败后的有效候选数可能小于请求数，应报告，不从费用中删掉失败。

本投票不做数学正确性验证，因此wrong和bad_steps的完成候选仍可能入票。bad_steps最终数字对，也不说明路径正确。投票选择的是答案一致性，不自动验证步骤和权限。

## 什么时候更多票不解决问题

固定题集第三题几乎只生成同一个错误答案。重复五次不会产生正确路径，只增加一致的错票。第一题seed17单次正确，但后四次的样本让错票胜出；这不是编码故障，是选择规则与生成分布的共同结果。

若把温度设0并重复同一确定性输出，通常只有重复，不新增证据。真实模型多次输出的相关性、问题偏差和答案提取质量都需对照，不能把N次当N个互不相关的证据。

## 动手与常见错误

手数三个明确候选的票，再用函数核对；把平票写成弃权。随后读取evaluation结果中vote的失败与错误，不能只保留投票改善的题。长文本不因出现很多相同数字就多计票，每个有效候选只一票。

错误：参考答案参与平票选择；丢掉失败尝试成本；五次确定性同输出称多样推理；选择过程中看到kind=correct就取它。当前kind只用于合成生成，真实选择不能有这个后门。

## 练习与答案

### 跟做：解释5变6

完成标准是指出单次与多次使用同一任务和seed，投票聚合了更多候选，但多数可能错。

> [!example]- 参考答案与解析
> 第一个候选给5，后续的分布偏向错误6，多数6胜出；增加计算不是单调提高质量。比较必须保留这一退化。

### 独立：四个答案分成2比2

先写预期，再构造两个correct/两个wrong调用majority_answer。完成标准是None及平票原因。

> [!example]- 参考答案与解析
> 没有唯一最高票数，弃权。若要另一平票规则，应预先固定并报告，不能按评测参考临时选择。

### 迁移：文本答案归一

“5件”“总数5”“五件”如何处理？完成标准是规则一致、保留单位/条件，无法可靠解析时弃权。

> [!example]- 参考答案与解析
> 可定义受控任务格式及数值/单位提取，把等价表达归同类；语义含糊或单位不同不强合并。需要验证提取器，不能用模糊相似就当同答案。

## 继续学习

> [!next] 下一步
> [[01_学习指南/32_推理时策略/逐讲学习/03 用Best-of-N区分结果验证与过程验证|下一讲：用Best-of-N区分结果验证与过程验证]]

> [!info]- 练习与记录
> [[01_学习指南/32_推理时策略/示例工程/README#代码导航|查看源码]] · [[01_学习指南/32_推理时策略/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 32：推理时策略|本单元完成清单]]
