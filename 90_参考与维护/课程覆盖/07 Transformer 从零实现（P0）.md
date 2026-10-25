---
title: 模块 07 覆盖与验收
tags: [reference, coverage]
updated: 2026-10-24
cssclasses: ["guide-page", "guide-reference"]
---

# 模块 07 覆盖与验收

> [!nav] 页面导航
> [[90_参考与维护/01 课程覆盖索引|覆盖索引]]

## 模块 07：Transformer 从零实现（P0）

教材状态：已编写为单元 08，含学习地图、六讲初学者教程、手写注意力与 decoder-only 示例工程；作者侧 CPU/CUDA 验证完成。入口：[[01_学习指南/08_Transformer从零实现/00 Transformer 从零实现学习地图|单元 08 学习地图]]、[[01_学习指南/08_Transformer从零实现/示例工程/README|示例工程]]、[[90_参考与维护/单元验证/08 Transformer从零实现验证记录|验证记录]]。

**学习内容**

- **K07-01** [[01_学习指南/08_Transformer从零实现/逐讲学习/01 看懂缩放点积注意力|Scaled Dot-Product Attention]]、[[01_学习指南/08_Transformer从零实现/逐讲学习/02 用 mask 阻断不该看的 token|padding/causal mask]]；
- **K07-02** [[01_学习指南/08_Transformer从零实现/逐讲学习/04 组装多头注意力与 Transformer Block|Multi-Head Attention、残差、LayerNorm、FFN]]；前置 [[01_学习指南/08_Transformer从零实现/逐讲学习/03 手算归一化前馈网络与残差|部件课]]补嵌入查表与梯度、归一化手算、固定 FFN、残差和顺序实验；
- **K07-03** [[01_学习指南/08_Transformer从零实现/逐讲学习/04 组装多头注意力与 Transformer Block|Pre-Norm/Post-Norm]]、[[01_学习指南/08_Transformer从零实现/逐讲学习/05 给 token 加位置并理解 RoPE|位置编码与 RoPE]]；
- **K07-04** [[01_学习指南/08_Transformer从零实现/逐讲学习/05 给 token 加位置并理解 RoPE|Encoder-Decoder 与 Decoder-only 结构对照]]；
- **K07-05** [[01_学习指南/08_Transformer从零实现/逐讲学习/06 对齐自回归目标与交叉熵|自回归目标、teacher forcing、token 级交叉熵与有效监督位置]]；
- **K07-06** [[01_学习指南/08_Transformer从零实现/逐讲学习/07 训练小模型并理解 FlashAttention|FlashAttention 分块、在线 softmax 和 IO 优化思想]]。

**验收标准**

- [ ] **C07-01** [[01_学习指南/08_Transformer从零实现/示例工程/app/attention.py|手写 Attention]]、[[01_学习指南/08_Transformer从零实现/示例工程/app/model.py|MHA 与 Transformer Block]]；
- [ ] **C07-02** [[01_学习指南/08_Transformer从零实现/示例工程/tests/test_attention.py|对形状、mask、数值稳定性和梯度编写测试]]；
- [ ] **C07-03** [[01_学习指南/08_Transformer从零实现/逐讲学习/04 组装多头注意力与 Transformer Block|画出两种 Norm 结构并解释稳定性差异]]；
- [ ] **C07-04** [[01_学习指南/08_Transformer从零实现/逐讲学习/01 看懂缩放点积注意力|从方差角度解释缩放因子]]；
- [ ] **C07-05** [[01_学习指南/08_Transformer从零实现/逐讲学习/06 对齐自回归目标与交叉熵|长度 4 输入/目标映射及训练/生成差异]]；
- [ ] **C07-06** [[01_学习指南/08_Transformer从零实现/逐讲学习/07 训练小模型并理解 FlashAttention|区分算法收益与硬件/版本条件]]。


## 单元 08 原地图对照：对应原清单

| 原编号 | 本单元覆盖 |
|---|---|
| K07-01 | [[01_学习指南/08_Transformer从零实现/逐讲学习/01 看懂缩放点积注意力\|Scaled Dot-Product Attention]]、[[01_学习指南/08_Transformer从零实现/逐讲学习/02 用 mask 阻断不该看的 token\|padding/causal mask]] |
| K07-02 | [[01_学习指南/08_Transformer从零实现/逐讲学习/04 组装多头注意力与 Transformer Block\|Multi-Head Attention、残差、LayerNorm、FFN]] |
| K07-03 | [[01_学习指南/08_Transformer从零实现/逐讲学习/04 组装多头注意力与 Transformer Block\|Pre-Norm/Post-Norm]]、[[01_学习指南/08_Transformer从零实现/逐讲学习/05 给 token 加位置并理解 RoPE\|位置编码与 RoPE]] |
| K07-04 | [[01_学习指南/08_Transformer从零实现/逐讲学习/05 给 token 加位置并理解 RoPE\|Encoder-Decoder 与 Decoder-only 的结构对照]] |
| K07-05 | [[01_学习指南/08_Transformer从零实现/逐讲学习/06 对齐自回归目标与交叉熵\|teacher forcing、错位目标、token 交叉熵与有效监督位置]] |
| K07-06 | [[01_学习指南/08_Transformer从零实现/逐讲学习/07 训练小模型并理解 FlashAttention\|分块、在线 softmax 和 IO 优化]] |

| 验收编号 | 证据位置 |
|---|---|
| C07-01 | [[01_学习指南/08_Transformer从零实现/示例工程/app/attention.py\|手写注意力]]、[[01_学习指南/08_Transformer从零实现/示例工程/app/model.py\|MHA 与 Transformer Block]]、[[01_学习指南/08_Transformer从零实现/示例工程/tests/test_model.py\|形状与因果测试]] |
| C07-02 | [[01_学习指南/08_Transformer从零实现/示例工程/tests/test_attention.py\|注意力、mask、稳定性与梯度测试]]、[[01_学习指南/08_Transformer从零实现/示例工程/tests/test_model.py\|模型测试]] |
| C07-03 | [[01_学习指南/08_Transformer从零实现/逐讲学习/04 组装多头注意力与 Transformer Block\|Pre-Norm/Post-Norm 结构和稳定性解释]] |
| C07-04 | [[01_学习指南/08_Transformer从零实现/逐讲学习/01 看懂缩放点积注意力\|点积方差与缩放因子推导]] |
| C07-05 | [[01_学习指南/08_Transformer从零实现/逐讲学习/06 对齐自回归目标与交叉熵\|长度 4 输入/目标表与训练/生成过程]] |
| C07-06 | [[01_学习指南/08_Transformer从零实现/逐讲学习/07 训练小模型并理解 FlashAttention\|算法收益与硬件/版本条件]] |
