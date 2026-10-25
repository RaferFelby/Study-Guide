---
title: 第 2 讲：Dataset与DataLoader
aliases:
  - Dataset DataLoader
tags:
  - pytorch
  - dataset
  - dataloader
  - collate
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：Dataset与DataLoader

> [!nav] 页面导航
> [[01_学习指南/06_PyTorch训练闭环/00 PyTorch训练闭环学习地图#学习顺序|单元 06：PyTorch训练闭环]] · [[01_学习指南/06_PyTorch训练闭环/逐讲学习/01 Tensor设备与广播|上一讲]] · [[01_学习指南/06_PyTorch训练闭环/逐讲学习/03 拼齐变长序列并验证掩码|下一讲]]

## 这一讲要解决什么问题

训练代码不应该把所有数据、随机打乱、批处理和设备搬运混在一个大循环里。Dataset 负责定义“一个样本是什么”，DataLoader 负责按批次取样，Sampler 决定取样顺序，collate_fn 负责把多个样本组合成模型能接受的批次。

> [!contents]- 本讲导航
> - [[#这一讲要解决什么问题|这一讲要解决什么问题]]
> - [[#开始前要会什么|开始前要会什么]]
> - [[#Dataset：一个样本的契约|Dataset：一个样本的契约]]
> - [[#DataLoader 与固定划分|DataLoader 与固定划分]]
> - [[#Sampler：明确样本出现顺序|Sampler：明确样本出现顺序]]
> - [[#collate_fn：组合一个 batch|collate_fn：组合一个 batch]]
> - [[#动手操作|动手操作]]
> - [[#常见错误|常见错误]]
> - [[#练习与答案解析|练习与答案解析]]
> - [[#本讲小结|本讲小结]]

## 开始前要会什么

你需要能读懂 Python 类、方法、列表或张量索引，并理解 Tensor 的 shape。若类或索引还不熟，先回看 [[01_学习指南/01_Python工程化/逐讲学习/01 运行Python并统计工单|单元 01 第 1 讲]]；shape 可回看 [[01_学习指南/05_数学概率与优化/逐讲学习/01 向量矩阵与张量形状|单元 05 第 1 讲]]。本讲先让你亲手运行一个四条数据的例子，再解释批次和采样。

先在 VS Code 打开 `01_学习指南/06_PyTorch训练闭环/示例工程/`，集成终端运行 `Get-Location` 核对目录。下面第一组三段代码依次放入同一个 `dataset_demo.py`；其他文件各自独立。第一次只完成固定大小批次与跟做题，第二次练采样和固定划分，再进入第 3 讲的变长序列。全部使用已有共享环境，`num_workers=0` 表示在当前进程读取数据，本讲暂不引入多进程。

## Dataset：一个样本的契约

自定义 Dataset 通常实现 __len__ 和 __getitem__。__len__ 告诉加载器有多少样本，__getitem__ 根据索引返回一个样本。返回结构要稳定，例如总是返回 feature 和 target，不能某些样本返回两个值、另一些返回三个值。

~~~python
import torch
from torch.utils.data import DataLoader, Dataset


class RegressionDataset(Dataset):
    def __init__(self, features, targets):
        if len(features) != len(targets):
            raise ValueError("features and targets must have the same length")
        self.features = features
        self.targets = targets

    def __len__(self):
        return len(self.features)

    def __getitem__(self, index):
        return self.features[index], self.targets[index]
~~~

把上面的类和下面代码放在同一个 `dataset_demo.py` 文件中。这里的 `features` 有 4 个样本，每个样本只有 1 个特征；`targets` 是与它们一一对应的答案：

~~~python
features = torch.tensor([[0.0], [1.0], [2.0], [3.0]])
targets = torch.tensor([[0.0], [1.0], [4.0], [9.0]])
dataset = RegressionDataset(features, targets)

print(len(dataset))
print(dataset[1])
~~~

在单元 06 示例工程目录运行 `..\..\..\.venv\Scripts\python.exe dataset_demo.py`。预期第一行是 `4`，第二行为 `(tensor([1.]), tensor([1.]))`，浮点显示位数可不同。`len(dataset)` 调用了 `__len__`；`dataset[1]` 调用了 `__getitem__(1)`，索引从 0 开始，所以它取的是第二条样本。

`__init__` 在创建对象时执行，`self` 是当前对象，`self.features` 保存这个对象的数据。`__getitem__` 里的逗号把特征与目标一起作为二元组返回。构造时先检查数量，避免最后一条特征取不到对应目标。这个教学类只演示索引契约，工程 [data.py](../示例工程/app/data.py) 还将输入转换为浮点类型；本例一开始就提供浮点张量。

## DataLoader 与固定划分

DataLoader 的 batch_size 控制每批样本数，shuffle=True 通常用于训练集，验证集通常不打乱也不改变样本内容。训练/验证划分必须固定随机种子和索引，才能比较两次实验；不能每次运行都抽到不同验证集后再把 loss 变化归因于模型。

示例工程的 `build_loaders` 用固定 generator 进行 `random_split`，并返回训练和验证 DataLoader。generator 是保存随机数生成状态的对象；相同起点与相同调用过程可重复抽取。这里固定的是划分，训练 DataLoader 的打乱还受其他随机状态影响，不能只靠 split 的 seed 就声称整个训练可复现。

继续在同一个文件中加上下面代码，观察 DataLoader 怎样把四条样本分成两个批次：

~~~python
data_loader = DataLoader(dataset, batch_size=2, shuffle=False, num_workers=0)
for feature_batch, target_batch in data_loader:
    print(feature_batch.shape, target_batch.shape)
    print(feature_batch[:, 0].tolist(), target_batch[:, 0].tolist())
~~~

预期每个批次的两个 shape 都是 `torch.Size([2, 1])`；样本值依次是 `[0.0, 1.0]` 对应 `[0.0, 1.0]`，以及 `[2.0, 3.0]` 对应 `[4.0, 9.0]`。`batch_size=2` 表示每次交给训练循环两个样本；`shuffle=False` 让本次演示顺序固定，方便对照输出。真实训练通常打乱训练集，但验证集一般不打乱。

`for feature_batch, target_batch` 把一批里的两部分分别接住。默认组合会把两个 `[1]` 特征堆成 `[2,1]`。`[:,0]` 表示所有行的第 0 列；`tolist()` 转成 Python 列表便于查看。一个 epoch 是把当前数据集遍历一轮。

现在把 `batch_size` 改为 3 再运行：第一批大小是 3，最后一批大小是 1，不能要求每批恰好 3。默认 `drop_last=False` 保留最后的不足一批；改为 True 时才丢掉它。四个样本每批 3 条，保留末批共两批，丢末批则只一批。对本节有确定长度、每条只取一次的数据，批次数为样本数除以 batch_size 后向上取整；其他采样策略要重新计算。

### 独立核对固定划分

另存为 `lesson_02_split.py`：

```python
from app.data import make_dataset, build_loaders

dataset = make_dataset(size=10, seed=7)
train_loader, valid_loader = build_loaders(dataset, batch_size=3, seed=7)
second_train, second_valid = build_loaders(dataset, batch_size=3, seed=7)
print(len(train_loader.dataset), len(valid_loader.dataset))
print(train_loader.dataset.indices == second_train.dataset.indices)
print(valid_loader.dataset.indices == second_valid.dataset.indices)
print(len(train_loader), len(valid_loader))
features, targets = next(iter(valid_loader))
print(list(features.shape), list(targets.shape))
```

运行 `..\..\..\.venv\Scripts\python.exe lesson_02_split.py`，应依次看到 `8 2`、`True`、`True`、`3 1`、`[2, 1] [2, 1]`。默认验证比例为 0.2，10 条分成 8／2；训练 8 条每批 3 条为三批。`.dataset.indices` 是这次子集在原数据中的索引列表。`next(iter(...))` 创建批次迭代器并取第一批，这里取不打乱的验证批次。

这段对照确认子集索引相同，尚未比较训练顺序。工程中的固定种子也无法阻止同一用户的重复数据泄漏；划分单位应结合任务决定，迁移题会处理这一点。

## Sampler：明确样本出现顺序

当类别不均衡、样本有权重或需要分布式切分时，可以使用 Sampler。WeightedRandomSampler 能提高少数类别被抽到的机会，但它改变了训练分布，不会自动修复验证集或指标解释。使用前要记录采样策略。

先不做加权采样，只明确指定顺序。另存为 `lesson_02_order.py`：

```python
import torch
from torch.utils.data import DataLoader, TensorDataset

features = torch.tensor([[0.0], [1.0], [2.0], [3.0]])
targets = features.square()
dataset = TensorDataset(features, targets)
loader = DataLoader(dataset, batch_size=2, sampler=[3, 1, 0, 2], num_workers=0)
for feature_batch, target_batch in loader:
    print(feature_batch[:, 0].tolist(), target_batch[:, 0].tolist())
```

运行 `..\..\..\.venv\Scripts\python.exe lesson_02_order.py`，两行是 `[3.0, 1.0] [9.0, 1.0]` 和 `[0.0, 2.0] [0.0, 4.0]`。`TensorDataset` 将长度相同的张量按相同索引配对，省去重复定义类；`square()` 对每项求平方。本例把索引列表作为可迭代 sampler 使用，顺序先由 sampler 决定，再按每批两个组合；特征与目标一起取，没有拆散对应关系。

不要同时设置这个 sampler 和 `shuffle=True`，框架会报告冲突。需要可重复的随机打乱时，给 DataLoader 单独传 `generator=torch.Generator().manual_seed(7)` 并记录状态；重复遍历同一个 generator 会推进状态，不会每一轮自动回到相同排列。加权与分布式采样属于后续内容。

## collate_fn：组合一个 batch

collate 指“组合一批”，`collate_fn` 是 DataLoader 在取出多个样本后调用的组合函数。默认方式能堆叠同形状张量；不同长度不能直接堆成长方形。padding 是补齐短序列，mask（掩码）记录哪些位置有效。补齐不是所有任务的唯一做法，也可按长度分组等；本单元练右侧补零。

进入 [[01_学习指南/06_PyTorch训练闭环/逐讲学习/03 拼齐变长序列并验证掩码|变长序列详细课]]：先手算 `[[4,0],[],[7]]` 的长度和掩码，再运行完整答案，最后接入 DataLoader。这里真实数字也可以是 0，因此不能用“值不为零”判断有效位置。这是下一讲的任务。本讲先完成下面的固定批次与分组划分练习，再按导航继续。

## 动手操作

1. 将最前面的类、四条样本和遍历批次三段合并运行，再改 batch_size=3，核对末批大小。
2. 运行独立的划分与顺序文件，解释 `8／2`、`3／1` 与两批取样顺序。
3. 把划分实验 batch_size 从 3 改为 4，预测批次数为 `2／1` 后再运行。
4. 记录一个下一讲要解决的问题：怎样区分真实零值、空序列和全空批次。具体实现留到下一讲。

## 常见错误

- 在 Dataset 内部随机增强，却没有记录随机种子和验证边界。
- 把验证样本混进训练集，造成数据泄漏。
- 只固定模型种子，不固定 split、DataLoader worker 或采样器。
- collate_fn padding 后没有返回 mask，导致模型把填充当真实输入。
- 最后一个 batch 比预期小：先核对样本数、batch_size 与 drop_last，而不是删除末批来掩盖错误。
- 定义类后没有输出：还需执行创建 dataset 与遍历的代码；文件里只有定义并不代表已读取数据。
- 找不到 `app`：确认脚本在本单元示例工程并从该目录运行，不混入其他单元同名模块。

## 练习与答案解析

### 跟做练习：检查一个 batch

写一个 check_batch 函数，确认 feature 的第一维等于 target 的第一维，dtype 是浮点，并打印 batch 大小。

提示：工程已有 `app.training.check_batch` 检查二维、等批量大小与有限值。本题先补浮点类型与非空的课堂要求，再复用现有检查，而不是复制一套训练检查。另存为 `lesson_02_check.py`：

> [!example]- 跟做参考答案与解析
> ```python
> import torch
> from torch.utils.data import DataLoader, TensorDataset
> from app.training import check_batch
>
> def check_float_batch(features, targets):
>     check_batch(features, targets)
>     if not features.is_floating_point() or not targets.is_floating_point():
>         raise ValueError("本回归练习要求浮点特征和目标")
>     if features.shape[0] == 0:
>         raise ValueError("批次不能为空")
>     print("批大小：", features.shape[0])
>
> values = torch.tensor([[0.0], [1.0], [2.0]])
> loader = DataLoader(TensorDataset(values, values.square()), batch_size=2)
> for features, targets in loader:
>     check_float_batch(features, targets)
> ```
> 用共享解释器运行该文件，输出 `批大小： 2` 和 `批大小： 1`。`is_floating_point()` 检查 dtype 是否为浮点数；`not` 取反，`or` 表示任一条件成立就拒绝。原检查用 `isfinite` 同时拒绝 NaN（无效数值）和正负无穷。每批调用能发现后面才出现的问题。把输入 2.0 改成 `float("nan")`，第一批打印后应在第二批报错，不应隐藏失败；修改后再恢复正常输入。

### 下一讲的独立练习预告

完成下一讲的逐步示例后，实现一个变长整数序列的 collate_fn，返回 padded_values、lengths 和 mask。测试空序列、长度相同和长度差异很大的 batch。

具体输入、逐步提示、完整源码导航与答案在 [[01_学习指南/06_PyTorch训练闭环/逐讲学习/03 拼齐变长序列并验证掩码|第 3 讲：拼齐变长序列并验证掩码]]。完成判断：不仅打印对形状，还能用 mask 取回每条原序列，真实 0 不丢失。

### 迁移练习

为工单分类设计训练/验证划分，说明为什么同一个用户或同一条工单的重复版本不能随意分到两边。

本题明确评估目标为“对新用户的工单分类”。四条 `(用户,工单,版本)` 为 `(u1,t1,1)`、`(u1,t1,2)`、`(u2,t2,1)`、`(u3,t3,1)`。先按用户将 u1、u2 放训练，u3 放验证，再说明为什么按行随机切分可能造成泄漏。

> [!example]- 迁移参考答案与解析
> 训练三条、验证一条；u1 的两个版本一起留在训练。否则验证可能只是识别已见用户或同一工单的近重复文字，无法回答新用户效果。用字典按 user_id 收集记录，再按用户列表分组；检查两侧用户集合不相交，工单版本不跨组，并保留索引记录。四条仅适合讲机制，不能估计稳定效果。
>
> 若真正目标是“已知用户未来的新工单”，应考虑时间切分、去除同一工单跨期的重复版本，并避免使用未来字段；此时用户可以跨两侧，不能把“用户永远不得跨集合”当通用规则。预处理的词表、标准化等也只在训练数据上拟合。完成判断：明确评估目标、分组单位、重复版本处理、检查方式，且能说明目标改变后为什么划分也变。

## 本讲小结

数据管道是训练闭环的一部分。先定义样本契约，再决定批次、顺序、采样和 padding；任何改变数据分布的操作都需要记录并解释。

参考接口：[PyTorch 2.14 数据加载说明](https://docs.pytorch.org/docs/2.14/data.html)。本讲在已有共享版本运行核对，其他版本需先确认接口与输出。

## 继续学习

> [!next] 下一步
> [[01_学习指南/06_PyTorch训练闭环/逐讲学习/03 拼齐变长序列并验证掩码|下一讲：拼齐变长序列并验证掩码]]

> [!info]- 练习与记录
> [[01_学习指南/06_PyTorch训练闭环/示例工程/README#代码导航|查看源码]] · [[01_学习指南/06_PyTorch训练闭环/示例工程/README#运行训练|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 06：PyTorch 与训练闭环|本单元完成清单]]
