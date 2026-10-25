---
title: 第 1 讲：从 Transformer 配置读懂模型骨架
tags:
  - llm-architecture
  - transformer
  - model-config
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 1 讲：从 Transformer 配置读懂模型骨架

> [!nav] 页面导航
> [[01_学习指南/09_主流大模型架构与参数估算/00 主流大模型架构与参数估算学习地图#学习顺序|单元 09：主流大模型架构与参数估算]] · [[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/02 估算参数量并读懂 SwiGLU 与 RMSNorm|下一讲]]

## 本讲目标与先修知识

先修是单元 08 的 token 表示、注意力和 Transformer Block；可以回顾 [[01_学习指南/08_Transformer从零实现/逐讲学习/04 组装多头注意力与 Transformer Block|Block 结构]]。学完后你能读懂 hidden size、layer 数、attention head 数、KV head 数和 intermediate size，并能用这些字段画出一层 Decoder。

## 为什么要读配置

模型名字里的“7B”“8B”是概括，不能告诉你每层长什么样、缓存占多少或结构是否共享。模型配置（config）是描述模型形状和功能开关的一组数据。读具体版本的配置，比凭家族名猜测可靠。

Decoder-only 模型可先画成：

~~~mermaid
flowchart TB
  ids[Token IDs] --> emb[词向量 Embedding]
  emb --> blocks[重复 N 层 Decoder Block]
  blocks --> norm[Final Norm]
  norm --> head[输出词表分数 LM Head]
  subgraph block[一个 Decoder Block]
    attn[因果自注意力] --> add1[残差]
    ffn[逐 token FFN] --> add2[残差]
  end
~~~

N 是层数。每层中的注意力负责跨 token 收集上下文；FFN（前馈网络）对每个 token 的特征单独做变换。

## 五个重要字段

- hidden_size（隐藏维度 D）：每个 token 在层间传递的向量宽度。
- num_hidden_layers（层数 L）：Decoder Block 重复次数。
- num_attention_heads（Query 头数 Hq）：一个 token 的查询向量分成多少个头。
- num_key_value_heads（KV 头数 Hkv）：Key/Value 分成多少个头。若小于 Hq，通常表示 GQA；下一讲会说明。
- intermediate_size（FFN 中间维度 F）：SwiGLU 中间投影的宽度。

head_dim 通常由 D/Hq 得到。每个头不是各自拥有完整 D 维，而是切分隐藏维度。配置应满足 D 能被 Hq 整除，Hq 能被 Hkv 整除。

## 用两个具体配置看差异

本课程附有配置字段快照：[Qwen2.5-7B](../示例工程/configs/qwen2_5_7b.json) 与 [Llama 3.1-8B](../示例工程/configs/llama3_1_8b.json)。Qwen 快照来自模型仓库提交 7c128df；Llama 快照来自 Meta 官方模型清单，链接指向 main，使用时应记录访问日期并重新核对。

| 字段 | Qwen2.5-7B | Llama 3.1-8B |
|---|---:|---:|
| D | 3584 | 4096 |
| L | 28 | 32 |
| Hq | 28 | 32 |
| Hkv | 4 | 8 |
| F | 18944 | 14336 |
| 词表 V | 152064 | 128256 |

Qwen 每层有 28 个 Query 头，但只需要 4 个 KV 头；Llama 对应 32 个 Query 头和 8 个 KV 头。两者都用 RoPE 位置机制和门控 FFN；具体实现仍应以对应版本的配置和代码为准。[Qwen2.5-7B 配置](https://huggingface.co/Qwen/Qwen2.5-7B/blob/7c128df/config.json)；[Meta Llama 3.1 官方模型清单](https://github.com/meta-llama/llama-models/blob/main/models/sku_list.py)。

## 动手操作与预期结果

1. 在 VS Code 打开两份 JSON 配置。
2. 将上表每个字段与 JSON 名称一一对应，圈出 Hq 与 Hkv 不同之处。
3. 在纸上画一个 Block：先标记因果注意力，再画 FFN，标出输入输出都是 D 维。
4. 暂时不下载模型，只读配置和估算器输出。

完成时应能说明 Qwen 每头维度为 3584/28=128，Llama 每头维度为 4096/32=128；一层 Block 的输入和输出维度不变。

## 常见错误

- 把模型名字的 7B 直接当成精确参数量：标签经过概括，embedding 和实现细节也影响总数。
- 误把 KV 头等于 Query 头：GQA/MQA 会让两种头数不同。
- 只记型号、不记版本：同一系列有不同尺寸、上下文和变体。
- 将最大上下文长度理解为免费容量：上下文越长，KV Cache 通常越大。

## 练习

### 跟做练习

打开 Qwen 配置，算 head_dim，并解释 28 个 Query 头与 4 个 KV 头的区别。完成标准：写出 128 维、每个 KV 头服务多个 Query 头。

### 独立练习

假设 D=3072、Hq=24、Hkv=6，算 head_dim 和平均每个 KV 头对应几个 Query 头。答案：128 维，4 个 Query 头共享一组 KV。

### 迁移练习

从任意模型官方配置找到层数、隐藏宽度、Query 头、KV 头、FFN 宽度和词表字段，并记录仓库、提交和日期。完成标准：另一人能按记录打开同一份结构数据。

> [!example]- 答案解析：为什么需要配置快照
> 模型系列名称是产品标签，不是完整结构说明。快照让教程中的算术可复算；记录源地址和提交能区分仓库更新后的版本。快照不是权重，也不能用来运行模型。

## 继续学习

> [!next] 下一步
> [[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/02 估算参数量并读懂 SwiGLU 与 RMSNorm|下一讲：估算参数量并读懂 SwiGLU 与 RMSNorm]]

> [!info]- 练习与记录
> [[01_学习指南/09_主流大模型架构与参数估算/示例工程/README#代码导航|查看源码]] · [[01_学习指南/09_主流大模型架构与参数估算/示例工程/README#运行方式|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 09：主流大模型架构与参数估算|本单元完成清单]]
