---
title: 第 3 讲：用 LSA 向量理解稠密检索
tags: [rag, lsa, dense-retrieval]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 3 讲：用 LSA 向量理解稠密检索

> [!nav] 页面导航
> [[01_学习指南/13_RAG检索重排与评估/00 RAG 检索重排与评估学习地图#学习顺序|单元 13：RAG 检索重排与评估]] · [[01_学习指南/13_RAG检索重排与评估/逐讲学习/02 手算 BM25 并运行关键词检索|上一讲]] · [[01_学习指南/13_RAG检索重排与评估/逐讲学习/04 组合改写混合检索与重排|下一讲]]

## 要解决什么问题

关键词索引为每个词设置一个坐标，词表可能有几万维。能否把片段压缩到少量连续数值，再用向量方向比较它们？这就是本讲要跑的稠密路线。

**稠密向量**通常是维度较低、很多坐标非零的数字数组。它不自动意味着“高级模型理解语义”。本工程用 **LSA（潜在语义分析）**：把词频权重矩阵做低秩近似，从共现统计中提取少量方向。它是真实计算的向量检索，但没有神经网络预训练，也没有下载 Embedding 模型。

前置：向量、矩阵形状、范数。需要完整数学补课时读[[01_学习指南/05_数学概率与优化/逐讲学习/01 向量矩阵与张量形状|形状]]和[[01_学习指南/05_数学概率与优化/逐讲学习/11 SVD低秩近似与综合速查|SVD]]。先掌握输入输出即可继续，不必现在推完矩阵分解。

## 从词表矩阵到八维向量

第一步 **TF-IDF**：词频乘以稀有词权重，得到“片段数 × 词表大小”的矩阵。本工程使用 scikit-learn 的 `TfidfVectorizer`；它的具体 TF-IDF 权重与 BM25 不同，不要混用公式。

第二步 **TruncatedSVD**：只保留若干主要方向，投影成“片段数 × 8”的矩阵。“截断”指舍弃其余方向。压缩像保留一张图片的主要轮廓：更省空间，但细节会丢；实际机制是矩阵投影，不是把向量任意截去末尾数字。官方将 TF-IDF 上的该用途称为 LSA：[TruncatedSVD 文档](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.TruncatedSVD.html)。

第三步 **normalize**：把每条向量缩放到长度 1。长度指平方和开根号，不是元素个数。单位向量点积就等于余弦相似度。

```text
资料文本 → fit TF-IDF → fit SVD → 归一化文档向量
问题文本 → transform 同一个 TF-IDF → transform 同一个 SVD → 归一化问题向量
```

`fit` 学习词表/权重/投影；`transform` 使用已经学习的规则。问题和文档必须在同一个坐标空间，不能为每道问题重新 fit 一个 SVD。两个各自转动过的坐标系，即使都八维，也不能直接比较。

## 手算余弦相似度

取问题向量 `[1, 0]`，片段 A `[2, 0]`，片段 B `[0, 3]`：

```text
cos(q, A) = (1×2 + 0×0) / (1×2) = 1
cos(q, B) = (1×0 + 0×3) / (1×3) = 0
```

相同方向得 1，垂直得 0。一般余弦范围是 -1～1；LSA 可以有负坐标，工程只保留正相似度候选，这是本实验选择。余弦高并不说明政策最新、权限可见或答案充分。

零向量没有有效方向。query 中的词全不在词表时，TF-IDF 为零，归一化保持零；分数全为零，候选为空。这是合理失败信号，不能为了凑 K 条结果随便返回文档。

## 阅读关键源码

打开 `retrieval.py` 的 `Retriever.__init__`：

1. `TfidfVectorizer(tokenizer=tokenize, token_pattern=None)` 使用我们已经解释的英文分词函数；`token_pattern=None` 关闭默认分词模式，避免两套规则混用。
2. `fit_transform` 一次完成学习和转换，得到稀疏文档矩阵。
3. `component_count` 取期望维度、词表维度减一、片段数减一的最小值，防止小矩阵要求过多方向。传入 8 不保证所有数据都恰好生成八维，先看实际 shape。
4. `random_state=42` 固定随机初始化，帮助同一环境复跑；不保证所有软件和硬件版本位级相同。
5. `normalize` 返回单位文档向量。

再看 `_rank` 的 dense 分支：转换 query；用同一 reducer 投影；归一化；`self.dense_vectors @ dense_query[0]` 计算每条文档与 query 的点积。`@` 是矩阵乘法，形状 `[24, 8] @ [8] → [24]`，不是逐元素相乘。

## 动手观察形状与结果

在示例工程新建 `inspect_dense.py`：

```python
from pathlib import Path
from data import load_dataset
from retrieval import Retriever

documents, _ = load_dataset(Path(__file__).parent / "fixtures")
retriever = Retriever(documents, dimensions=8)
print(retriever.dense_vectors.shape)
for hit in retriever.search("storage retention period", "dense", top_k=3):
    print(hit.document.document_id, round(hit.score, 3))
print(retriever.search("zzzzunseenword", "dense"))
```

运行共享解释器，预期形状 `(24, 8)`，常规 query 返回最多三项正分候选，最后未知词 query 返回 `[]`。不要预先认定 gold 必在第一名；用第 5 讲指标检查。

运行 `demo.py --dimensions 4 --output results_dim4` 与默认 8 维对照。`--dimensions` 是压缩维度；`--output` 指定新的结果目录，防止覆盖默认结果。记录各策略指标，再想：维度变小是否让不同字段混在一起？维度大是否一定更好？样本小，不能只看一次数字就定生产参数。

## 与神经 Embedding 和 GPU 的关系

LSA 依赖当前小语料共现，没见过的同义词很难匹配。神经 Embedding 通过训练学习文本表示，能利用训练数据的语义模式；它也会受语言、领域、截断、query/document 前缀和模型版本影响。

真实接入时替换的是“文本 → 向量”部分：固定模型及 revision、query/document 编码约定、token 上限、归一化和相似度，再用相同 gold 评估。语料变更可能要求重新建索引，不能只把新向量塞进旧模型空间。

当前 LSA 在 CPU 运行。GPU 更适合批量神经 Embedding 和 CrossEncoder 推理；是否值得用取决于规模、显存和吞吐。先学这个 CPU 实验不会限制后面使用 GPU；它让你能先发现指标、分组和引用错误，而这些错误不会因为换 GPU 自动消失。

## 常见错误与练习

`ModuleNotFoundError: sklearn`：先检查 VS Code 是否选共享解释器，再检查根依赖清单；不要直接全局安装。`empty vocabulary`：看语料与分词器是否产生词。维度不符：核对 query 有没有使用相同 vectorizer/reducer。数值略有差异：记录安装版本，先比较排序和容差，不要求打印最后一位相同。

**跟做：** 手算 `[1,1]` 与 `[1,0]` 的余弦，约 0.707。完成标准：知道分母来自两条向量范数。

**独立：** 写出 24 段、词表 80 词、投影 8 维时每一步形状；解释为何 query 输出是 `[1,8]`。

**迁移：** 设计换成中文神经 Embedding 的对照表，包含模型 revision、设备、前缀、维度、归一化、延迟和相同测试集。先形成可复核方案；安装模型包/下载权重需按工作区规则批准。

> [!example]- 参考答案与解析
> 文档稀疏矩阵 `[24,80]` → 文档稠密矩阵 `[24,8]`；query `[1,80]` → `[1,8]`。压缩方向由文档 fit，query 只 transform。更高维可能保留细节，也可能保留噪声；真正答案由开发集选择和保留集评估决定。未知词零向量说明这个表示没覆盖它，不说明问题没有业务答案。

## 继续学习

> [!next] 下一步
> [[01_学习指南/13_RAG检索重排与评估/逐讲学习/04 组合改写混合检索与重排|下一讲：组合改写混合检索与重排]]

> [!info]- 练习与记录
> [[01_学习指南/13_RAG检索重排与评估/示例工程/README#代码导航|查看源码]] · [[01_学习指南/13_RAG检索重排与评估/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 13：RAG 检索重排与评估|本单元完成清单]]
