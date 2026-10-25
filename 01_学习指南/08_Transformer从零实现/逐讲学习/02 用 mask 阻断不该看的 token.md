---
title: 第 2 讲：用 mask 阻断不该看的 token
tags:
  - transformer
  - attention-mask
  - pytorch
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：用 mask 阻断不该看的 token

> [!nav] 页面导航
> [[01_学习指南/08_Transformer从零实现/00 Transformer 从零实现学习地图#学习顺序|单元 08：Transformer 从零实现]] · [[01_学习指南/08_Transformer从零实现/逐讲学习/01 看懂缩放点积注意力|上一讲]] · [[01_学习指南/08_Transformer从零实现/逐讲学习/03 手算归一化前馈网络与残差|下一讲]]

继续组装 Block 前，先完成 [[01_学习指南/08_Transformer从零实现/逐讲学习/03 手算归一化前馈网络与残差|归一化、前馈网络与残差]]，避免把三个陌生部件一起当作黑盒。

## 本讲目标与先修知识

本讲沿用上一讲的 `[B,H,T,T]` 分数矩阵和逐行 softmax。学完后，你能解释因果 mask 和 padding mask 的区别、画出长度 4 的允许读取区域，并能从测试确认未来 token 不影响过去输出。

## 因果 mask：不读未来

自回归语言模型要根据左侧已知 token 预测下一个 token。若位置 1 看到了位置 2 的答案，训练就发生了信息泄漏。因果约束让位置 i 只能读取位置 0 到 i：

```text
Query 行 \\ Key 列   0  1  2  3
位置 0              ✓  ×  ×  ×
位置 1              ✓  ✓  ×  ×
位置 2              ✓  ✓  ✓  ×
位置 3              ✓  ✓  ✓  ✓
```

手写实现先构造下三角允许区域，再把不允许位置分数设为负无穷。softmax 后，被屏蔽位置的权重为 0。注意顺序：先屏蔽分数，再 softmax。

## Padding mask：不读填充位置

一批句子长度不同，为了拼成矩形，短句末尾会补 padding token。它只是占位符，不应被当作真实上下文。工程使用 `valid_tokens_mask`，形状为 `[B,T]`，其中 `True` 表示允许作为 Key 被读取，`False` 表示 padding。它扩展后与因果约束一起作用于分数。

不同 PyTorch API 的布尔 mask 语义可能相反；本工程自定义函数和 PyTorch 函数不能只凭名字猜语义，要看参数文档。当前实现也要求右侧 padding，并对不合法布局给出错误。

## 结合两种规则

对一个因果语言模型，某个分数可见，当且仅当 Key 不在未来、且该 Key 不是 padding。屏蔽的 Key 权重为零。不要把“屏蔽 Query 输出”和“屏蔽 Key 输入”混为一谈：这里的有效 token mask 控制每个 Query 能读取哪些 Key；padding 位置的监督目标另由损失函数处理，见 [[01_学习指南/08_Transformer从零实现/逐讲学习/06 对齐自回归目标与交叉熵|第 6 讲：对齐自回归目标与交叉熵]]。

## 在工程里动手

打开 [attention.py](../示例工程/app/attention.py)，查看 `scaled_dot_product_attention` 中生成因果允许矩阵和组合 `valid_tokens_mask` 的部分；再读 [test_attention.py](../示例工程/tests/test_attention.py) 中的未来泄漏与 padding 测试。

在工程终端运行：

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest tests/test_attention.py -q
```

成功结果应包含 `passed`。关键验证方式不是只看矩阵，而是改变未来 token 后，早期位置输出仍保持相同（在浮点容差范围内）。若结果变化，就说明未来信息泄漏。

## 常见错误与排查

- mask 方向反了：检查对角线下方是否允许、上方是否屏蔽。
- 在 softmax 后才把权重清零：剩余权重行和会小于 1；应该先遮分数。
- padding token 参与语言模型损失：即使注意力遮住了它，目标标签也要用忽略索引排除。
- 全部 Key 都被屏蔽：softmax 对一整行负无穷会产生无效数值。构造数据时至少保证每个有效 Query 有合法 Key。
- 不同接口的 mask 语义相反：查当前安装版本 API 的布尔值定义。

## 练习

### 跟做练习

对 4 个位置写出因果矩阵，并指出位置 2 可看哪些 Key。完成标准：位置 2 能看 0、1、2，不能看 3。

### 独立练习

句子有效长度为 3，输入被补到长度 5。写出允许 Key 的 padding mask。参考：`[True, True, True, False, False]`。再叠加因果规则后，第 1 个 Query 只允许 Key 0、1。

### 迁移练习

设计一个测试：先固定前两个 token，只改变后续 token，再比较前两个位置的输出。说明若测试失败可能是什么原因。完成标准：指出 mask 缺失/方向错误，并能定位到注意力权重遮罩前后顺序。

> [!example]- 答案解析：两类 mask
> 因果约束按 Query 位置和 Key 位置比较；padding mask 按每个样本告诉我们哪些 Key 是有效 token。对位置 1，因果规则只允许 0、1；若位置 0 或 1 是 padding，则再由有效 mask 去掉。两者组合是逻辑“且”。

## 继续学习

> [!next] 下一步
> [[01_学习指南/08_Transformer从零实现/逐讲学习/03 手算归一化前馈网络与残差|下一讲：手算归一化前馈网络与残差]]

> [!info]- 练习与记录
> [[01_学习指南/08_Transformer从零实现/示例工程/README#代码导航|查看源码]] · [[01_学习指南/08_Transformer从零实现/示例工程/README#环境与运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 08：Transformer 从零实现|本单元完成清单]]
