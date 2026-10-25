---
title: 第 5 讲：区分 Prefill Decode 与采样参数
tags:
  - llm-architecture
  - decoding
  - inference
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 5 讲：区分 Prefill Decode 与采样参数

> [!nav] 页面导航
> [[01_学习指南/09_主流大模型架构与参数估算/00 主流大模型架构与参数估算学习地图#学习顺序|单元 09：主流大模型架构与参数估算]] · [[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/04 比较滑动窗口 MoE 与 MLA|上一讲]] · [[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/06 完成模型资源估算与架构报告|下一讲]]

## 本讲目标与先修知识

本讲承接自回归生成与 KV Cache（[[01_学习指南/08_Transformer从零实现/逐讲学习/06 对齐自回归目标与交叉熵|生成目标]]、[[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/03 用 GQA 与 KV Cache 估算推理显存|缓存]]）。你会画出提示输入到生成结束的过程，区分 prefill 与 decode，并解释 greedy、temperature、top-k/top-p、EOS、最大生成长度、TTFT 和逐 token 延迟。

## Prefill 与 Decode 两阶段

用户给一段 prompt（提示文本）后，模型把它分词并进行 prefill（前缀处理）：一次处理整个已有 token 序列，算出各层隐藏状态和 KV Cache，并得到下一个 token 的分数。

随后进入 decode（逐 token 生成）：根据当前分数选择或采样一个 token，追加到序列；为新 token 算新的 KV 并继续下一步。新的缓存随生成长度增长。

~~~mermaid
sequenceDiagram
  participant U as 用户
  participant M as 模型
  U->>M: 提示词（已有 token）
  M->>M: Prefill：处理整个前缀，建立 KV Cache
  M-->>U: 第一个生成 token
  loop 继续生成
    M->>M: Decode：读旧缓存、追加新 token 的 KV
    M-->>U: 下一个 token
  end
  M-->>U: 遇到 EOS 或达到长度上限
~~~

Prefill 可在整段已知提示上并行计算，但提示越长，处理工作和初始缓存越大。Decode 每次只生成下一个 token，前一步结果决定下一步输入；因此输出长度增长会延长逐步生成时间，并让 KV Cache 持续增长。

## 两个常见延迟指标

- TTFT（首 token 延迟）：从请求开始到第一个输出 token 到达的时间。它受分词、排队、prefill 和首次 decode 等影响。
- TPOT / inter-token latency（逐 token 时间）：生成阶段相邻输出 token 的时间间隔。具体统计口径因系统而异。

这些指标不能互相替代。长 prompt 往往让 TTFT 更明显变长；长回答会让 decode 阶段持续更久。真实服务还要记录并发、batching、模型版本、硬件、精度和提示长度。

## 选择下一个 token

模型先给词表每个 token 一个 logit（未归一化分数）。Greedy 每步直接取最高分 token，确定且容易复现，但可能重复。

Sampling（采样）把分数转成概率分布后随机抽样：

- Temperature：把 logits 除以温度再 softmax。正温度小于 1 通常让高低概率差异更明显；大于 1 通常更平。它改动分布，不保证答案质量提高。温度为 0 的处理常由生成库作为 greedy 特例。
- Top-k：只保留分数最高的 k 个候选再归一化抽样。
- Top-p：按概率从大到小排列，保留累计概率达到 p 所需的最小候选集合再抽样。
- EOS：模型输出结束标记时，生成通常停止。
- 最大新 token 数：硬上限；即使没出 EOS 也停止。

生成库里这些参数的默认值和组合规则依版本而异；提交报告要记录实际设置。[Hugging Face Generation 文档](https://huggingface.co/docs/transformers/main_classes/text_generation)；[生成策略说明](https://huggingface.co/docs/transformers/v4.40.0/generation_strategies)。

## 固定提示对照操作

不需加载权重也能先设计实验记录表。若已有可调用的同一模型服务，可对固定 prompt 运行三次：

| 运行 | 策略 | 关键设置 | 记录 |
|---|---|---|---|
| A | Greedy | do_sample=false | 输出、首 token 时间、输出 token 数 |
| B | Sampling | temperature=0.7, top_p=0.9 | 随机种子、输出、相同指标 |
| C | Sampling | temperature=1.0, top_p=0.9 | 随机种子、输出、相同指标 |

保持模型版本、系统提示、prompt、最大新 token 数、服务和并发条件一致。采样要固定随机种子才能减少偶然差异，但某些硬件/后端未必完全确定。没有模型服务时，把表格作为设计练习，不编造实测输出。

## 常见错误

- 认为 prefill 每个 token 串行生成：已知 prompt 可一次并行处理。
- 认为 decode 可以并行决定所有后续 token：每个新 token 依赖前一步选择。
- 把 EOS 和最大长度混为一谈：一个是模型停止标记，一个是调用方上限。
- 认为 temperature 越高越准确：温度调随机程度，不是准确率旋钮。
- 报 TTFT 却不记 prompt 长度和并发：结果无法比较。

## 练习

### 跟做练习

画出 5-token prompt 先 prefill、再生成 3 个 token、最后 EOS 的流程，并在每个 decode 后标注缓存长度。

> [!example]- 答案解析：已采样的token与已写入缓存的token
> 常见逐token实现中，prefill处理5个输入，KV长度5，并用最后位置logits采样第1个新token；此时新token还没做前向。把第1个新token送入decode，缓存到6，采样第2个；再decode到7，采样第3个；再decode到8，采样EOS并停止。若采样到EOS后不再前向，EOS没有对应的新KV，因此缓存长度8，不是简单把5+3+1都计进去。静态缓存容量和引擎调度可不同，这里说明实际已计算位置；资源预算可按最大长度预留，不能把容量与已填充长度混为一谈。

### 独立练习

说明长 prompt 和长回答分别主要增加哪段工作压力。答案：长 prompt 主要加重 prefill 与初始缓存；长回答延长 decode 循环并使缓存继续增长。

### 迁移练习

设计一个 greedy 与 top-p 采样的对照实验，列出至少 6 个必须固定或记录的条件。可包括模型 revision、prompt、最大新 token 数、temperature、top-p、seed、硬件、并发和服务版本。

> [!example]- 答案解析：为什么 temperature 不代表正确率
> Temperature 改变候选概率分布的尖锐程度。某个任务的准确率还取决于模型、提示、数据和评估标准；不同温度只可在固定实验条件下比较输出行为，不能从单个参数变化推出普遍正确率变化。

## 继续学习

> [!next] 下一步
> [[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/06 完成模型资源估算与架构报告|下一讲：完成模型资源估算与架构报告]]

> [!info]- 练习与记录
> [[01_学习指南/09_主流大模型架构与参数估算/示例工程/README#代码导航|查看源码]] · [[01_学习指南/09_主流大模型架构与参数估算/示例工程/README#运行方式|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 09：主流大模型架构与参数估算|本单元完成清单]]
